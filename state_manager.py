# File: state_manager.py
import os
import json
import datetime
import hashlib
import platform
import uuid
import traceback
from dateutil.parser import parse
from typing import Any, Dict, List, Union, Tuple, Optional
from rich import print  # Ensure rich.print is explicitly imported

# Assume module_call_counter exists and works as intended
import module_call_counter

# Import the robust JSON handlers from helper_general
# We assume helper_general is available in the path
try:
    from helper_general import load_json, save_json
except ImportError:
    print("[bold red]Critical Error: Cannot import load_json/save_json from helper_general. State Manager cannot function.[/bold red]")
    # Define dummy functions to prevent immediate crashes, but functionality will be broken
    def load_json(file_path: str, default_value=None):
        print(f"[red]Error: load_json unavailable. Returning default for {file_path}[/red]")
        return default_value if default_value is not None else {}
    def save_json(file_path: str, data: Any) -> bool:
        print(f"[red]Error: save_json unavailable. Cannot save data to {file_path}[/red]")
        return False

# --- Constants for Filenames ---
OPTIONS_FILENAME = "j_options.json"
FILTERS_FILENAME = "j_todoist_filters.json"
ACTIVE_TASK_FILENAME = "j_active_task.json"
COMPLETED_TASKS_LOG_FILENAME = "j_todays_completed_tasks.json"
COMPLETED_COUNT_FILENAME = "j_number_of_todays_completed_tasks.json"
DIARY_FILENAME = "j_diary.json"
GRAFT_FILENAME = "j_grafted_tasks.json"
RECURRING_ANOMALIES_LOG_FILENAME = "j_recurring_anomalies.json"

# --- Default State Values ---
DEFAULT_OPTIONS = {
    "enable_diary_prompts": "yes",
    "last_backup_timestamp": None,
    # Date string YYYY-MM-DD (Europe/London) when the all-done celebration last played
    "last_all_done_celebration_date": None,
}
DEFAULT_FILTERS = [{"id": 1, "filter": "(no due date | today | overdue) & !#Team Virtue", "isActive": 1, "project_id": None}]
DEFAULT_COMPLETED_COUNT = {"total_today": 0, "todays_date": ""}

# --- Private Helper Functions ---

def _load_data(filename: str, default_value: Any) -> Any:
    """Loads data from a JSON file using the robust helper."""
    return load_json(filename, default_value=default_value)

def _save_data(filename: str, data: Any) -> bool:
    """Saves data to a JSON file using the robust helper."""
    return save_json(filename, data)

def _get_device_id() -> str:
    """Generates a unique device identifier."""
    try:
        system_info = [
            platform.node(), platform.machine(), platform.processor(),
            str(uuid.getnode()), platform.system(),
        ]
        system_info = [info for info in system_info if info]
        if not system_info:
            return str(uuid.uuid4()) # Fallback
        unique_string = ':'.join(system_info)
        return hashlib.sha256(unique_string.encode()).hexdigest()
    except Exception as e:
        print(f"[red]Error generating device ID: {e}. Falling back to random UUID.[/red]")
        traceback.print_exc()
        return str(uuid.uuid4())

# --- Public State Management Functions ---

# --- Options State ---
def get_options() -> Dict:
    """Loads options, returning defaults if necessary."""
    return _load_data(OPTIONS_FILENAME, default_value=DEFAULT_OPTIONS)

def save_options(options_data: Dict) -> bool:
    """Saves the provided options dictionary."""
    return _save_data(OPTIONS_FILENAME, options_data)

def get_last_backup_timestamp() -> Optional[datetime.datetime]:
    """Reads the last backup timestamp from options."""
    options = get_options()
    timestamp_str = options.get("last_backup_timestamp")
    if not timestamp_str:
        return None
    try:
        dt = datetime.datetime.fromisoformat(timestamp_str)
        # Ensure timezone-aware (assume UTC if naive)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except (ValueError, TypeError):
        print(f"[red]Error parsing 'last_backup_timestamp' value ('{timestamp_str}').[/red]")
        return None

def set_last_backup_timestamp(timestamp: datetime.datetime) -> bool:
    """Sets the last backup timestamp in options."""
    options = get_options()
    # Ensure timezone-aware (UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
    else:
        timestamp = timestamp.astimezone(datetime.timezone.utc)
    options["last_backup_timestamp"] = timestamp.isoformat()
    return save_options(options)

# --- All-done Celebration Tracking ---
def get_last_all_done_celebration_date() -> Optional[str]:
    """Returns the stored date string (YYYY-MM-DD) when the all-done celebration last played."""
    options = get_options()
    value = options.get("last_all_done_celebration_date")
    return value if isinstance(value, str) and value else None

def set_last_all_done_celebration_date(date_str: str) -> bool:
    """Sets the last all-done celebration date string (YYYY-MM-DD)."""
    if not isinstance(date_str, str) or not date_str:
        return False
    options = get_options()
    options["last_all_done_celebration_date"] = date_str
    return save_options(options)

# --- Filters State ---
def get_filters() -> List[Dict]:
    """Loads Todoist filter definitions."""
    filters = _load_data(FILTERS_FILENAME, default_value=DEFAULT_FILTERS)
    if not isinstance(filters, list):
        print(f"[red]Error: Expected list in {FILTERS_FILENAME}, found {type(filters)}. Returning default.[/red]")
        return DEFAULT_FILTERS[:] # Return a copy
    return filters

def save_filters(filters_data: List[Dict]) -> bool:
    """Saves the provided list of filter definitions."""
    return _save_data(FILTERS_FILENAME, filters_data)

def _is_filter_active(value: Any) -> bool:
    """Accept common JSON encodings for active flags: 1, '1', true."""
    return value in (1, "1", True)

def get_active_filter_details() -> Tuple[Optional[str], Optional[str]]:
    """Finds the active filter and returns its query string and project_id."""
    filters = get_filters()
    for filter_data in filters:
        if isinstance(filter_data, dict) and _is_filter_active(filter_data.get("isActive")):
            if "filter" in filter_data:
                 # Use .get with default None for project_id
                return filter_data.get("filter"), filter_data.get("project_id")
            else:
                print(f"[yellow]Warning: Active filter found without 'filter' key: {filter_data}[/yellow]")
    # No active filter found or error in format
    print(f"[yellow]No active filter found in {FILTERS_FILENAME}. Using default.[/yellow]")
    default_filter_entry = DEFAULT_FILTERS[0] if DEFAULT_FILTERS else {}
    return default_filter_entry.get("filter"), default_filter_entry.get("project_id")

def toggle_active_filter() -> bool:
    """Switches the active filter to the next one in the list."""
    filters = get_filters()
    if not filters:
        print("[yellow]No filters defined to toggle.[/yellow]")
        return False

    active_index = -1
    for i, f in enumerate(filters):
        if isinstance(f, dict) and _is_filter_active(f.get("isActive")):
            active_index = i
            break

    if active_index != -1:
        filters[active_index]["isActive"] = 0 # Deactivate current
        next_index = (active_index + 1) % len(filters)
    else:
        print("[yellow]No active filter found. Activating the first one.[/yellow]")
        next_index = 0 # Activate the first one if none were active

    if isinstance(filters[next_index], dict):
        filters[next_index]["isActive"] = 1
        print(f"[cyan]Activated filter: '{filters[next_index].get('filter', 'N/A')}'[/cyan]")
        return save_filters(filters)
    else:
        print(f"[red]Cannot activate filter at index {next_index}, invalid format.[/red]")
        # Re-save potentially deactivated filter state if active_index was valid
        if active_index != -1:
             return save_filters(filters)
        return False


# --- Active Task State ---
def get_active_task() -> Optional[Dict]:
    """Loads the currently active task details, handling missing file vs. invalid data."""
    # <<< MODIFIED: Check file existence first >>>
    if not os.path.exists(ACTIVE_TASK_FILENAME):
        # File doesn't exist, indicating no active task is set (normal after clearing).
        return None

    # File exists, now attempt to load and validate its content.
    task = _load_data(ACTIVE_TASK_FILENAME, default_value=None) # Default None if load fails

    if task is not None:
        # Data was loaded, validate its structure.
        if not isinstance(task, dict):
            # Loaded data is not a dictionary.
            print(f"[yellow]Warning: Invalid data type found in {ACTIVE_TASK_FILENAME}. Expected dict, got {type(task).__name__}. Data: {task}. Clearing file and ignoring.[/yellow]")
            clear_active_task() # Remove the corrupt file.
            return None
        elif "task_id" not in task:
            # Loaded data is a dictionary but missing the essential 'task_id'.
            print(f"[yellow]Warning: Invalid data structure in {ACTIVE_TASK_FILENAME}. Missing 'task_id' key. Data: {task}. Clearing file and ignoring.[/yellow]")
            clear_active_task() # Remove the corrupt file.
            return None
        # If validation passes, the loaded 'task' dictionary is returned below.
    elif task is None and os.path.exists(ACTIVE_TASK_FILENAME):
        # Edge case: File exists, but _load_data returned None (e.g., JSON decode error within load_json).
        print(f"[yellow]Warning: Could not load data from existing file {ACTIVE_TASK_FILENAME} (possibly corrupted). Clearing file and ignoring.[/yellow]")
        clear_active_task() # Remove the corrupt file.
        return None
    # <<< END MODIFICATION >>>

    # Return the validated task dictionary or None if the file didn't exist initially.
    return task

def set_active_task(task_details: Dict) -> bool:
    """Saves the provided task details as the active task, adding device ID and timestamp."""
    task_details["device_id"] = _get_device_id()
    task_details["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return _save_data(ACTIVE_TASK_FILENAME, task_details)

def clear_active_task() -> bool:
    """Removes the active task file."""
    if os.path.exists(ACTIVE_TASK_FILENAME):
        try:
            os.remove(ACTIVE_TASK_FILENAME)
            # print(f"[dim]Cleared active task file: {ACTIVE_TASK_FILENAME}[/dim]") # Optional debug
            return True
        except OSError as e:
            print(f"[red]Error removing active task file {ACTIVE_TASK_FILENAME}: {e}[/red]")
            return False
    return True # File already doesn't exist

def verify_active_task_device() -> bool:
    """Checks if the active task's device ID matches the current device."""
    active_task = get_active_task() # Uses the refined getter
    if not active_task:
        # No active task is set (file missing or cleared due to invalid data), so no device mismatch.
        return True

    task_device_id = active_task.get("device_id")
    current_device_id = _get_device_id()

    if task_device_id and task_device_id != current_device_id:
        last_updated_str = active_task.get("last_updated", "Unknown time")
        task_name = active_task.get("task_name", "Unknown task")
        print("[bold red]Warning: Active task mismatch![/bold red]")
        print(f"  Task: '{task_name}'")
        print(f"  Last updated on a different device ({last_updated_str}).")
        print("[yellow]Recommendation:[/yellow] Refresh tasks or set a new active task on *this* device before proceeding.")
        return False
    # Active task exists and device ID matches, or task has no device ID (legacy).
    return True


# --- Completed Tasks Log State ---
def get_completed_tasks_log() -> List[Dict]:
    """Loads the log of completed tasks."""
    tasks = _load_data(COMPLETED_TASKS_LOG_FILENAME, default_value=[])
    if not isinstance(tasks, list):
        print(f"[yellow]Warning: Invalid data in {COMPLETED_TASKS_LOG_FILENAME}. Returning empty list.[/yellow]")
        return []
    return tasks

def save_completed_tasks_log(tasks_list: List[Dict]) -> bool:
    """Saves the entire list of completed tasks."""
    return _save_data(COMPLETED_TASKS_LOG_FILENAME, tasks_list)

def add_completed_task_log(task_entry: Dict) -> bool:
    """Adds a new task entry to the completed tasks log, assigning an ID."""
    tasks = get_completed_tasks_log()
    # Find the next available ID
    existing_ids = set(t.get('id', 0) for t in tasks if isinstance(t.get('id'), int))
    new_id = 1
    while new_id in existing_ids:
        new_id += 1
    task_entry['id'] = new_id
    # Add timestamp if not present
    if 'datetime' not in task_entry:
        task_entry['datetime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tasks.append(task_entry)
    return save_completed_tasks_log(tasks)

def purge_old_completed_tasks_log(days_to_keep: int = 30) -> int:
    """Removes entries older than 'days_to_keep' from the completed tasks log."""
    tasks = get_completed_tasks_log()
    original_count = len(tasks)
    now = datetime.datetime.now()
    cutoff_date = (now - datetime.timedelta(days=days_to_keep)).date()
    purged_tasks = []
    parse_error_count = 0

    for task in tasks:
        if not isinstance(task, dict):
            print(f"[yellow]Skipping invalid entry during purge: {task}[/yellow]")
            purged_tasks.append(task) # Keep invalid entries for now
            continue

        datetime_str = task.get('datetime')
        if not isinstance(datetime_str, str):
            print(f"[yellow]Skipping task with missing/invalid datetime: {task.get('task_name', 'N/A')}[/yellow]")
            purged_tasks.append(task)
            continue

        try:
            task_date = parse(datetime_str).date()
            if task_date >= cutoff_date:
                purged_tasks.append(task)
        except (ValueError, TypeError):
            parse_error_count += 1
            purged_tasks.append(task) # Keep tasks with parse errors

    if parse_error_count > 0:
         print(f"[yellow]Could not parse datetime for {parse_error_count} tasks during purge.[/yellow]")

    purged_count = original_count - len(purged_tasks)
    if purged_count > 0 or parse_error_count > 0: # Save if changes were made
        if save_completed_tasks_log(purged_tasks):
            if purged_count > 0:
                 print(f"[cyan]Purged {purged_count} completed tasks older than {days_to_keep} days.[/cyan]")
        else:
            print(f"[red]Failed to save purged completed tasks log.[/red]")
            return -1 # Indicate save failure

    return purged_count


# --- Recurring Anomalies Log State ---
def get_recurring_anomalies_log() -> List[Dict]:
    """Loads the log of recurring-task anomalies (e.g. completion not advancing due)."""
    entries = _load_data(RECURRING_ANOMALIES_LOG_FILENAME, default_value=[])
    if not isinstance(entries, list):
        print(f"[yellow]Warning: Invalid data in {RECURRING_ANOMALIES_LOG_FILENAME}. Returning empty list.[/yellow]")
        return []
    return entries


def save_recurring_anomalies_log(entries: List[Dict]) -> bool:
    return _save_data(RECURRING_ANOMALIES_LOG_FILENAME, entries)


def add_recurring_anomaly_log(entry: Dict) -> bool:
    """Append an anomaly entry with an ID, UTC timestamp, and device ID."""
    if not isinstance(entry, dict):
        return False

    entries = get_recurring_anomalies_log()
    existing_ids = set(e.get("id", 0) for e in entries if isinstance(e, dict) and isinstance(e.get("id"), int))
    new_id = 1
    while new_id in existing_ids:
        new_id += 1

    entry = dict(entry)
    entry["id"] = new_id
    entry.setdefault("datetime_utc", datetime.datetime.now(datetime.timezone.utc).isoformat())
    entry.setdefault("device_id", _get_device_id())

    entries.append(entry)
    return save_recurring_anomalies_log(entries)


# --- Completed Count State ---
def get_completed_tasks_count() -> int:
    """Gets the number of tasks completed today."""
    today_str = datetime.date.today().isoformat()
    data = _load_data(COMPLETED_COUNT_FILENAME, default_value=DEFAULT_COMPLETED_COUNT)

    if not isinstance(data, dict) or data.get("todays_date") != today_str:
        return 0 # Not today's count or invalid data
    return int(data.get("total_today", 0)) # Ensure integer

def update_completed_tasks_count() -> bool:
    """Increments today's completed task count, resetting if it's a new day."""
    today_str = datetime.date.today().isoformat()
    data = _load_data(COMPLETED_COUNT_FILENAME, default_value=DEFAULT_COMPLETED_COUNT)

    if not isinstance(data, dict) or "todays_date" not in data or "total_today" not in data:
        # Reset invalid data
        data = {"total_today": 1, "todays_date": today_str}
    elif data.get("todays_date") == today_str:
        # Increment today's count
        data["total_today"] = int(data.get("total_today", 0)) + 1
    else:
        # Reset for new day
        data = {"total_today": 1, "todays_date": today_str}

    return _save_data(COMPLETED_COUNT_FILENAME, data)


# --- Diary State ---
def get_diary_data() -> Dict:
    """Loads the entire diary data."""
    diary = _load_data(DIARY_FILENAME, default_value={})
    if not isinstance(diary, dict):
         print(f"[yellow]Warning: Invalid data in {DIARY_FILENAME}. Returning empty dict.[/yellow]")
         return {}
    return diary

def save_diary_data(diary_data: Dict) -> bool:
    """Saves the entire diary data object."""
    return _save_data(DIARY_FILENAME, diary_data)

def update_diary_entry(date_str: str, entry_data: Dict) -> bool:
    """Updates or creates the diary entry for a specific date string (YYYY-MM-DD)."""
    diary = get_diary_data()
    # Ensure date entry exists and is a dictionary
    if date_str not in diary or not isinstance(diary[date_str], dict):
        diary[date_str] = {}
    diary[date_str].update(entry_data) # Merge new data into existing entry
    return save_diary_data(diary)

def update_todays_objective(objective: str) -> bool:
    """Updates the 'overall_objective' for today's diary entry."""
    if not objective or not isinstance(objective, str):
        print("[red]Invalid objective provided.[/red]")
        return False
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    diary_data = get_diary_data()
    if today_str not in diary_data or not isinstance(diary_data[today_str], dict):
        diary_data[today_str] = {}
    diary_data[today_str]['overall_objective'] = objective
    if save_diary_data(diary_data):
        print(f"Today's overall objective updated: [gold1]{objective}[/gold1]")
        return True
    else:
        print("[red]Failed to save updated objective to diary file.[/red]")
        return False

def find_most_recent_objective(start_date: datetime.date, lookback_days: int = 30) -> Tuple[Optional[str], Optional[datetime.date]]:
    """Finds the most recent non-empty objective looking back from start_date."""
    diary_data = get_diary_data()
    current_date = start_date
    for _ in range(lookback_days):
        date_str = current_date.strftime("%Y-%m-%d")
        entry = diary_data.get(date_str)
        if isinstance(entry, dict):
            objective = entry.get('overall_objective')
            if objective and isinstance(objective, str) and objective.strip():
                return objective.strip(), current_date
        current_date -= datetime.timedelta(days=1)
    return None, None

# --- Graft State ---
def get_grafted_tasks() -> Optional[List[Dict]]:
    """Loads grafted tasks. Returns None if file doesn't exist, or empty list if invalid."""
    if not os.path.exists(GRAFT_FILENAME):
        return None # Indicate file doesn't exist

    tasks = _load_data(GRAFT_FILENAME, default_value=[])
    if not isinstance(tasks, list):
        print(f"[red]Error reading graft file '{GRAFT_FILENAME}'. Invalid format. Clearing file.[/red]")
        clear_grafted_tasks_file()
        return [] # Return empty list after clearing invalid file
    if not tasks: # File exists but is empty
         clear_grafted_tasks_file() # Clean up empty file
         return []
    # Validate entries minimally
    valid_tasks = []
    has_invalid = False
    for task in tasks:
        if isinstance(task, dict) and "task_name" in task:
            valid_tasks.append(task)
        else:
            has_invalid = True
            print(f"[yellow]Warning: Invalid entry found in graft file: {task}[/yellow]")

    if has_invalid:
        # Optionally save back only the valid tasks, or just return them
        print("[yellow]Returning only valid entries from graft file.[/yellow]")

    return valid_tasks


def clear_grafted_tasks_file() -> bool:
    """Removes the graft file if it exists."""
    if os.path.exists(GRAFT_FILENAME):
        try:
            os.remove(GRAFT_FILENAME)
            # print(f"[cyan]Removed graft file: {GRAFT_FILENAME}[/cyan]") # Optional confirmation
            return True
        except OSError as e:
            print(f"[red]Error removing graft file {GRAFT_FILENAME}: {e}[/red]")
            return False
    return True # File already doesn't exist


# --- Apply Call Counter ---
# Decorate all public functions in this module
if 'module_call_counter' in globals() and hasattr(module_call_counter, 'apply_call_counter_to_all'):
     module_call_counter.apply_call_counter_to_all(globals(), __name__)
else:
     print("[yellow]Warning: module_call_counter not fully available in state_manager.[/yellow]")
