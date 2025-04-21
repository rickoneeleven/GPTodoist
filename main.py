# File: main.py
import os, readline, time
import helper_todoist_part1, helper_todoist_part2, helper_commands, module_call_counter, helper_general, helper_parse, helper_diary
from rich import print
from datetime import datetime, timedelta, timezone # Import necessary datetime components
import traceback # For detailed error logging
from todoist_api_python.api import TodoistAPI
from helper_general import load_json, save_json # <<< Import specific JSON helpers

# --- Constants ---
TODOIST_API_KEY = os.environ["TODOIST_API_KEY"]
# BACKUP_TIMESTAMP_FILE = "j_last_backup_timestamp.txt" # <<< REMOVED
OPTIONS_FILENAME = "j_options.json" # <<< ADDED: Central options file
BACKUP_INTERVAL_HOURS = 1
LAST_BACKUP_KEY = "last_backup_timestamp" # <<< ADDED: Key for timestamp in JSON

# --- Initialization ---
api = TodoistAPI(TODOIST_API_KEY)
readline.set_auto_history(
    True
)  # Suppress warning, enables arrow keys in input()

# --- Backup Logic ---

def _read_last_backup_timestamp() -> datetime | None:
    """Reads the last backup timestamp from the options JSON file."""
    # <<< MODIFIED: Use load_json from helper_general >>>
    options_data = load_json(OPTIONS_FILENAME, default_value=helper_general.DEFAULT_OPTIONS)

    timestamp_str = options_data.get(LAST_BACKUP_KEY)

    if not timestamp_str:
        return None # Key doesn't exist or is None/empty

    try:
        # Parse ISO format timestamp, ensuring it's timezone-aware (UTC assumed)
        dt = datetime.fromisoformat(timestamp_str)
        if dt.tzinfo is None:
             return dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError) as e:
        print(f"[red]Error parsing '{LAST_BACKUP_KEY}' value ('{timestamp_str}') from {OPTIONS_FILENAME}: {e}[/red]")
        return None # Treat as if no valid timestamp exists
    except Exception as e:
        # Catch unexpected errors during parsing specifically
        print(f"[red]Unexpected error parsing timestamp string: {e}[/red]")
        traceback.print_exc()
        return None

def _write_last_backup_timestamp(timestamp: datetime):
    """Writes the current backup timestamp to the options JSON file."""
    # <<< MODIFIED: Load, update, save JSON >>>
    options_data = load_json(OPTIONS_FILENAME, default_value=helper_general.DEFAULT_OPTIONS)

    # Ensure timestamp is timezone-aware (UTC) before writing
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    # Update the specific key
    options_data[LAST_BACKUP_KEY] = timestamp.isoformat()

    # Save the entire dictionary back
    if not save_json(OPTIONS_FILENAME, options_data):
        print(f"[red]Failed to save updated options file: {OPTIONS_FILENAME}[/red]")
    # else:
    #     print(f"[dim]Updated '{LAST_BACKUP_KEY}' in {OPTIONS_FILENAME}[/dim]") # Optional confirmation


# --- _check_and_trigger_backup (Unchanged, relies on modified read/write functions) ---
def _check_and_trigger_backup():
    """Checks if enough time has passed and triggers the backup process."""
    last_backup_time = _read_last_backup_timestamp()
    current_time_utc = datetime.now(timezone.utc)
    backup_needed = False

    if last_backup_time is None:
        print("[cyan]No previous backup timestamp found in options. Triggering initial backup.[/cyan]")
        backup_needed = True
    else:
        time_since_last_backup = current_time_utc - last_backup_time
        if time_since_last_backup >= timedelta(hours=BACKUP_INTERVAL_HOURS):
            print(f"[cyan]More than {BACKUP_INTERVAL_HOURS} hour(s) since last backup. Triggering backup.[/cyan]")
            backup_needed = True

    if backup_needed:
        try:
            print("[cyan]Running backup process...[/cyan]")
            helper_general.backup_json_files()
            _write_last_backup_timestamp(current_time_utc)
            print("[green]Backup process finished.[/green]")
        except Exception as e:
            print(f"[red]An unexpected error occurred during the backup process execution: {e}[/red]")
            traceback.print_exc()
        print("-" * 20) # Separator after backup attempt


# --- Main Loop (Unchanged structure) ---
def main_loop():
    """The main execution loop of the application."""
    while True:
        print("-" * 60)
        _check_and_trigger_backup()
        helper_todoist_part2.get_next_todoist_task(api)
        helper_todoist_part1.print_completed_tasks_count()
        helper_todoist_part2.check_if_grafting(api)
        helper_diary.weekly_audit()
        helper_diary.purge_old_completed_tasks()
        helper_todoist_part1.update_recurrence_patterns(api)
        user_message = helper_parse.get_user_input()
        print("processing... ++++++++++++++++++++++++++++++++++++++++++++++")
        if not helper_general.connectivity_check():
            print("[red]Connectivity check failed. Please check network and try again.[/red]")
            time.sleep(2)
            continue
        if not helper_todoist_part1.verify_device_id_before_command():
            print("[bold red]Command blocked due to device ID mismatch.[/bold red]")
            time.sleep(1)
            continue
        command_handled = helper_commands.ifelse_commands(api, user_message)
        if not command_handled:
            print()
            print("[bold][wheat1]          eh? (Command not recognized)[/wheat1][/bold]\n")

# --- Entry Point (Unchanged) ---
if __name__ == "__main__":
    module_call_counter.apply_call_counter_to_all(globals(), __name__)
    main_loop()