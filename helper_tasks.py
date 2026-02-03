# File: helper_tasks.py
# <<< REMOVED: os, json imports >>>
import time # time is not used, can be removed unless planned for future use
import module_call_counter
# <<< REMOVED: helper_general import (not used) >>>
# <<< REMOVED: helper_todoist_part1 import (not used) >>>
from datetime import datetime, timedelta # Keep datetime
from rich import print
import state_manager # <<< ADDED: Import the state manager

# --- Constants ---
# <<< REMOVED: COMPLETED_TASKS_FILENAME constant >>>

# --- Functions ---

def _tomorrow_at_9am_local(now: datetime) -> datetime:
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)


def add_completed_task(user_message: str):
    """Logs an ad-hoc completed task using the state manager."""
    # Remove the "xx " prefix from the user message
    task_content = user_message[3:].strip()
    if not task_content:
        print("[yellow]No task content provided for 'xx' command.[/yellow]")
        return

    scheduled_datetime: datetime | None = None
    if task_content.lower().startswith("(t)"):
        task_content = task_content[3:].strip()
        if not task_content:
            print("[yellow]No task content provided after '(t)'.[/yellow]")
            return
        scheduled_datetime = _tomorrow_at_9am_local(datetime.now())

    # Get the current timestamp (handled by state_manager, but can be added here if specific format is needed)
    # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # State manager adds this

    # Create the task entry dictionary (without ID, state_manager assigns it)
    task_entry = {
        # "datetime": timestamp, # Let state_manager handle timestamping
        "task_name": task_content
    }
    if scheduled_datetime is not None:
        task_entry["datetime"] = scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S")

    # <<< MODIFIED: Call state_manager to add the entry >>>
    if state_manager.add_completed_task_log(task_entry):
        # State manager now assigns the ID, so we can't easily print it here unless add_completed_task_log returns it
        # Simplifiying the confirmation message
        if scheduled_datetime is not None:
            when = scheduled_datetime.strftime("%Y-%m-%d %H:%M")
            print(f"[bright_magenta]Ad-hoc task logged as completed at {when}:[/bright_magenta] {task_content}")
        else:
            print(f"[bright_magenta]Ad-hoc task added to completed daily tasks:[/bright_magenta] {task_content}")
    else:
        print(f"[red]Failed to log ad-hoc task: {task_content}[/red]")


def display_completed_tasks():
    """Displays tasks logged as completed today via the state manager."""
    # <<< MODIFIED: Get tasks from state_manager >>>
    completed_tasks = state_manager.get_completed_tasks_log()

    if not completed_tasks:
        print("[yellow]No completed tasks found in the log.[/yellow]")
        return

    print("[bold cyan]--- Completed Tasks Log ---[/bold cyan]")
    # Filter for today's tasks if needed, although the file name implies only today's
    # For robustness, let's filter here, assuming the log might contain older tasks
    # despite the purge logic existing in state_manager.
    today_str = datetime.now().strftime("%Y-%m-%d")
    todays_tasks = []
    parse_error = False
    for task in completed_tasks:
         dt_str = task.get('datetime')
         if isinstance(dt_str, str) and dt_str.startswith(today_str):
              todays_tasks.append(task)
         elif isinstance(dt_str, str):
             pass # Task from another day
         else:
             parse_error = True # Found task with invalid/missing datetime

    if parse_error:
         print("[yellow]Warning: Some tasks in the log have missing/invalid datetimes.[/yellow]")

    if not todays_tasks:
         print("[dim]No tasks logged as completed today.[/dim]")
         print("-----------------------------")
         return

    # Sort today's tasks by time for display
    try:
        todays_tasks.sort(key=lambda x: datetime.strptime(x.get('datetime', ''), "%Y-%m-%d %H:%M:%S") if isinstance(x.get('datetime'), str) else datetime.min)
    except ValueError:
        print("[yellow]Warning: Error sorting completed tasks by time. Order may be incorrect.[/yellow]")

    # Print sorted tasks for today
    for task in todays_tasks:
        dt_str = task.get('datetime', '????-??-?? ??:??:??')
        time_part = dt_str.split(' ')[-1] if ' ' in dt_str else dt_str # Show only time part
        name = task.get('task_name', '[Unknown Task]')
        print(f"{time_part} - {name}")

    print("-----------------------------")


# --- reset_task_indices (Remains unchanged as it operates on a passed list) ---
# Note: This function is not called anywhere in the provided code.
# If intended to modify the persistent log, its logic should move to state_manager.
# Keeping it as is for now based on the current structure.
def reset_task_indices(tasks: list):
    """Sorts tasks by added date and resets 'index' key. Operates on the provided list."""
    # Ensure datetime objects for sorting
    def get_sort_key(task):
        try:
            added_str = task.get("added")
            if isinstance(added_str, str):
                return datetime.strptime(added_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError, KeyError):
            pass # Handle missing/invalid 'added' key or format
        return datetime.min # Default sort key for errors

    # Sort tasks in-place
    tasks.sort(key=get_sort_key)

    # Reset task indices (assuming 'index' is a desired key on these tasks)
    for i, task in enumerate(tasks):
        task["index"] = i


# --- add_to_completed_tasks (Refactored for state_manager) ---
# Note: This function seems similar to add_completed_task_log in state_manager.
# It adds a "(Deleted long task)" prefix. Consider merging this logic.
# Refactoring to use state_manager.add_completed_task_log.
def add_to_completed_tasks(task: dict):
    """Logs a task (e.g., a deleted long task) to the completed tasks log via state_manager."""
    if not isinstance(task, dict) or 'task_name' not in task:
         print("[yellow]Invalid task data passed to add_to_completed_tasks.[/yellow]")
         return

    original_task_name = task.get('task_name', 'Unknown Task')

    # Prepare the entry for the state manager
    log_entry = {
        # Let state_manager handle datetime and ID
        "task_name": f"(Deleted long task) {original_task_name}"
    }

    # <<< MODIFIED: Call state_manager >>>
    if not state_manager.add_completed_task_log(log_entry):
        print(f"[red]Failed to log completed (deleted long) task: {original_task_name}[/red]")
    # else: # Success message could be added, but might be verbose
        # print(f"[cyan]Logged deleted long task: {original_task_name}[/cyan]")


# Apply call counter decorator (No changes needed)
module_call_counter.apply_call_counter_to_all(globals(), __name__)
