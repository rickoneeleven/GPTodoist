# File: helper_todoist_long.py
import module_call_counter
from rich import print
from datetime import datetime, timedelta, timezone, tzinfo, time # Import time class as well
import re
import pytz # Ensure pytz is imported
from dateutil.parser import parse
import helper_tasks
import time as time_module  # Import time module with alias to avoid conflicts
import traceback

# Import API type hint if needed
# from todoist_api_python.api import TodoistAPI


def get_long_term_project_id(api):
    """Get the ID of the 'Long Term Tasks' project, returns None if not found or error occurs."""
    project_name = "Long Term Tasks" # Store in variable for consistency
    try:
        projects = api.get_projects()
        if projects is None: # API call might return None on error
             print(f"[red]Error: Failed to retrieve projects from Todoist API.[/red]")
             return None

        for project in projects:
            # <<< ADDED: Type check to handle unexpected items in the projects list >>>
            if not hasattr(project, 'name'):
                print(f"[yellow]Warning: Skipping unexpected item in project list (type: {type(project)}): {project}[/yellow]")
                continue # Skip this item and proceed with the next

            # Case-sensitive check might be too strict, consider .lower() comparison
            if project.name == project_name:
                # print(f"[cyan]Found '{project_name}' project with ID: {project.id}[/cyan]") # Reduced verbosity
                return project.id

        # If loop finishes without finding the project
        print(f"[yellow]Warning: Project named '{project_name}' not found in Todoist.[/yellow]")
        print(f"[yellow]Long Term Task functionality will be unavailable until the project is created.[/yellow]")
        return None
    except Exception as error:
        # Catch other potential errors during project retrieval/iteration
        print(f"[red]Error accessing or processing Todoist projects: {error}[/red]")
        traceback.print_exc()
        return None

# --- Other functions in helper_todoist_long.py remain unchanged from the original provided code ---
# Internal helper to find task by index - avoids code duplication
def _find_task_by_index(api, project_id, index):
    """Internal helper to find a task by its index '[index]' in a project."""
    try:
        tasks = api.get_tasks(project_id=project_id)
        if tasks is None:
             print(f"[red]Error retrieving tasks for project ID {project_id}.[/red]")
             return None

        for task in tasks:
            # Use regex to safely extract index from content like '[123] Task name'
            match = re.match(r'\s*\[(\d+)\]', task.content) # Allow leading space
            if match:
                try:
                    task_index = int(match.group(1))
                    if task_index == index:
                        return task # Found the task
                except ValueError:
                    # Should not happen with \d+ regex, but safety check
                    print(f"[yellow]Warning: Found non-integer index in task '{task.content}'. Skipping.[/yellow]")
                    continue # Skip this task

        # If loop finishes, task not found
        # Caller functions now handle the 'not found' message.
        return None
    except Exception as error:
        print(f"[red]Error searching for task with index [{index}] in project {project_id}: {error}[/red]")
        traceback.print_exc()
        return None


def delete_task(api, index):
    """Deletes a task with the given index from the Long Term Tasks project."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None # Indicate failure

    try:
        target_task = _find_task_by_index(api, project_id, index)

        if not target_task:
            print(f"[yellow]No task found with index [{index}] to delete.[/yellow]")
            return None # Indicate task not found

        task_content_for_log = target_task.content # Store content before deletion

        print(f"[cyan]Attempting to delete task: {task_content_for_log} (ID: {target_task.id})[/cyan]")
        success = api.delete_task(task_id=target_task.id)

        if success:
            print(f"[green]Successfully deleted task: {task_content_for_log}[/green]")
            # Return the content of the deleted task for potential use
            return task_content_for_log
        else:
            print(f"[red]API indicated failure deleting task ID {target_task.id}. Please check Todoist.[/red]")
            return None # Indicate failure

    except Exception as error:
        print(f"[red]An unexpected error occurred deleting task with index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None


def reschedule_task(api, index, schedule):
    """Reschedules a long-term task to the specified schedule string."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None

    if not schedule or not isinstance(schedule, str):
        print("[red]Invalid schedule provided for rescheduling.[/red]")
        return None
    # Basic validation (can be enhanced)
    if schedule.isdigit() and len(schedule) == 4:
        print("[red]Invalid time format for reschedule. Use formats like 'tomorrow 9am', 'next monday', etc.[/red]")
        return None

    try:
        target_task = _find_task_by_index(api, project_id, index)

        if not target_task:
            print(f"[yellow]No task found with index [{index}] to reschedule.[/yellow]")
            return None

        # Check for recurring task confirmation
        is_recurring = is_task_recurring(target_task) # Use helper function
        if is_recurring:
            response = input(f"Task '{target_task.content}' is recurring. Rescheduling might break recurrence. Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled by user.")
                return None

        print(f"[cyan]Attempting to reschedule task '{target_task.content}' to '{schedule}'[/cyan]")

        # Update the task
        updated_task = api.update_task(
            task_id=target_task.id,
            due_string=schedule
        )

        if not updated_task:
             print(f"[red]API call to update task did not return updated task details. Reschedule might have failed.[/red]")
             return None

        # Verification (optional, especially tricky for recurring)
        print("[cyan]Verifying reschedule...[/cyan]")
        time_module.sleep(1) # Delay for API consistency
        verification_task = api.get_task(target_task.id)

        if verification_task and verification_task.due and verification_task.due.string:
            print(f"[green]Task reschedule successful. Verified due: '{verification_task.due.string}'[/green]")
            return updated_task # Return the updated task object
        else:
            if is_recurring:
                print(f"[yellow]Recurring task reschedule initiated. Verification inconclusive, please check Todoist manually.[/yellow]")
                return updated_task # Return optimistic update for recurring
            else:
                print(f"[red]Failed to verify task reschedule. Please check Todoist.[/red]")
                return None # Indicate verification failure

    except Exception as error:
        print(f"[red]An unexpected error occurred rescheduling task index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None


def is_task_recurring(task):
    """Checks if a Todoist task object represents a recurring task."""
    if not task or not task.due:
        return False # No due date means not recurring

    try:
        # Primary check: the is_recurring flag
        if hasattr(task.due, 'is_recurring') and task.due.is_recurring:
            return True

        # Secondary check: look for keywords in the due string (less reliable)
        if hasattr(task.due, 'string') and isinstance(task.due.string, str):
            due_string_lower = task.due.string.lower()
            recurrence_patterns = ['every ', 'every!', 'daily', 'weekly', 'monthly', 'yearly']
            if any(pattern in due_string_lower for pattern in recurrence_patterns):
                 # Double-check common non-recurring phrases containing 'every'
                 if 'every day until' in due_string_lower: # Example exception
                      return False
                 return True # Found a likely recurring keyword

        return False # No recurrence indicators found
    except Exception as e:
        print(f"[yellow]Warning: Error checking recurrence for task {task.id}: {e}[/yellow]")
        return False # Assume not recurring on error

def is_task_due_today_or_earlier(task):
    """
    Checks if a task is due today or earlier, handling timezones and specific times.
    Returns True if due, False otherwise.

    Note: Tasks with no due date are considered "due" to ensure they appear in the list.
    """
    if not task:
        return False # Still return False if task itself is invalid

    # Consider tasks with no due date as "due" to show them in the list
    if not task.due:
        return True

    try:
        london_tz = pytz.timezone("Europe/London")
        now_london = datetime.now(london_tz) # Current time in London (aware)

        # --- Case 1: Task has a specific datetime ---
        if task.due.datetime:
            task_due_datetime_london = None
            try:
                raw_dt_str = task.due.datetime
                parsed_dt = parse(raw_dt_str)

                # Ensure parsed_dt becomes timezone-aware in London time
                if parsed_dt.tzinfo is None or parsed_dt.tzinfo.utcoffset(parsed_dt) is None:
                    # Naive datetime: Assume it represents London time, make it aware
                    try:
                        task_due_datetime_london = london_tz.localize(parsed_dt, is_dst=None) # Auto-handle DST
                    except (pytz.exceptions.AmbiguousTimeError, pytz.exceptions.NonExistentTimeError) as dst_err:
                        print(f"[yellow]Warning: DST ambiguity/non-existence for task '{task.content}' (ID: {task.id}) due '{raw_dt_str}': {dst_err}. Treating as not due.[/yellow]")
                        # Decide handling: here we treat ambiguous/non-existent as not due for safety
                        return False
                else:
                    # Aware datetime (e.g., UTC): Convert to London time
                    task_due_datetime_london = parsed_dt.astimezone(london_tz)

                # Perform the comparison: Task due time <= Current time
                if task_due_datetime_london:
                    # print(f"[dim]Task '{task.content}' due: {task_due_datetime_london}, Now: {now_london}, Due? {task_due_datetime_london <= now_london}[/dim]") # Debugging
                    return task_due_datetime_london <= now_london
                else:
                     # Should not happen if parsing/localization worked, but safety check
                     print(f"[yellow]Warning: Failed to determine valid London due time for task '{task.content}' (ID: {task.id}). Treating as not due.[/yellow]")
                     return False # Treat as not due if time calculation failed

            except (ValueError, TypeError) as parse_err:
                print(f"[yellow]Warning: Error parsing due datetime '{task.due.datetime}' for task '{task.content}' (ID: {task.id}): {parse_err}. Treating as not due.[/yellow]")
                return False # Treat as not due if parsing fails

        # --- Case 2: Task has only a date (all-day) ---
        elif task.due.date:
            try:
                task_due_date = parse(task.due.date).date()
                # print(f"[dim]Task '{task.content}' due date: {task_due_date}, Today: {now_london.date()}, Due? {task_due_date <= now_london.date()}[/dim]") # Debugging
                # An all-day task is due if its date is today or in the past
                return task_due_date <= now_london.date()
            except (ValueError, TypeError) as parse_err:
                print(f"[yellow]Warning: Error parsing due date '{task.due.date}' for task '{task.content}' (ID: {task.id}): {parse_err}. Treating as not due.[/yellow]")
                return False # Treat as not due if parsing fails

        # --- Case 3: Task.due exists but has neither .datetime nor .date ---
        else:
            # This shouldn't normally happen per Todoist API structure, but handle defensively
            # print(f"[dim]Task '{task.content}' has due object but no date/datetime. Treating as not due.[/dim]") # Debugging
            return True # Changed to TRUE to include tasks with empty due objects

    except Exception as e:
        # Catch-all for unexpected errors during the check
        print(f"[red]Unexpected error checking due status for task '{task.content}' (ID: {task.id}): {e}[/red]")
        traceback.print_exc()
        return False # Treat as not due on unexpected error


def handle_recurring_task(api, task, skip_logging=False):
    """Completes a recurring task using the standard completion function."""
    if not task:
        print("[red]Error: No task provided to handle_recurring_task.[/red]")
        return False

    print(f"[cyan]Completing recurring task: '{task.content}' (ID: {task.id})[/cyan]")
    try:
        # Import the function known to work for completions (potentially from part1)
        from helper_todoist_part1 import complete_todoist_task_by_id

        success = complete_todoist_task_by_id(api, task.id, skip_logging=skip_logging)

        if not success:
            # complete_todoist_task_by_id should log its own errors
            print(f"[red]Failed to complete recurring task '{task.content}'.[/red]")
            return False
        return True # Completion successful (or skipped correctly)

    except ImportError:
         print("[red]Error: Could not import 'complete_todoist_task_by_id'. Cannot complete recurring task.[/red]")
         return False
    except Exception as e:
         print(f"[red]Unexpected error handling recurring task '{task.content}': {e}[/red]")
         traceback.print_exc()
         return False


def handle_non_recurring_task(api, task, skip_logging=False):
    """
    Handles a non-recurring long-term task 'touch'.
    Logs completion (if not skipped) and sets due date to tomorrow.
    """
    if not task:
        print("[red]Error: No task provided to handle_non_recurring_task.[/red]")
        return None # Return None on failure

    print(f"[cyan]Touching non-recurring task: '{task.content}' (ID: {task.id})[/cyan]")
    try:
        # Log as completed if not skipped
        if not skip_logging:
            try:
                # Assuming helper_tasks and state_manager are available correctly now
                # Prepare entry for state_manager logging
                completed_task_log_entry = {
                    'task_name': f"(Touched Long Task) {task.content}" # Add prefix for clarity
                }
                # Log via state_manager
                if state_manager.add_completed_task_log(completed_task_log_entry):
                    print(f"  [green]Logged task touch to completed tasks.[/green]")
                else:
                    print(f"  [red]Failed to log non-recurring task touch via state_manager.[/red]")
            except NameError: # Handle if state_manager wasn't imported correctly
                 print("[red]Error: state_manager not available. Cannot log task touch.[/red]")
            except Exception as log_error:
                 print(f"[red]Error logging non-recurring task touch: {log_error}[/red]")

        # Update due date to tomorrow (relative to today in London timezone)
        london_tz = pytz.timezone("Europe/London")
        tomorrow_london = (datetime.now(london_tz) + timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"  Setting due date to tomorrow: {tomorrow_london}")

        updated_task = api.update_task(
            task_id=task.id,
            due_string=tomorrow_london # Use simple date string
        )

        if updated_task:
            print(f"  [green]Successfully updated task due date.[/green]")
            return updated_task # Return the updated task object
        else:
            print(f"  [red]API failed to update task due date.[/red]")
            return None # Indicate failure

    except Exception as error:
        print(f"[red]An unexpected error occurred handling non-recurring task '{task.content}': {error}[/red]")
        traceback.print_exc()
        return None


def touch_task(api, task_index, skip_logging=False):
    """
    'Touches' a long-term task: Completes recurring ones, pushes non-recurring to tomorrow.
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None # Indicate failure

    try:
        target_task = _find_task_by_index(api, project_id, task_index)

        if not target_task:
            print(f"[yellow]No task found with index [{task_index}] to touch.[/yellow]")
            return None # Indicate task not found

        # Check if task is recurring and handle appropriately
        if is_task_recurring(target_task):
             # Returns True on success, False on failure
             success = handle_recurring_task(api, target_task, skip_logging=skip_logging)
             return target_task if success else None # Return task object if successful
        else:
             # Returns updated task object on success, None on failure
             updated_task = handle_non_recurring_task(api, target_task, skip_logging=skip_logging)
             return updated_task # Return updated task or None

    except Exception as error:
        print(f"[red]An unexpected error occurred touching task index [{task_index}]: {error}[/red]")
        traceback.print_exc()
        return None


def add_task(api, task_name):
    """Adds a new task to the Long Term Tasks project using the task factory."""
    if not task_name or not isinstance(task_name, str):
        print("[red]Invalid task name provided for adding long-term task.[/red]")
        return None

    try:
        # Import locally to avoid circular dependencies
        import helper_task_factory

        print(f"[cyan]Adding long-term task: '{task_name}'[/cyan]")

        # Use the factory, specifying 'long' type
        task = helper_task_factory.create_task(
            api=api,
            task_content=task_name,
            task_type="long", # Specify type 'long'
            options={"api": api} # Pass API instance needed by factory for long tasks
        )

        if task:
            return task # Return the created task object
        else:
            return None # Indicate failure

    except ImportError:
         print("[red]Error: Could not import helper_task_factory. Long-term task creation failed.[/red]")
         return None
    except Exception as error:
        print(f"[red]An unexpected error occurred adding long-term task: {error}[/red]")
        traceback.print_exc()
        return None

# --- Refactored Fetching and Indexing ---
def _fetch_and_index_long_tasks(api, project_id):
    """
    Internal helper: Fetches all tasks from the project and ensures they have indices.
    Returns a dictionary map of task_id: task_object for indexed tasks.
    """
    indexed_tasks_map = {}
    indices = set()
    unindexed_tasks = []

    try:
        tasks = api.get_tasks(project_id=project_id)
        if tasks is None:
            print(f"[red]Error retrieving tasks for project ID {project_id}.[/red]")
            return {} # Return empty map on failure

        # First pass: identify existing indices and unindexed tasks
        for task in tasks:
             # <<< ADDED: Type check here as well for robustness >>>
             if not hasattr(task, 'content') or not hasattr(task, 'id'):
                  print(f"[yellow]Warning: Skipping unexpected item in task list (type: {type(task)}): {task}[/yellow]")
                  continue

             match = re.match(r'\s*\[(\d+)\]', task.content)
             if match:
                  try:
                       index_num = int(match.group(1))
                       if index_num in indices:
                            print(f"[yellow]Warning: Duplicate index [{index_num}] found! Task: '{task.content}'. Manual fix needed.[/yellow]")
                       indices.add(index_num)
                       indexed_tasks_map[task.id] = task
                  except ValueError:
                       print(f"[yellow]Warning: Invalid index format in task '{task.content}'. Treating as unindexed.[/yellow]")
                       if task.id not in indexed_tasks_map: # Avoid adding duplicates if possible
                            unindexed_tasks.append(task)
             else:
                  if task.id not in indexed_tasks_map:
                     unindexed_tasks.append(task)

        # Second pass: assign indices to unindexed tasks
        fixed_indices_count = 0
        if unindexed_tasks:
            print(f"[yellow]Found {len(unindexed_tasks)} long-term tasks without a '[index]' prefix. Auto-fixing...[/yellow]")
            next_index = 0
            for task in unindexed_tasks:
                while next_index in indices:
                    next_index += 1

                new_content = f"[{next_index}] {task.content}"
                print(f"  Assigning index [{next_index}] to task '{task.content}' (ID: {task.id})")
                try:
                    # Use update_task to change content
                    update_success = api.update_task(task_id=task.id, content=new_content)
                    if update_success:
                         task.content = new_content # Update local object
                         indices.add(next_index)
                         indexed_tasks_map[task.id] = task # Add to map after fixing
                         fixed_indices_count += 1
                         next_index += 1
                    else:
                         print(f"  [red]API failed to update index for task ID {task.id}.[/red]")
                except Exception as index_error:
                    print(f"  [red]Error assigning index [{next_index}] to task ID {task.id}: {index_error}[/red]")

            if fixed_indices_count > 0:
                print(f"[green]Finished auto-indexing. Assigned indices to {fixed_indices_count} tasks.[/green]")
            elif unindexed_tasks:
                print(f"[yellow]Could not assign indices to {len(unindexed_tasks) - fixed_indices_count} tasks due to errors.[/yellow]")


        return indexed_tasks_map

    except Exception as error:
        print(f"[red]An unexpected error occurred fetching and indexing tasks: {error}[/red]")
        traceback.print_exc()
        return {} # Return empty map on major error

# --- Sorting Helpers ---
def _get_sort_index(task):
    """Helper to extract the numerical index for sorting. Returns float('inf') if no index."""
    # <<< ADDED: Basic check if task has content >>>
    if not hasattr(task, 'content') or not isinstance(task.content, str):
        return float('inf')
    match = re.match(r'\s*\[(\d+)\]', task.content)
    try:
        return int(match.group(1)) if match else float('inf')
    except ValueError:
        return float('inf') # Handle non-integer index

def _get_due_sort_key(task, now_london, london_tz):
    """Helper to determine the datetime sort key for a task."""
    if not task:
        # <<< CORRECTED: Use datetime.max directly >>>
        return datetime.max.replace(tzinfo=pytz.utc)

    # Default to far future, aware
    # <<< CORRECTED: Use datetime.max directly >>>
    due_datetime_sort = datetime.max.replace(tzinfo=pytz.utc)

    if hasattr(task, 'due') and task.due: # Check task has 'due' and it's not None
        if hasattr(task.due, 'datetime') and task.due.datetime:
            try:
                parsed_dt = parse(task.due.datetime)
                # Ensure aware for comparison
                if parsed_dt.tzinfo is None or parsed_dt.tzinfo.utcoffset(parsed_dt) is None:
                    due_datetime_sort = london_tz.localize(parsed_dt, is_dst=None)
                else:
                    due_datetime_sort = parsed_dt.astimezone(london_tz) # Convert to London if aware elsewhere
            except (ValueError, TypeError, pytz.exceptions.PyTZException): pass # Keep default on error
        elif hasattr(task.due, 'date') and task.due.date:
            try:
                due_date = parse(task.due.date).date()
                # Use current time for past/today, min time for future for sorting
                time_comp = now_london.time() if due_date <= now_london.date() else time.min
                due_datetime_sort = london_tz.localize(datetime.combine(due_date, time_comp))
            except (ValueError, TypeError): pass # Keep default on error

    return due_datetime_sort

# --- Task Fetching/Categorization Logic ---
def get_categorized_tasks(api):
    """Fetches, auto-fixes indices, filters by due date, and categorizes long-term tasks."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return [], []

    london_tz = pytz.timezone("Europe/London")
    now_london = datetime.now(london_tz)

    try:
        indexed_tasks_map = _fetch_and_index_long_tasks(api, project_id)
        if not indexed_tasks_map:
             return [], [] # Return empty if fetching/indexing failed

        # Filter by due date first
        filtered_tasks = [
            task for task in indexed_tasks_map.values()
            if is_task_due_today_or_earlier(task)
        ]

        # Categorize
        one_shot_tasks = []
        recurring_tasks = []
        for task in filtered_tasks:
            if is_task_recurring(task):
                recurring_tasks.append(task)
            else:
                one_shot_tasks.append(task)

        # Sort categories by due date, then index
        def sort_key_due_index(task):
            return (_get_due_sort_key(task, now_london, london_tz), _get_sort_index(task))

        one_shot_tasks.sort(key=sort_key_due_index)
        recurring_tasks.sort(key=sort_key_due_index)

        return one_shot_tasks, recurring_tasks

    except Exception as error:
        print(f"[red]An unexpected error occurred fetching and categorizing tasks: {error}[/red]")
        traceback.print_exc()
        return [], []

def get_all_long_tasks_sorted_by_index(api):
    """Fetches, auto-fixes indices, and returns ALL long-term tasks sorted by index."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return [] # Return empty list if project not found

    try:
        # Fetch and ensure tasks are indexed
        indexed_tasks_map = _fetch_and_index_long_tasks(api, project_id)
        if not indexed_tasks_map:
             return [] # Return empty if fetching/indexing failed

        # Convert map values to a list
        all_tasks_list = list(indexed_tasks_map.values())

        # Sort the list purely by index
        all_tasks_list.sort(key=_get_sort_index)

        return all_tasks_list

    except Exception as error:
        print(f"[red]An unexpected error occurred getting all long tasks: {error}[/red]")
        traceback.print_exc()
        return [] # Return empty list on error


# Kept for backward compatibility if called directly elsewhere, but get_categorized_tasks is preferred.
def fetch_tasks(api, prefix=None):
    """DEPRECATED: Use get_categorized_tasks instead. Fetches raw long-term tasks."""
    print("[yellow]Warning: fetch_tasks is deprecated. Use get_categorized_tasks.[/yellow]")
    project_id = get_long_term_project_id(api)
    if not project_id:
        return []

    # Define timezone variables at the outer scope so nested functions can access them
    london_tz = pytz.timezone("Europe/London")
    now_london = datetime.now(london_tz)  # Current time in London (aware)

    try:
        # Fetch and ensure tasks are indexed using the helper
        indexed_tasks_map = _fetch_and_index_long_tasks(api, project_id)
        if not indexed_tasks_map: return []

        all_tasks_list = list(indexed_tasks_map.values())

        # Filter tasks that are due today or earlier
        filtered_tasks = [task for task in all_tasks_list if is_task_due_today_or_earlier(task)]

        # Sort by due date (oldest first), then by index for tasks with same date
        def sort_key_due_index(task):
            return (_get_due_sort_key(task, now_london, london_tz), _get_sort_index(task))

        filtered_tasks.sort(key=sort_key_due_index)
        return filtered_tasks

    except Exception as error:
        print(f"[red]Error fetching tasks (deprecated method): {error}[/red]")
        return []


# --- Display Logic ---
def format_task_for_display(task):
    """Formats a long-term task for display including index, recurrence schedule, and priority."""
    if not task or not hasattr(task, 'content'):
        return "[red]Invalid Task Object[/red]"

    try:
        # Extract index
        match = re.match(r'\s*\[(\d+)\]', task.content)
        task_index_str = "[?]" # Placeholder
        content_without_index = task.content # Default if no index found

        if match:
            task_index_str = f"[{match.group(1)}]"
            # Remove index prefix for cleaner display
            content_without_index = re.sub(r'^\s*\[\d+\]\s*', '', task.content).strip()
        else:
            # Task is missing index (should have been fixed by _fetch_and_index_long_tasks)
            print(f"[yellow]Warning: Task '{task.content}' is missing index prefix for display.[/yellow]")

        prefix = ""
        # Add recurring info (including schedule string)
        if is_task_recurring(task):
             due_string = getattr(task.due, 'string', None) if task.due else None
             if due_string:
                  # Include the schedule string
                  prefix += f"[cyan](r) {due_string}[/cyan] - "
             else:
                  # Fallback if recurring flag is true but no string (less likely)
                  prefix += "[cyan](r)[/cyan] "

        # Add priority info
        if hasattr(task, 'priority') and isinstance(task.priority, int) and task.priority > 1: # P1, P2, P3
            priority_map = {4: 1, 3: 2, 2: 3}
            display_p = priority_map.get(task.priority)
            if display_p:
                 color_map = {1: "red", 2: "orange1", 3: "yellow"}
                 color = color_map.get(display_p, "white")
                 prefix += f"[bold {color}](p{display_p})[/bold {color}] "

        # Combine parts: Index Prefix Content
        display_text = f"{task_index_str} {prefix}{content_without_index}"

        return display_text

    except Exception as error:
        print(f"[red]Error formatting task for display (ID: {getattr(task, 'id', 'N/A')}): {error}[/red]")
        traceback.print_exc() # Log stack trace
        # Fallback to raw content with error marker
        return f"[?err {getattr(task, 'id', 'N/A')}] {task.content if task else 'N/A'}"

def _display_formatted_task_list(title, tasks):
    """Internal helper to print a list of tasks using the standard format."""
    print(f"\n{title}:")
    if tasks:
        for task in tasks:
            # <<< ADDED: Ensure task is not None before formatting >>>
            if task is None:
                print("[yellow]  Skipping None task during display.[/yellow]")
                continue
            formatted_task = format_task_for_display(task)
            print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
            # Display description indented below the task
            if hasattr(task, 'description') and task.description: # Check attribute exists
                # Limit description length and replace newlines for preview
                desc_preview = (task.description[:75] + '...') if len(task.description) > 75 else task.description
                print(f"  [italic blue]Desc: {desc_preview.replace(chr(10), ' ')}[/italic blue]")
    else:
        print("[dim]  No tasks in this category.[/dim]")


def display_tasks(api, task_type=None):
    """Displays categorized long-term tasks (One-Shots and Recurring)."""
    # task_type parameter is unused, kept for backward compatibility if needed
    if task_type:
         print(f"[yellow]Warning: 'task_type' parameter in display_tasks is ignored.[/yellow]")

    print("\n[bold cyan]--- Long Term Tasks (Due) ---[/bold cyan]")
    try:
        one_shot_tasks, recurring_tasks = get_categorized_tasks(api) # Use the main function

        _display_formatted_task_list("One Shots", one_shot_tasks)
        _display_formatted_task_list("Recurring", recurring_tasks)

        print() # Add final newline for spacing

    except Exception as e:
         print(f"[red]An error occurred displaying long-term tasks: {e}[/red]")
         traceback.print_exc()

# --- New function for the 'show long all' command ---
def display_all_long_tasks(api):
    """Fetches and displays ALL long-term tasks, sorted by index."""
    print("\n[bold magenta]--- All Long Term Tasks (by Index) ---[/bold magenta]")
    try:
        # Fetch all tasks, already indexed and sorted by index
        all_tasks = get_all_long_tasks_sorted_by_index(api)

        # Use the common display helper
        _display_formatted_task_list("All Tasks", all_tasks)

        print() # Add final newline for spacing

    except Exception as e:
         print(f"[red]An error occurred displaying all long-term tasks: {e}[/red]")
         traceback.print_exc()

# --- End New Function ---

def rename_task(api, index, new_name):
    """Renames a long-term task, preserving its index prefix."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None

    if not new_name or not isinstance(new_name, str):
        print("[red]Invalid new name provided for renaming.[/red]")
        return None

    try:
        target_task = _find_task_by_index(api, project_id, index)

        if not target_task:
            print(f"[yellow]No task found with index [{index}] to rename.[/yellow]")
            return None

        # <<< ADDED: Check if task has content before proceeding >>>
        if not hasattr(target_task, 'content'):
             print(f"[red]Error: Task object for index [{index}] is invalid (missing content). Cannot rename.[/red]")
             return None

        # Preserve the original index from the matched task
        match = re.match(r'\s*\[(\d+)\]', target_task.content)
        if not match:
             print(f"[red]Error: Could not extract original index from task '{target_task.content}'. Cannot rename.[/red]")
             return None
        original_index = match.group(1) # Keep the index as found

        # Construct new task content with original index
        new_content = f"[{original_index}] {new_name.strip()}" # Ensure no extra spaces

        print(f"[cyan]Renaming task index [{original_index}] from '{target_task.content}' to '{new_content}'[/cyan]")

        # Update the task
        updated_task = api.update_task(
            task_id=target_task.id,
            content=new_content
        )

        if updated_task:
            print(f"[green]Task successfully renamed.[/green]")
            return updated_task # Return the updated task object
        else:
            print(f"[red]API failed to rename task ID {target_task.id}.[/red]")
            return None # Indicate failure

    except Exception as error:
        print(f"[red]An unexpected error occurred renaming task index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None

# Apply call counter decorator to all functions defined in this module
# <<< ADDED: Import state_manager for handle_non_recurring_task >>>
import state_manager
module_call_counter.apply_call_counter_to_all(globals(), __name__)