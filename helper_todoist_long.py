import module_call_counter
from rich import print
from datetime import datetime, timedelta, timezone
import re
import pytz # Ensure pytz is imported if used directly (e.g., london_tz)
from dateutil.parser import parse
import helper_tasks  # Keep if handle_non_recurring_task uses it
# Import API type hint if needed
# from todoist_api_python.api import TodoistAPI
import time # <-- Added missing import here
import traceback # Import traceback for logging


def get_long_term_project_id(api):
    """Get the ID of the 'Long Term Tasks' project, returns None if not found or error occurs."""
    project_name = "Long Term Tasks" # Store in variable for consistency
    try:
        projects = api.get_projects()
        if projects is None: # API call might return None on error
             print(f"[red]Error: Failed to retrieve projects from Todoist API.[/red]")
             return None

        for project in projects:
            # Case-sensitive check might be too strict, consider .lower() comparison
            if project.name == project_name:
                # print(f"[cyan]Found '{project_name}' project with ID: {project.id}[/cyan]") # Reduced verbosity
                return project.id

        # If loop finishes without finding the project
        print(f"[yellow]Warning: Project named '{project_name}' not found in Todoist.[/yellow]")
        print(f"[yellow]Long Term Task functionality will be unavailable until the project is created.[/yellow]")
        return None
    except Exception as error:
        print(f"[red]Error accessing Todoist projects: {error}[/red]")
        # Log stack trace
        traceback.print_exc()
        return None

# Helper to find task by index - avoids code duplication
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
        # Log stack trace
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
        # Log stack trace
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
            # description=target_task.description # Preserved by default
        )

        if not updated_task:
             print(f"[red]API call to update task did not return updated task details. Reschedule might have failed.[/red]")
             return None

        # Verification (optional, especially tricky for recurring)
        print("[cyan]Verifying reschedule...[/cyan]")
        time.sleep(1) # Delay for API consistency
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
        # Log stack trace
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
            # Use specific patterns to avoid false positives (e.g., 'everyday clothes')
            # Regex might be more robust here: r'\b(every|daily|weekly|monthly|yearly)\b'
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
    """Checks if a task is due today or earlier, considering timezones and all-day tasks."""
    if not task: return False # Handle null task object

    if not task.due:
        # print(f"[dim]Task '{task.content}' has no due date.[/dim]") # Debugging
        return False # Treat tasks without due dates as not due "today or earlier" for this specific check

    try:
        london_tz = pytz.timezone("Europe/London")
        now_london = datetime.now(london_tz) # Current time in London

        task_due_datetime_london = None
        is_all_day = True

        if task.due.datetime:
            # Task has a specific time
            utc_dt = parse(task.due.datetime)
            # Ensure timezone awareness
            if utc_dt.tzinfo is None or utc_dt.tzinfo.utcoffset(utc_dt) is None:
                utc_dt = pytz.utc.localize(utc_dt) # Assume UTC if naive
            task_due_datetime_london = utc_dt.astimezone(london_tz)
            is_all_day = False
            # print(f"[dim]Task '{task.content}' due datetime: {task_due_datetime_london}[/dim]") # Debugging
        elif task.due.date:
            # Task has only a date (all-day task)
            task_due_date = parse(task.due.date).date()
            # Consider an all-day task "due" for the entire day. Compare dates only.
            # print(f"[dim]Task '{task.content}' due date: {task_due_date}[/dim]") # Debugging
            return task_due_date <= now_london.date()
        else:
            # Should not happen if task.due exists, but safety check
            # print(f"[dim]Task '{task.content}' has due object but no date/datetime.[/dim]") # Debugging
            return False # Cannot determine due status

        # If it has a specific time, compare datetime
        if not is_all_day and task_due_datetime_london:
            return task_due_datetime_london <= now_london
        else:
            # Should have returned based on date comparison already
            return False

    except (ValueError, TypeError, AttributeError) as e:
        print(f"[yellow]Warning: Error parsing due date for task '{task.content}' (ID: {task.id}): {e}. Treating as not due.[/yellow]")
        return False # Treat as not due if parsing fails
    except Exception as e:
        print(f"[red]Unexpected error checking due date for task '{task.content}' (ID: {task.id}): {e}. Treating as not due.[/red]")
        # Log stack trace
        traceback.print_exc()
        return False


def handle_recurring_task(api, task, skip_logging=False):
    """Completes a recurring task using the standard completion function."""
    if not task:
        print("[red]Error: No task provided to handle_recurring_task.[/red]")
        return False

    print(f"[cyan]Completing recurring task: '{task.content}' (ID: {task.id})[/cyan]")
    try:
        # Import the function known to work for completions (potentially from part1)
        # Ensure the import path is correct based on file structure
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
         # Log stack trace
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
                # Use helper_tasks to log it (ensure helper_tasks is imported)
                # Pass a dictionary structure if that's what add_to_completed_tasks expects
                completed_task_log_entry = {
                    'task_name': f"(Touched Long Task) {task.content}" # Add prefix for clarity
                }
                # Assuming add_to_completed_tasks exists and works
                helper_tasks.add_to_completed_tasks(completed_task_log_entry)
                print(f"  [green]Logged task touch to completed tasks.[/green]")
            except AttributeError:
                 print("[red]Error: 'helper_tasks.add_to_completed_tasks' not found or import failed. Cannot log task touch.[/red]")
                 # Decide whether to continue or fail here
            except Exception as log_error:
                 print(f"[red]Error logging non-recurring task touch: {log_error}[/red]")
                 # Log stack trace if needed
                 # traceback.print_exc()
                 # Continue with the due date update regardless of logging failure?

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
        # Log stack trace
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
        # Log stack trace
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
            # Factory should handle logging success
            # print(f"[green]Successfully added long-term task: {task.content}[/green]")
            return task # Return the created task object
        else:
            # Factory should handle logging failure
            # print(f"[red]Failed to add long-term task using factory.[/red]")
            return None # Indicate failure

    except ImportError:
         print("[red]Error: Could not import helper_task_factory. Long-term task creation failed.[/red]")
         return None
    except Exception as error:
        print(f"[red]An unexpected error occurred adding long-term task: {error}[/red]")
        # Log stack trace
        traceback.print_exc()
        return None

def get_categorized_tasks(api):
    """Fetches, auto-fixes indices, filters, and categorizes long-term tasks."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return [], [] # Return empty lists if project not found

    try:
        # Get all tasks in the project
        tasks = api.get_tasks(project_id=project_id)
        if tasks is None:
             print(f"[red]Error retrieving tasks for project ID {project_id}.[/red]")
             return [], []

        # --- Auto-indexing ---
        indices = set() # Use a set for faster lookups
        unindexed_tasks = []
        indexed_tasks_map = {} # Store tasks we've processed to avoid reprocessing

        for task in tasks:
             match = re.match(r'\s*\[(\d+)\]', task.content)
             if match:
                  try:
                       index_num = int(match.group(1))
                       if index_num in indices:
                            print(f"[yellow]Warning: Duplicate index [{index_num}] found! Task: '{task.content}'. Manual fix needed.[/yellow]")
                            # Handle duplicates? For now, just record it.
                       indices.add(index_num)
                       indexed_tasks_map[task.id] = task # Add to processed map
                  except ValueError:
                       print(f"[yellow]Warning: Invalid index format in task '{task.content}'. Treating as unindexed.[/yellow]")
                       unindexed_tasks.append(task)
             else:
                  # Only add if not already processed (e.g., if API returns duplicates somehow)
                  if task.id not in indexed_tasks_map:
                     unindexed_tasks.append(task)


        fixed_indices_count = 0
        if unindexed_tasks:
            print(f"[yellow]Found {len(unindexed_tasks)} long-term tasks without a '[index]' prefix. Auto-fixing...[/yellow]")
            next_index = 0
            for task in unindexed_tasks:
                # Find the lowest available index starting from 0
                while next_index in indices:
                    next_index += 1

                new_content = f"[{next_index}] {task.content}"
                print(f"  Assigning index [{next_index}] to task '{task.content}' (ID: {task.id})")
                try:
                    update_success = api.update_task(
                        task_id=task.id,
                        content=new_content
                    )
                    if update_success:
                         # Update the local task object for correct categorization
                         task.content = new_content # Modify the object in the original list
                         indices.add(next_index) # Add the newly assigned index
                         indexed_tasks_map[task.id] = task # Add to processed map
                         fixed_indices_count += 1
                         next_index += 1 # Move to next potential index for the next task
                    else:
                         print(f"  [red]API failed to update index for task ID {task.id}.[/red]")
                except Exception as index_error:
                    print(f"  [red]Error assigning index [{next_index}] to task ID {task.id}: {index_error}[/red]")
                    # Stop trying to assign indices if one fails? Or just skip? Skip for now.

            if fixed_indices_count > 0: # Only print if something was fixed
                print(f"[green]Finished auto-indexing. Assigned indices to {fixed_indices_count} tasks.[/green]")
            # Re-fetch tasks after indexing? Might be safer but adds API calls.
            # For now, work with the modified local list. Tasks reference objects, so changes persist.


        # --- Filtering and Categorization ---
        # Use the comprehensive due date checker
        # print("[cyan]Filtering tasks due today or earlier...[/cyan]") # Debug
        filtered_tasks = [
             task for task_id, task in indexed_tasks_map.items() # Iterate over indexed tasks
             if is_task_due_today_or_earlier(task)
        ]
        # print(f"[cyan]Found {len(filtered_tasks)} tasks due today or earlier.[/cyan]") # Debug

        one_shot_tasks = []
        recurring_tasks = []

        for task in filtered_tasks:
            if is_task_recurring(task):
                recurring_tasks.append(task)
            else:
                one_shot_tasks.append(task)

        # --- Sorting ---
        def get_sort_index(task):
             match = re.match(r'\s*\[(\d+)\]', task.content)
             try:
                  return int(match.group(1)) if match else float('inf') # Sort unindexed last
             except ValueError:
                  return float('inf') # Sort invalid index last

        def sort_key(task):
             # Sort primarily by due date (earliest first), then by index
             due_date = datetime.max.date() # Default for tasks with no due date (sorts last)
             if task.due and task.due.date:
                  try:
                       due_date = parse(task.due.date).date()
                  except (ValueError, TypeError): pass # Keep default on parse error

             return (due_date, get_sort_index(task))

        one_shot_tasks.sort(key=sort_key)
        recurring_tasks.sort(key=sort_key)

        return one_shot_tasks, recurring_tasks

    except Exception as error:
        print(f"[red]An unexpected error occurred fetching and categorizing tasks: {error}[/red]")
        # Log stack trace
        traceback.print_exc()
        return [], [] # Return empty lists on error


# Kept for backward compatibility if called directly elsewhere, but get_categorized_tasks is preferred.
def fetch_tasks(api, prefix=None):
    """DEPRECATED: Use get_categorized_tasks instead. Fetches raw long-term tasks."""
    print("[yellow]Warning: fetch_tasks is deprecated. Use get_categorized_tasks.[/yellow]")
    project_id = get_long_term_project_id(api)
    if not project_id:
        return []

    try:
        tasks = api.get_tasks(project_id=project_id)
        if tasks is None: return []

        # Filter tasks that are due today or earlier
        filtered_tasks = [task for task in tasks if is_task_due_today_or_earlier(task)]

        # Sort by due date (oldest first), then by index for tasks with same date
        def get_index(task):
             match = re.match(r'\s*\[(\d+)\]', task.content)
             try: return int(match.group(1)) if match else float('inf')
             except ValueError: return float('inf')

        def sort_key(task):
            due_date = datetime.max.date()
            if task.due and task.due.date:
                 try: due_date = parse(task.due.date).date()
                 except (ValueError, TypeError): pass
            return (due_date, get_index(task))

        filtered_tasks.sort(key=sort_key)
        return filtered_tasks

    except Exception as error:
        print(f"[red]Error fetching tasks (deprecated method): {error}[/red]")
        return []


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
            # Task is missing index (should have been fixed by get_categorized_tasks)
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
        # Example: [12] [cyan](r) every day[/cyan] - [bold red](p1)[/bold red] Actual task content
        display_text = f"{task_index_str} {prefix}{content_without_index}"

        return display_text

    except Exception as error:
        print(f"[red]Error formatting task for display (ID: {getattr(task, 'id', 'N/A')}): {error}[/red]")
        traceback.print_exc() # Log stack trace
        # Fallback to raw content with error marker
        return f"[?err {getattr(task, 'id', 'N/A')}] {task.content if task else 'N/A'}"


def display_tasks(api, task_type=None):
    """Displays categorized long-term tasks (One-Shots and Recurring)."""
    # task_type parameter is unused, kept for backward compatibility if needed
    if task_type:
         print(f"[yellow]Warning: 'task_type' parameter in display_tasks is ignored.[/yellow]")

    print("\n[bold cyan]--- Long Term Tasks (Due) ---[/bold cyan]") # Moved title here
    try:
        one_shot_tasks, recurring_tasks = get_categorized_tasks(api) # Use the main function

        print("\nOne Shots:")
        if one_shot_tasks:
            for task in one_shot_tasks:
                formatted_task = format_task_for_display(task)
                print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
                # Display description indented below the task
                if task.description:
                    # Limit description length?
                    desc_preview = (task.description[:75] + '...') if len(task.description) > 75 else task.description
                    print(f"  [italic blue]Desc: {desc_preview.replace(chr(10), ' ')}[/italic blue]") # Replace newlines
        else:
            print("[dim]  No one-shot tasks due.[/dim]")

        print("\nRecurring:")
        if recurring_tasks:
            for task in recurring_tasks:
                formatted_task = format_task_for_display(task) # Format function now includes schedule string
                print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
                if task.description:
                    desc_preview = (task.description[:75] + '...') if len(task.description) > 75 else task.description
                    print(f"  [italic blue]Desc: {desc_preview.replace(chr(10), ' ')}[/italic blue]")
        else:
            print("[dim]  No recurring tasks due.[/dim]")
        print() # Add final newline for spacing

    except Exception as e:
         print(f"[red]An error occurred displaying long-term tasks: {e}[/red]")
         # Log stack trace
         traceback.print_exc()

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
        # Log stack trace
        traceback.print_exc()
        return None

# Apply call counter decorator to all functions defined in this module
module_call_counter.apply_call_counter_to_all(globals(), __name__)