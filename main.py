# File: main.py
import os
import readline
import threading
import time
import helper_todoist_part1
import helper_todoist_part2
import helper_display
import helper_commands
import module_call_counter
import helper_general # Still needed for connectivity_check and backup_json_files
import helper_parse
import helper_diary
import helper_recurrence
import state_manager # <<< ADDED: Import the new state manager
import helper_effects
import helper_pinescore_status
from rich import print
from datetime import datetime, timedelta, timezone # Keep necessary datetime components
import traceback # For detailed error logging
from todoist_api_python.api import TodoistAPI
import pytz
# <<< REMOVED: load_json, save_json imports as they are handled by state_manager for backups now

# --- Constants ---
TODOIST_API_KEY = os.environ["TODOIST_API_KEY"]
_raw_pinescore_token = os.environ.get("PINESCOREDATA_WRITE_TOKEN")
PINESCOREDATA_WRITE_TOKEN = _raw_pinescore_token.strip() if isinstance(_raw_pinescore_token, str) else None
if PINESCOREDATA_WRITE_TOKEN == "":
    PINESCOREDATA_WRITE_TOKEN = None
PINESCOREDATA_BASE_URL = os.environ.get("PINESCOREDATA_BASE_URL", "https://data.pinescore.com")
PINESCOREDATA_UPDATED_BY = os.environ.get("PINESCOREDATA_UPDATED_BY", "gptodoist")
PINESCOREDATA_DEVICE_ID = helper_pinescore_status.get_local_device_id()
PINESCOREDATA_DEVICE_LABEL = helper_pinescore_status.get_local_device_label()
_raw_pinescore_interval = os.environ.get("PINESCOREDATA_BACKGROUND_INTERVAL_SECONDS", "300")
try:
    PINESCOREDATA_BACKGROUND_INTERVAL_SECONDS = max(1.0, float(_raw_pinescore_interval))
except (TypeError, ValueError):
    PINESCOREDATA_BACKGROUND_INTERVAL_SECONDS = 300.0
# <<< REMOVED: BACKUP_TIMESTAMP_FILE and OPTIONS_FILENAME, LAST_BACKUP_KEY as they are managed within state_manager
BACKUP_INTERVAL_HOURS = 1

# --- Initialization ---
api = TodoistAPI(TODOIST_API_KEY)
readline.set_auto_history(
    True
)  # Suppress warning, enables arrow keys in input()

# --- Backup Logic ---

# <<< REMOVED: _read_last_backup_timestamp function (moved to state_manager) >>>
# <<< REMOVED: _write_last_backup_timestamp function (moved to state_manager) >>>

# --- _check_and_trigger_backup (Refactored to use state_manager) ---
def _check_and_trigger_backup():
    """Checks if enough time has passed and triggers the backup process using state_manager."""
    # <<< MODIFIED: Use state_manager to get timestamp >>>
    last_backup_time = state_manager.get_last_backup_timestamp()
    current_time_utc = datetime.now(timezone.utc)
    backup_needed = False

    if last_backup_time is None:
        print("[cyan]No previous backup timestamp found. Triggering initial backup.[/cyan]")
        backup_needed = True
    else:
        # Ensure comparison is between aware datetime objects
        if last_backup_time.tzinfo is None: # Safety check if state_manager somehow returned naive
             last_backup_time = last_backup_time.replace(tzinfo=timezone.utc)
        time_since_last_backup = current_time_utc - last_backup_time
        if time_since_last_backup >= timedelta(hours=BACKUP_INTERVAL_HOURS):
            print(f"[cyan]More than {BACKUP_INTERVAL_HOURS} hour(s) since last backup. Triggering backup.[/cyan]")
            backup_needed = True
        # else: # Debugging/Info
        #     print(f"[dim]Time since last backup: {time_since_last_backup}. Interval: {BACKUP_INTERVAL_HOURS}h. No backup needed.[/dim]")


    if backup_needed:
        try:
            print("[cyan]Running backup process...[/cyan]")
            helper_general.backup_json_files() # Backup process itself still lives in helper_general
            # <<< MODIFIED: Use state_manager to set timestamp >>>
            state_manager.set_last_backup_timestamp(current_time_utc)
            print("[green]Backup process finished.[/green]")
        except Exception as e:
            print(f"[red]An unexpected error occurred during the backup process execution: {e}[/red]")
            traceback.print_exc()
        print("-" * 20) # Separator after backup attempt


# --- Main Loop (Uses refactored state_manager for verify_device_id implicitly) ---
def main_loop():
    """The main execution loop of the application."""
    pinescore_stop_event = None
    pinescore_thread = None
    startup_commands_shown = False

    if PINESCOREDATA_WRITE_TOKEN:
        print("[dim]data.pinescore.com status push: enabled[/dim]")
        background_api = TodoistAPI(TODOIST_API_KEY)
        pinescore_stop_event = threading.Event()
        pinescore_thread = threading.Thread(
            target=helper_pinescore_status.background_status_push_loop,
            kwargs={
                "stop_event": pinescore_stop_event,
                "api": background_api,
                "token": PINESCOREDATA_WRITE_TOKEN,
                "updated_by": PINESCOREDATA_UPDATED_BY,
                "base_url": PINESCOREDATA_BASE_URL,
                "interval_s": PINESCOREDATA_BACKGROUND_INTERVAL_SECONDS,
                "timeout_s": 3.0,
                "local_device_id": PINESCOREDATA_DEVICE_ID,
                "on_error": lambda exc: print(f"[red]data.pinescore.com background status push failed: {exc}[/red]"),
            },
            daemon=True,
            name="pinescore-status-push",
        )
        pinescore_thread.start()
        print(
            f"[dim]data.pinescore.com background status push interval: "
            f"{int(PINESCOREDATA_BACKGROUND_INTERVAL_SECONDS)}s[/dim]"
        )
        print(
            f"[dim]data.pinescore.com device: "
            f"{PINESCOREDATA_DEVICE_LABEL} ({PINESCOREDATA_DEVICE_ID[:8]})[/dim]"
        )
    else:
        print("[dim]data.pinescore.com status push: disabled (PINESCOREDATA_WRITE_TOKEN not set)[/dim]")

    try:
        while True:
            print("-" * 60)
            _check_and_trigger_backup() # Uses state_manager for timestamps now
            if not startup_commands_shown:
                helper_commands.print_startup_command_reference()
                startup_commands_shown = True
            regular_tasks, long_tasks_showing_count = helper_todoist_part2.get_next_todoist_task(api) # Will be refactored later
            # helper_todoist_part1.print_completed_tasks_count()  # Hidden by request
            helper_display.check_if_grafting(api)
            helper_diary.weekly_audit() # Will be refactored later
            helper_diary.purge_old_completed_tasks() # Will be refactored later
            helper_recurrence.update_recurrence_patterns(api)

            if PINESCOREDATA_WRITE_TOKEN and regular_tasks is not None:
                try:
                    pushed = helper_pinescore_status.push_tasks_up_to_date_status(
                        token=PINESCOREDATA_WRITE_TOKEN,
                        regular_tasks=regular_tasks,
                        long_tasks_showing_count=long_tasks_showing_count,
                        updated_by=PINESCOREDATA_UPDATED_BY,
                        base_url=PINESCOREDATA_BASE_URL,
                        timeout_s=3.0,
                    )
                    status = pushed.status
                    print(
                        f"[dim]data.pinescore.com status push: up_to_date={status.up_to_date} "
                        f"reason={status.reason}[/dim]"
                    )
                except Exception as exc:
                    print(f"[red]data.pinescore.com status push failed: {exc}[/red]")

            user_message = helper_parse.get_user_input()
            print("processing... ++++++++++++++++++++++++++++++++++++++++++++++")

            if not helper_general.connectivity_check():
                print("[red]Connectivity check failed. Please check network and try again.[/red]")
                time.sleep(2)
                continue

            # <<< MODIFIED: Use state_manager for device ID verification >>>
            if not state_manager.verify_active_task_device():
                # Message is printed within verify_active_task_device
                print("[bold red]Command blocked due to device ID mismatch.[/bold red]")
                time.sleep(1)
                continue

            if PINESCOREDATA_WRITE_TOKEN and isinstance(user_message, str) and user_message.strip():
                try:
                    helper_pinescore_status.claim_background_push_ownership(
                        token=PINESCOREDATA_WRITE_TOKEN,
                        updated_by=PINESCOREDATA_UPDATED_BY,
                        base_url=PINESCOREDATA_BASE_URL,
                        timeout_s=3.0,
                        device_id=PINESCOREDATA_DEVICE_ID,
                        device_label=PINESCOREDATA_DEVICE_LABEL,
                    )
                except Exception as exc:
                    print(f"[red]data.pinescore.com background ownership claim failed: {exc}[/red]")

            command_handled = helper_commands.ifelse_commands(api, user_message) # Will be refactored later
            if not command_handled:
                print()
                print("[bold][wheat1]          eh? (Command not recognized)[/wheat1][/bold]\n")

            # Trigger celebration once when both regular and long-term due tasks are done
            try:
                tasks = helper_todoist_part2.fetch_todoist_tasks(api)
                regular_done = tasks is not None and len(tasks) == 0
            except Exception:
                regular_done = False

            try:
                from long_term_indexing import get_next_due_long_task
                long_done = get_next_due_long_task(api) is None
            except Exception:
                long_done = False

            if regular_done and long_done:
                london_tz = pytz.timezone("Europe/London")
                today_london = datetime.now(london_tz).date().isoformat()
                last_date = state_manager.get_last_all_done_celebration_date()
                if last_date != today_london:
                    helper_effects.play_completion_celebration(duration=10.0)
                    state_manager.set_last_all_done_celebration_date(today_london)
    finally:
        if pinescore_stop_event is not None:
            pinescore_stop_event.set()
        if pinescore_thread is not None and pinescore_thread.is_alive():
            pinescore_thread.join(timeout=1.0)

# --- Entry Point (Unchanged) ---
if __name__ == "__main__":
    module_call_counter.apply_call_counter_to_all(globals(), __name__)
    main_loop()
