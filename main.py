# File: main.py
import os
import readline
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
from rich import print
from datetime import datetime, timedelta, timezone # Keep necessary datetime components
import traceback # For detailed error logging
from todoist_api_python.api import TodoistAPI
# <<< REMOVED: load_json, save_json imports as they are handled by state_manager for backups now

# --- Constants ---
TODOIST_API_KEY = os.environ["TODOIST_API_KEY"]
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
    while True:
        print("-" * 60)
        _check_and_trigger_backup() # Uses state_manager for timestamps now
        helper_todoist_part2.get_next_todoist_task(api) # Will be refactored later
        # helper_todoist_part1.print_completed_tasks_count()  # Hidden by request
        helper_display.check_if_grafting(api)
        helper_diary.weekly_audit() # Will be refactored later
        helper_diary.purge_old_completed_tasks() # Will be refactored later
        helper_recurrence.update_recurrence_patterns(api)

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

        command_handled = helper_commands.ifelse_commands(api, user_message) # Will be refactored later
        if not command_handled:
            print()
            print("[bold][wheat1]          eh? (Command not recognized)[/wheat1][/bold]\n")

# --- Entry Point (Unchanged) ---
if __name__ == "__main__":
    module_call_counter.apply_call_counter_to_all(globals(), __name__)
    main_loop()
