# File: helper_todoist_part1.py (Imports Only)
import dateutil.parser
import datetime
import sys
import signal
import pyfiglet
import time
import module_call_counter
from dateutil.parser import parse
from datetime import timedelta, timezone
from rich import print
import state_manager
import os # Needed for read_long_term_tasks check
import json # Needed for read_long_term_tasks check
from typing import Optional, Tuple # <<< ADDED: Import Optional and Tuple

# <<< REMOVED: Constants for j_todoist_filters.json, j_active_task.json, etc. >>>

# --- Functions ---

def change_active_task():
    """Toggles the active filter using the state manager."""
    # <<< MODIFIED: Use state_manager.toggle_active_filter >>>
    if not state_manager.toggle_active_filter():
        print("[red]Failed to toggle active filter.[/red]")
    # Success/failure message handled by state_manager or logged above

# <<< REMOVED: get_device_id function (logic moved to state_manager) >>>

# <<< MODIFIED: add_to_active_task_file becomes a wrapper for state_manager.set_active_task >>>
def add_to_active_task_file(task_name: str, task_id: str, task_due: Optional[str]):
    """Sets the active task details using the state manager."""
    active_task_details = {
        "task_name": task_name,
        "task_id": task_id,
        "task_due": task_due, # Pass due info (can be None)
        # device_id and last_updated are added by state_manager
    }
    # <<< MODIFIED: Call state_manager >>>
    if not state_manager.set_active_task(active_task_details):
        print(f"[red]Failed to save active task: {task_name}[/red]")


def get_active_filter() -> tuple[Optional[str], Optional[str]]:
    """Gets the active filter query string and project ID from the state manager."""
    # <<< MODIFIED: Call state_manager >>>
    return state_manager.get_active_filter_details()


# <<< KEPT: read_long_term_tasks - Assumed not managed by state_manager for now >>>
def read_long_term_tasks(filename="j_long_term_tasks.json"): # Default filename added
    """Reads tasks from a specified JSON file (likely deprecated/managed elsewhere)."""
    if not os.path.exists(filename): # Keep os import for this specific function check
        print(f"[yellow]Long term tasks file '{filename}' not found. Creating empty file.[/yellow]")
        try:
            with open(filename, "w") as file:
                json.dump([], file, indent=2) # Keep json import for this specific function
            return [] # Return empty list immediately
        except IOError as e:
            print(f"[red]Error creating long term tasks file {filename}: {e}[/red]")
            return [] # Return empty list on error

    try:
        with open(filename, "r") as file:
            tasks = json.load(file)
        if not isinstance(tasks, list):
            print(f"[red]Error: Expected a list in {filename}, found {type(tasks)}. Returning empty list.[/red]")
            return []
        return tasks
    except json.JSONDecodeError:
        print(f"[red]Error reading JSON from {filename}. Returning empty list.[/red]")
        return []
    except IOError as e:
        print(f"[red]Error accessing long term tasks file {filename}: {e}. Returning empty list.[/red]")
        return []
    except Exception as e:
        print(f"[red]An unexpected error occurred reading long term tasks: {e}. Returning empty list.[/red]")
        # Log stack trace if needed
        # import traceback
        # traceback.print_exc()
        return []
# Re-add necessary imports if read_long_term_tasks is kept:
import os
import json


# --- Task Completion ---
def complete_todoist_task_by_id(api, task_id, skip_logging=False):
    """Completes a Todoist task by its ID, logging via state_manager."""
    # Timeout logic remains the same
    if hasattr(signal, 'SIGALRM'):
        def handler(signum, frame):
            raise TimeoutError(f"Todoist API call timed out after 30 seconds for task ID {task_id}")
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(30)
    else:
        print("[yellow]Warning: signal.SIGALRM not available. Cannot enforce timeout.[/yellow]")

    try:
        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]No task found with ID: {task_id}[/yellow]")
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)
            return False

        task_name = task.content
        success = api.close_task(task_id=task_id)

        if hasattr(signal, 'SIGALRM'): signal.alarm(0) # Disable alarm after API call

        if success:
            if not skip_logging:
                # <<< MODIFIED: Call state_manager to log >>>
                log_entry = {"task_name": task_name} # Let state manager handle timestamp/ID
                state_manager.add_completed_task_log(log_entry)
                # Note: We don't check the return value of logging here, assume best effort

            status = 'SKIPPED' if skip_logging else 'COMPLETED'
            print(f"[yellow]{task_name}[/yellow] -- {status}")
            return True
        else:
            print(f"[red]Todoist API indicated failure to close task ID: {task_id}.[/red]")
            return False

    except TimeoutError as te:
        print(f"[red]Error: {te}[/red]")
        if hasattr(signal, 'SIGALRM'): signal.alarm(0)
        return False
    except Exception as error:
        print(f"[red]Error completing task ID {task_id}: {error}[/red]")
        if hasattr(signal, 'SIGALRM'): signal.alarm(0)
        # import traceback; traceback.print_exc() # Optional detailed logging
        return False
    # No 'finally' needed here as alarm is cleared inside try/except blocks

def complete_active_todoist_task(api, skip_logging=False):
    """Completes the active Todoist task using state_manager."""
    max_retries = 3
    retry_delay = 1

    if hasattr(signal, 'SIGALRM'):
        def handler(signum, frame):
            raise TimeoutError("Todoist API call timed out after 5 seconds for active task")
    # else: # Warning printed elsewhere

    # 1. Get Active Task from State Manager
    active_task = state_manager.get_active_task()
    if not active_task:
        print(f"[red]Error: No active task found to complete.[/red]")
        return False

    task_id = active_task.get("task_id")
    task_name = active_task.get("task_name")
    if not task_id or not task_name:
        print(f"[red]Error: Invalid active task data (missing ID or name).[/red]")
        state_manager.clear_active_task() # Clear invalid task
        return False

    # 2. API Interaction Loop
    for attempt in range(max_retries):
        try:
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(5)

            task = api.get_task(task_id)
            if not task:
                print(f"[yellow]Active task (ID: {task_id}, Name: '{task_name}') no longer exists.[/yellow]")
                state_manager.clear_active_task() # Clear stale active task
                if hasattr(signal, 'SIGALRM'): signal.alarm(0)
                return False # Task gone

            success = api.close_task(task_id=task_id)
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)

            if success:
                if not skip_logging:
                    # <<< MODIFIED: Call state_manager to log >>>
                    log_entry = {"task_name": task_name}
                    state_manager.add_completed_task_log(log_entry)
                    # <<< MODIFIED: Call state_manager to update count >>>
                    state_manager.update_completed_tasks_count()

                status = 'SKIPPED' if skip_logging else 'COMPLETED'
                print(f"[yellow]{task_name}[/yellow] -- {status}")
                state_manager.clear_active_task() # Clear active task on success
                return True
            else:
                 print(f"[yellow]Attempt {attempt + 1}: API failed closing task ID {task_id}. Retrying...[/yellow]")

        except TimeoutError as te:
             if hasattr(signal, 'SIGALRM'): signal.alarm(0)
             print(f"[yellow]Attempt {attempt + 1}: API call timed out. {te}. Retrying...[/yellow]")
        except Exception as error:
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)
            print(f"[red]Attempt {attempt + 1}: Error completing task ID {task_id}: {error}[/red]")

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    print(f"[red]Failed to complete active task '{task_name}' (ID: {task_id}) after {max_retries} attempts.[/red]")
    return False

# <<< REMOVED: update_completed_tasks_count function (logic moved to state_manager) >>>

def postpone_due_date(api, user_message):
    """Postpones the active task's due date using state_manager."""
    # 1. Get Active Task
    active_task = state_manager.get_active_task()
    if not active_task:
        print("[red]No active task set. Cannot postpone.[/red]")
        return

    task_id = active_task.get("task_id")
    content = active_task.get("task_name") # Use name from state for initial message
    if not task_id or not content:
        print(f"[red]Error: Invalid active task data.[/red]")
        state_manager.clear_active_task()
        return

    # 2. Extract Due String
    due_string = user_message.replace("postpone ", "", 1).strip()
    if not due_string:
        print("[yellow]No postpone date/time provided. Usage: postpone <due_string>[/yellow]")
        return
    if due_string.isdigit() and len(due_string) == 4:
        print("[red]Invalid time format. Use formats like 'tomorrow 9am', etc.[/red]")
        return

    try:
        # 3. Get Full Task Details from API
        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]Task ID {task_id} (from active task) not found in Todoist.[/yellow]")
            state_manager.clear_active_task()
            return

        # 4. Handle Recurring vs. Non-Recurring
        is_recurring = task.due and task.due.is_recurring
        if is_recurring:
            print(f"[cyan]Postponing recurring task '{task.content}' by creating new instance.[/cyan]")
            close_success = api.close_task(task_id=task.id)
            # Log completion (not skipped) - uses state manager
            if close_success:
                 log_entry = {"task_name": task.content}
                 state_manager.add_completed_task_log(log_entry)
                 state_manager.update_completed_tasks_count()
            else:
                 print(f"[yellow]Warning: Failed to close original recurring task ID {task.id}.[/yellow]")

            new_task_args = { "content": task.content, "due_string": due_string,
                              "description": task.description, "priority": task.priority }
            if hasattr(task, "project_id") and task.project_id:
                new_task_args["project_id"] = task.project_id
            new_task = api.add_task(**new_task_args)

            if new_task:
                print(f"[green]Recurring task effectively postponed to '{due_string}'.[/green]")
                # Clear the old active task, don't set the new one as active automatically
                state_manager.clear_active_task()
            else:
                print(f"[red]Error: Failed to create new task instance for '{task.content}'.[/red]")
        else:
            # Update existing task
            print(f"[cyan]Postponing non-recurring task '{task.content}' to '{due_string}'.[/cyan]")
            updated_task = api.update_task(task_id=task.id, due_string=due_string)
            if updated_task:
                print(f"[green]Task postponed successfully to '{due_string}'.[/green]")
                # Update active task file with new due info
                # <<< MODIFIED: Use state_manager wrapper function >>>
                add_to_active_task_file(updated_task.content, updated_task.id, updated_task.due.datetime if updated_task.due else None)
            else:
                print(f"[red]Error: Failed to update task '{task.content}' due date.[/red]")

    except Exception as error:
        print(f"[red]An unexpected error occurred during postpone: {error}[/red]")
        # import traceback; traceback.print_exc()


def get_active_task() -> Optional[dict]:
    """Reads and returns the active task data using the state manager."""
    # <<< MODIFIED: Call state_manager >>>
    return state_manager.get_active_task()

# <<< MODIFIED: verify_device_id_before_command becomes a wrapper for state_manager >>>
def verify_device_id_before_command() -> bool:
    """Checks if the active task was last updated on the current device using state_manager."""
    # <<< MODIFIED: Call state_manager >>>
    return state_manager.verify_active_task_device()


# <<< KEPT: update_task_due_date (No file I/O) >>>
def update_task_due_date(api, task_id, due_string):
    """Updates the due date of a specific task."""
    try:
        updated_task = api.update_task(task_id=task_id, due_string=due_string)
        if updated_task:
             print(f"Task ID {task_id} due date updated to '{due_string}'.")
             return True
        else:
             print(f"[red]Failed to update due date for task ID {task_id} via API.[/red]")
             return False
    except Exception as e:
        print(f"[red]Error updating due date for task ID {task_id}: {e}[/red]")
        return False


# <<< KEPT: get_full_task_details (No file I/O) >>>
def get_full_task_details(api, task_id):
    """Fetches the full details of a task by its ID."""
    try:
        task = api.get_task(task_id)
        return task
    except Exception as e:
        print(f"[red]Error fetching full details for task ID {task_id}: {e}[/red]")
        return None


def check_and_update_task_due_date(api, user_message):
    """Checks the active task (via state_manager) and updates its due date."""
    try:
        # 1. Get Active Task
        # <<< MODIFIED: Use state_manager >>>
        active_task = state_manager.get_active_task()
        if not active_task:
            print("[red]No active task set. Cannot update due date.[/red]")
            return False

        task_id = active_task.get("task_id")
        if not task_id:
             print(f"[red]Error: 'task_id' missing in active task data.[/red]")
             return False

        # 2. Extract Due String
        due_string = user_message.replace("time ", "", 1).strip()
        if not due_string:
            print("[yellow]No due date/time provided. Usage: time <due_string>[/yellow]")
            return False
        if due_string.isdigit() and len(due_string) == 4:
            print("[red]Invalid time format. Use formats like '9am', 'tomorrow 14:00', etc.[/red]")
            return False

        # 3. Get Original Task Details
        original_task = get_full_task_details(api, task_id)
        if not original_task:
            print(f"[yellow]Active task ID {task_id} not found in Todoist.[/yellow]")
            state_manager.clear_active_task() # Clear stale task
            return False

        # Display, Confirmation, Update, Verification logic remains largely the same...
        print("\n[cyan]Original task state:[/cyan]")
        print(f"  Content: {original_task.content}")
        print(f"  Due: {original_task.due.string if original_task.due else 'None'}")
        print(f"  Recurring: {original_task.due.is_recurring if original_task.due else 'No'}")
        print(f"  Description: {'Yes' if original_task.description else 'No'}")

        is_recurring = original_task.due and original_task.due.is_recurring
        if is_recurring:
            response = input(f"Task '{original_task.content}' is recurring. Modify date? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled.")
                return False

        print(f"\n[cyan]Attempting update task '{original_task.content}' to due: '{due_string}'[/cyan]")
        try:
            updated_task = api.update_task(task_id=task_id, due_string=due_string)
            if not updated_task:
                 print("[red]API call did not return updated task details. Update might have failed.[/red]")
                 return False

            print("[cyan]Verifying update...[/cyan]")
            time.sleep(1)
            verification_task = api.get_task(task_id)

            if verification_task and verification_task.due and verification_task.due.string:
                print(f"[green]Task due date updated. Verified due: '{verification_task.due.string}'[/green]")
                # <<< MODIFIED: Use wrapper to update active task file >>>
                add_to_active_task_file(verification_task.content, verification_task.id, verification_task.due.datetime if verification_task.due else None)
                return True
            else:
                if is_recurring:
                    print(f"[yellow]Recurring task update initiated. Verification inconclusive.[/yellow]")
                    add_to_active_task_file(original_task.content, task_id, None)
                    return True
                else:
                    print("[red]Failed to verify task update.[/red]")
                    return False

        except Exception as api_error:
            print(f"[red]Error during Todoist API update call: {api_error}[/red]")
            return False

    except Exception as error:
        print(f"[red]An unexpected error occurred checking/updating task due date: {error}[/red]")
        return False


def delete_todoist_task(api):
    """Deletes the active Todoist task using state_manager."""
    # 1. Read Active Task
    # <<< MODIFIED: Use state_manager >>>
    active_task = state_manager.get_active_task()
    if not active_task:
        print(f"[red]Error: No active task found to delete.[/red]")
        return False

    task_id = active_task.get("task_id")
    task_name = active_task.get("task_name", "Unknown task")
    if not task_id:
        print(f"[red]Error: Invalid active task data (missing ID). Cannot delete.[/red]")
        state_manager.clear_active_task() # Clear invalid task
        return False

    try:
        # 2. Verify Task Exists (Optional)
        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]Task ID {task_id} ('{task_name}') not found. Already deleted?[/yellow]")
            # <<< MODIFIED: Clear active task via state_manager >>>
            state_manager.clear_active_task()
            return True # Success if already gone

        # 3. Delete Task
        success = api.delete_task(task_id=task_id)

        if success:
            print(f"\n[bright_red]'{task_name}' (ID: {task_id}) deleted.[/bright_red]\n")
            # <<< MODIFIED: Clear active task via state_manager >>>
            state_manager.clear_active_task()
            return True
        else:
            print(f"[red]Failed to delete task '{task_name}' (ID: {task_id}) via API.[/red]")
            return False

    except Exception as error:
        print(f"[red]An unexpected error occurred deleting task: {error}[/red]")
        return False


# <<< KEPT: format_due_time (No file I/O) >>>
def format_due_time(due_time_str, timezone):
    """Formats a due date/time string into a user-friendly format in the specified timezone."""
    if due_time_str is None: return ""
    try:
        due_time = dateutil.parser.parse(due_time_str)
        if not isinstance(timezone, datetime.tzinfo):
             print(f"[red]Error: Invalid timezone object: {type(timezone)}[/red]")
             return due_time_str
        localized_due_time = due_time.astimezone(timezone)
        friendly_due_time = localized_due_time.strftime("%Y-%m-%d %H:%M")
        return friendly_due_time
    except (ValueError, TypeError) as e:
        print(f"[yellow]Warning: Could not format due time '{due_time_str}': {e}[/yellow]")
        return due_time_str
    except Exception as e:
        print(f"[red]Unexpected error formatting due time '{due_time_str}': {e}[/red]")
        return due_time_str


def print_completed_tasks_count():
    """Reads and prints the number of tasks completed today using state_manager."""
    # <<< MODIFIED: Call state_manager >>>
    count = state_manager.get_completed_tasks_count()
    print(f"Tasks completed today: {count}")


# <<< MODIFIED: log_completed_task becomes a simple wrapper >>>
def log_completed_task(task_name):
    """Logs a completed task via the state manager."""
    log_entry = {"task_name": task_name}
    # <<< MODIFIED: Call state_manager >>>
    if not state_manager.add_completed_task_log(log_entry):
        print(f"[red]Failed to log completed task: {task_name}[/red]")


# <<< KEPT: update_recurrence_patterns (No file I/O relevant to state_manager) >>>
def update_recurrence_patterns(api):
    """Updates recurring long tasks using 'every ' to 'every! '."""
    updated_count = 0
    error_count = 0
    try:
        import helper_todoist_long # Import locally
        project_id = helper_todoist_long.get_long_term_project_id(api)
        if not project_id: return

        tasks = api.get_tasks(project_id=project_id)
        if tasks is None:
             print("[yellow]Could not retrieve 'Long Term Tasks'.[/yellow]")
             return

        tasks_to_update = []
        for task in tasks:
            if task.due and hasattr(task.due, 'string') and isinstance(task.due.string, str):
                due_string = task.due.string.lower()
                if task.due.is_recurring and 'every ' in due_string and 'every!' not in due_string:
                    tasks_to_update.append(task)

        if not tasks_to_update: return

        print(f"[cyan]Found {len(tasks_to_update)} long tasks needing 'every ' -> 'every!'.[/cyan]")
        for task in tasks_to_update:
            try:
                current_due_string = task.due.string
                new_due_string = current_due_string.replace('every ', 'every! ')
                if new_due_string == current_due_string: continue

                print(f"  Updating: '{task.content}' ('{current_due_string}' -> '{new_due_string}')")
                update_success = api.update_task(task_id=task.id, due_string=new_due_string)
                if update_success:
                    updated_count += 1
                else:
                    print(f"  [red]API failed updating task ID {task.id}.[/red]")
                    error_count += 1
            except Exception as e:
                print(f"[red]Error updating task '{task.content}': {e}[/red]")
                error_count += 1

        if updated_count > 0 or error_count > 0:
             print(f"[cyan]Recurrence update finished. Updated: {updated_count}, Errors: {error_count}[/cyan]")

    except Exception as e:
        print(f"[red]Unexpected error during recurrence update: {e}[/red]")


# Apply call counter decorator (No changes needed)
module_call_counter.apply_call_counter_to_all(globals(), __name__)