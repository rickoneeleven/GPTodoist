# File: helper_todoist_part2.py

import re
import pytz
import datetime
import time
import os # KEPT: For os.environ.get in timesheet, but potentially removable later
import signal
import subprocess
from datetime import timedelta, timezone # Ensure timezone is imported
import module_call_counter
import helper_todoist_long
from dateutil.parser import parse
from rich import print
import traceback # Import traceback for logging
import state_manager # <<< ADDED: Import state manager

# Import necessary functions from part1 or state_manager
from helper_todoist_part1 import (
    # get_active_filter, # Now handled via state_manager
    complete_todoist_task_by_id,
    format_due_time,
    add_to_active_task_file, # Wrapper for state_manager.set_active_task
)
# Import API type hint if needed
# from todoist_api_python.api import TodoistAPI


def add_todoist_task(api, user_message):
    """Adds a new task to Todoist based on the active filter's project ID (obtained via state_manager)."""
    try:
        import helper_task_factory # Import locally

        # <<< MODIFIED: Get filter details via state_manager >>>
        active_filter_query, project_id = state_manager.get_active_filter_details()

        if not user_message.lower().startswith("add task "):
            print("[red]Invalid command format. Use 'add task <task content>'.[/red]")
            return None
        task_content = user_message[len("add task "):].strip()
        if not task_content:
             print("[yellow]No task content provided.[/yellow]")
             return None

        print(f"[cyan]Attempting to add task: '{task_content}'[/cyan]")
        if project_id:
            print(f"[cyan]Target project ID from active filter: {project_id}[/cyan]")
        else:
            print("[cyan]No project ID set in active filter; task will use default.[/cyan]")

        task = helper_task_factory.create_task(
            api=api,
            task_content=task_content,
            task_type="normal",
            options={"project_id": project_id} # Pass project_id from filter details
        )

        if task:
            # Task factory handles success/failure messages
            # Consider displaying tasks after adding?
            # display_todoist_tasks(api)
            return task
        else:
            return None

    except ImportError:
         print("[red]Error: Could not import helper_task_factory. Task creation failed.[/red]")
         return None
    except Exception as error:
        print(f"[red]An unexpected error occurred adding task: {error}[/red]")
        traceback.print_exc()
        return None


def fetch_todoist_tasks(api):
    """Fetches and sorts tasks based on the active filter (obtained via state_manager)."""
    # Timeout logic remains
    if hasattr(signal, 'SIGALRM'):
        def handler(signum, frame):
            raise TimeoutError("Todoist task fetch timed out after 5 seconds")
    # else: # Warning printed elsewhere

    # <<< MODIFIED: Get filter query via state_manager >>>
    active_filter_query, _ = state_manager.get_active_filter_details() # Project ID not needed here
    if not active_filter_query:
        print("[red]Error: No active filter query found. Cannot fetch tasks.[/red]")
        return None # Return None to indicate failure

    retries = 3
    retry_delay = 2

    for attempt in range(retries):
        try:
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(5)

            # <<< MODIFIED: Added comment explaining potential TypeError >>>
            # Note: The following line uses the 'filter=' keyword argument.
            # This is correct for todoist-api-python v2.x.
            # If you encounter a TypeError "got an unexpected keyword argument 'filter'",
            # ensure you have the correct library version installed (e.g., v2.1.3 or later v2.x)
            # as specified or investigated per todo.txt.
            tasks = api.get_tasks(filter=active_filter_query)

            if hasattr(signal, 'SIGALRM'): signal.alarm(0)

            if not isinstance(tasks, list):
                print(f"[red]Error: API returned unexpected data type: {type(tasks)}[/red]")
                return None

            # Timezone processing logic remains the same...
            london_tz = pytz.timezone("Europe/London")
            now_utc = datetime.datetime.now(timezone.utc)
            now_london = now_utc.astimezone(london_tz)
            processed_tasks = []
            for task in tasks:
                try:
                    task.has_time = False
                    if task.due:
                        task.due_string_raw = getattr(task.due, 'string', None)
                        task.is_recurring_flag = getattr(task.due, 'is_recurring', False)
                        if task.due.datetime:
                            parsed_dt = parse(task.due.datetime)
                            if parsed_dt.tzinfo is None or parsed_dt.tzinfo.utcoffset(parsed_dt) is None:
                                try:
                                    london_dt = london_tz.localize(parsed_dt, is_dst=None)
                                except pytz.exceptions.AmbiguousTimeError:
                                     london_dt = london_tz.localize(parsed_dt, is_dst=True)
                                except pytz.exceptions.NonExistentTimeError:
                                     london_dt = parsed_dt # Keep naive
                            else:
                                london_dt = parsed_dt.astimezone(london_tz)
                            task.due.datetime_localized = london_dt
                            task.has_time = True
                        elif task.due.date:
                            due_date = parse(task.due.date).date()
                            if due_date <= now_london.date():
                                london_dt = london_tz.localize(datetime.datetime.combine(due_date, now_london.time()))
                            else:
                                london_dt = london_tz.localize(datetime.datetime.combine(due_date, datetime.time(0, 1)))
                            task.due.datetime_localized = london_dt
                            task.has_time = False
                        else:
                            task.due.datetime_localized = now_london
                            task.has_time = False
                            task.due_string_raw = None
                            task.is_recurring_flag = False
                    else:
                        task.due = type("Due", (object,), {"datetime_localized": now_london, "string": None,"is_recurring": False})()
                        task.has_time = False
                        task.due_string_raw = None
                        task.is_recurring_flag = False

                    task.created_at_sortable = parse(task.created_at) if hasattr(task, 'created_at') and task.created_at else datetime.datetime.min.replace(tzinfo=pytz.utc)
                    processed_tasks.append(task)
                except Exception as process_error:
                    print(f"[yellow]Warn: Err processing task {getattr(task, 'id', 'N/A')}: {process_error}. Skip.[/yellow]")
                    # traceback.print_exc()

            # Sorting logic remains the same...
            sorted_final_tasks = sorted(
                processed_tasks,
                key=lambda t: (
                    -getattr(t, 'priority', 1),
                    getattr(t.due, 'datetime_localized', now_london) if t.due else now_london,
                    getattr(t, 'has_time', False),
                    getattr(t, 'created_at_sortable', datetime.datetime.min.replace(tzinfo=pytz.utc))
                ),
            )
            return sorted_final_tasks

        except TimeoutError as te:
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)
            print(f"[yellow]Attempt {attempt + 1}: Task fetch timed out. {te}. Retrying...[/yellow]")
        except Exception as e:
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)
            print(f"[red]Attempt {attempt + 1}: Error fetching tasks: {e}[/red]")
            # Only print traceback here if it's not the specific TypeError we commented on
            if not isinstance(e, TypeError) or "unexpected keyword argument 'filter'" not in str(e):
                traceback.print_exc()

        if attempt < retries - 1:
            time.sleep(retry_delay)

    print(f"[red]Failed to fetch tasks after {retries} attempts.[/red]")
    return None


def get_next_todoist_task(api):
    """Gets the next task, displays it, and saves it as the active task using state_manager."""
    try:
        tasks = fetch_todoist_tasks(api) # Uses state_manager for filter query
        if tasks is None:
            print("[yellow]Unable to fetch tasks.[/yellow]\n")
            return # Cannot proceed
        if not tasks:
            print("\u2705 [bold green]All tasks complete! \u2705[/bold green]\n")
            # <<< MODIFIED: Clear active task via state_manager >>>
            state_manager.clear_active_task()
            # Continue to display long term tasks
        else:
            # Task exists, set it as active
            next_task = tasks[0]
            task_name = getattr(next_task, 'content', 'Unknown Task')
            task_id = getattr(next_task, 'id', None)
            task_due_iso = None

            if task_id:
                # Extract due date info for saving
                if next_task.due and hasattr(next_task.due, 'datetime_localized') and next_task.due.datetime_localized:
                     try:
                        # Check if it's the 'now' timestamp we assigned to undated tasks
                        london_tz = pytz.timezone("Europe/London")
                        now_utc = datetime.datetime.now(timezone.utc)
                        now_london = now_utc.astimezone(london_tz)
                        time_diff = abs(next_task.due.datetime_localized - now_london)
                        is_effectively_now = time_diff < timedelta(seconds=1)

                        # Only save ISO if it's not the 'now' timestamp OR if it had an original time
                        if not (is_effectively_now and not getattr(next_task, 'has_time', False)):
                            if hasattr(next_task.due.datetime_localized, 'tzinfo') and next_task.due.datetime_localized.tzinfo is not None:
                                task_due_iso = next_task.due.datetime_localized.isoformat()
                     except Exception: pass # Ignore formatting errors for saving

                # <<< MODIFIED: Use wrapper for state_manager.set_active_task >>>
                add_to_active_task_file(task_name, task_id, task_due_iso)
            else:
                 print("[red]Error: Could not determine ID of the next task. Active task NOT set.[/red]")


            # Display logic remains the same...
            print("[bold green]--- Next Task ---[/bold green]")
            try:
                task_display = next_task # Use the already fetched task data
                base_display_info = get_task_display_info(task_display, include_recurring_marker=False)
                due_display_str = ""
                recurring_schedule_prefix = ""
                is_recurring = getattr(task_display, 'is_recurring_flag', False)
                due_string = getattr(task_display, 'due_string_raw', None)

                if is_recurring:
                    recurring_schedule_prefix = f"[cyan](r) {due_string}[/cyan] - " if due_string else "[cyan](r)[/cyan] "

                # Determine display string for due date/time
                if task_display.due and hasattr(task_display.due, 'datetime_localized') and task_display.due.datetime_localized:
                     try:
                         london_tz = pytz.timezone("Europe/London")
                         now_utc = datetime.datetime.now(timezone.utc)
                         now_london = now_utc.astimezone(london_tz)
                         if hasattr(task_display.due.datetime_localized, 'tzinfo') and task_display.due.datetime_localized.tzinfo is not None:
                             time_diff = abs(task_display.due.datetime_localized - now_london)
                             is_effectively_now = time_diff < timedelta(seconds=1)
                             if is_effectively_now and not getattr(task_display, 'has_time', False):
                                  due_display_str = "(No due date)"
                             elif getattr(task_display, 'has_time', False):
                                  due_display_str = f"(Due: {task_display.due.datetime_localized.strftime('%Y-%m-%d %H:%M')})"
                             else: # All day task
                                  due_display_str = f"(Due: {task_display.due.datetime_localized.strftime('%Y-%m-%d')} All day)"
                         else: # Remained naive
                              due_display_str = f"(Due: {task_display.due.datetime_localized.strftime('%Y-%m-%d %H:%M')} ?TZ?)" # Indicate TZ issue
                     except Exception as fmt_err:
                          print(f"[yellow]Warning: Error formatting due date for display: {fmt_err}[/yellow]")
                          due_display_str = "(Due info error)"
                elif due_string: # Fallback to raw due string if localized failed but string exists
                     due_display_str = f"(Due: {due_string})"


                # Check if task is in the future (using localized times)
                is_future = False
                future_time_str = ""
                if task_display.due and hasattr(task_display.due, 'datetime_localized') and task_display.due.datetime_localized:
                    try:
                        london_tz = pytz.timezone("Europe/London")
                        now_utc = datetime.datetime.now(timezone.utc)
                        now_london = now_utc.astimezone(london_tz)
                        if hasattr(task_display.due.datetime_localized, 'tzinfo') and task_display.due.datetime_localized.tzinfo is not None:
                            # Consider future if due more than a minute from now
                            if task_display.due.datetime_localized > (now_london + timedelta(minutes=1)):
                                # Avoid showing future if it's effectively 'now' and was originally undated
                                time_diff = abs(task_display.due.datetime_localized - now_london)
                                is_effectively_now = time_diff < timedelta(seconds=1)
                                # Only show future time if it had an actual time component originally
                                if not (is_effectively_now and not getattr(task_display, 'has_time', False)) and getattr(task_display, 'has_time', False):
                                     is_future = True
                                     future_time_str = task_display.due.datetime_localized.strftime('%H:%M')
                    except Exception as future_check_err:
                         print(f"[yellow]Warning: Error checking if task is in the future: {future_check_err}[/yellow]")

                # Use task name from the object for display consistency
                task_name_display = getattr(task_display, 'content', 'Unknown Task')
                if is_future:
                    print(f"                   [orange1]{base_display_info}{recurring_schedule_prefix}{task_name_display} (next task due at {future_time_str})[/orange1]")
                else:
                     print(f"                   [green]{base_display_info}{recurring_schedule_prefix}{task_name_display} {due_display_str}[/green]")

                # Print description if it exists
                if getattr(task_display, 'description', None):
                    print(f"                   [italic blue]  Desc: {task_display.description}[/italic blue]")
                print() # Add a newline for spacing

            except Exception as display_error:
                 print(f"[red]Error preparing next task display: {display_error}[/red]")
                 traceback.print_exc()
                 # Fallback display using name from potentially stale active file info if needed
                 print(f"                   [green]{task_name}[/green]\n") # Use task_name from above

        # Display long-term tasks (logic unchanged)
        try:
            helper_todoist_long.display_tasks(api)
        except Exception as long_term_error:
            print(f"[red]Error displaying long-term tasks: {long_term_error}[/red]")
            # traceback.print_exc() # Can be verbose
            print()

    except Exception as e:
        print(f"[red]An unexpected error occurred in get_next_todoist_task: {e}[/red]")
        traceback.print_exc()
        print("Continuing...\n")


def get_task_display_info(task, include_recurring_marker=True):
    """
    Generates a prefix string for task display including recurring (optional) and priority info.
    (No file I/O - unchanged)
    """
    display_info = ""
    if not task: return ""
    try:
        if include_recurring_marker:
            if getattr(task, 'is_recurring_flag', False):
                display_info += "[cyan](r)[/cyan] "
        priority = getattr(task, 'priority', None)
        if isinstance(priority, int) and priority > 1:
             priority_map = {4: 1, 3: 2, 2: 3}
             display_p = priority_map.get(priority)
             if display_p:
                 color_map = {1: "red", 2: "orange1", 3: "yellow"}
                 color = color_map.get(display_p, "white")
                 display_info += f"[bold {color}](p{display_p})[/bold {color}] "
    except Exception as e:
         print(f"[yellow]Warn: Err gen display info {getattr(task, 'id', 'N/A')}: {e}[/yellow]")
    return display_info


def display_todoist_tasks(api):
    """Fetches and displays all tasks from the active filter, formatted.
    (Relies on fetch_todoist_tasks which is refactored - unchanged logic here)
    """
    print("[cyan]Fetching tasks for display...[/cyan]")
    tasks = fetch_todoist_tasks(api) # Uses refactored fetch
    if tasks is None:
        print("[red]Could not fetch tasks to display.[/red]")
        return
    if not tasks:
        print("[green]No tasks found matching the active filter.[/green]")
        return

    print("[bold magenta]--- Current Tasks ---[/bold magenta]")
    display_data = []
    # Pre-processing and display logic remains the same...
    for task in tasks:
        try:
            base_display_info = get_task_display_info(task, include_recurring_marker=False)
            recurring_schedule_prefix = ""
            due_display = "(No due date)"
            is_recurring = getattr(task, 'is_recurring_flag', False)
            due_string = getattr(task, 'due_string_raw', None)
            if is_recurring:
                recurring_schedule_prefix = f"[cyan](r) {due_string}[/cyan] - " if due_string else "[cyan](r)[/cyan] "
            if task.due and hasattr(task.due, 'datetime_localized') and task.due.datetime_localized:
                 try:
                    london_tz = pytz.timezone("Europe/London")
                    now_utc = datetime.datetime.now(timezone.utc)
                    now_london = now_utc.astimezone(london_tz)
                    if hasattr(task.due.datetime_localized, 'tzinfo') and task.due.datetime_localized.tzinfo is not None:
                        time_diff = abs(task.due.datetime_localized - now_london)
                        is_effectively_now = time_diff < timedelta(seconds=1)
                        if not (is_effectively_now and not getattr(task, 'has_time', False)):
                            if getattr(task, 'has_time', False):
                                due_display = task.due.datetime_localized.strftime("%Y-%m-%d %H:%M")
                            else:
                                due_display = task.due.datetime_localized.strftime("%Y-%m-%d") + " All day"
                    else:
                         due_display = f"{task.due.datetime_localized.strftime('%Y-%m-%d %H:%M')} ?TZ?"
                 except Exception: due_display = "(Due Error)"
            elif due_string: due_display = due_string
            display_data.append({
                "prefix": base_display_info, "recurring_prefix": recurring_schedule_prefix,
                "due": due_display, "content": getattr(task, 'content', 'Unknown'),
                "description": getattr(task, 'description', None) })
        except Exception as e:
             print(f"[yellow]Warn: Err proc task {getattr(task, 'id', 'N/A')} for disp: {e}[/yellow]")
             traceback.print_exc()

    max_due_len = 0
    if display_data:
        try: max_due_len = max(len(data['due']) for data in display_data)
        except ValueError: pass
    tab = "    "
    for data in display_data:
        try:
            due_padded = data['due'].ljust(max_due_len)
            full_prefix = data['prefix'] + data['recurring_prefix']
            line = f"{due_padded}{tab}{full_prefix}{data['content']}"
            print(line)
            if data['description']:
                desc_indent = " " * (max_due_len + len(tab))
                for desc_line in data['description'].splitlines():
                     print(f"{desc_indent}[italic blue]Desc: {desc_line}[/italic blue]")
        except Exception as e:
            print(f"[red]Err print line '{data.get('content', 'N/A')}': {e}[/red]")
            traceback.print_exc()
    print("[bold magenta]---------------------[/bold magenta]")


def check_if_grafting(api):
     """Checks if the graft file exists and displays graft status using state_manager."""
     # <<< MODIFIED: Use state_manager >>>
     grafted_tasks = state_manager.get_grafted_tasks()

     if grafted_tasks is None:
          # File doesn't exist, not grafting
          return False
     elif not grafted_tasks:
          # File was empty or invalid (state manager cleared it)
          return False
     else:
          # Valid grafted tasks exist
          print("[bold red]*** GRAFT MODE ACTIVE ***[/bold red]")
          print("[yellow]Focus on these tasks:[/yellow]")
          for i, task in enumerate(grafted_tasks):
              # Assume state_manager returned only valid tasks
              index = task.get("index", i + 1) # Use index if present, fallback to list order
              print(f"  {index}. {task['task_name']}")
          print()
          return True


def rename_todoist_task(api, user_message):
    """Renames the active Todoist task using state_manager."""
    try:
        if not user_message.lower().startswith("rename "):
            print("[red]Invalid format. Use 'rename <new task name>'.[/red]")
            return False
        new_task_name = user_message[len("rename "):].strip()
        if not new_task_name:
            print("[yellow]No new task name provided.[/yellow]")
            return False

        # <<< MODIFIED: Get active task via state_manager >>>
        active_task = state_manager.get_active_task()
        if not active_task:
            print(f"[red]Error: Active task file not found or invalid. Cannot rename.[/red]")
            return False
        task_id = active_task.get("task_id")
        if not task_id:
             print(f"[red]Error: 'task_id' missing in active task data.[/red]")
             return False

        task = api.get_task(task_id) # Verify task exists
        if not task:
            print(f"[yellow]Task ID {task_id} not found. Cannot rename.[/yellow]")
            state_manager.clear_active_task()
            return False

        print(f"[cyan]Renaming task '{task.content}' to '{new_task_name}'[/cyan]")
        update_success = api.update_task(task_id=task_id, content=new_task_name)

        if update_success:
            print(f"[green]Task successfully renamed to: '{new_task_name}'[/green]")
            # <<< MODIFIED: Update active task via state_manager wrapper >>>
            add_to_active_task_file(new_task_name, task_id, active_task.get("task_due"))
            return True
        else:
            print(f"[red]Failed to rename task ID {task_id} via API.[/red]")
            return False

    except Exception as error:
        print(f"[red]An unexpected error occurred renaming task: {error}[/red]")
        traceback.print_exc()
        return False


def change_active_task_priority(api, user_message):
    """Changes the priority of the active Todoist task using state_manager."""
    try:
        parts = user_message.lower().split()
        if len(parts) < 2 or not parts[-1].isdigit():
             print("[red]Invalid format. Use 'priority <1|2|3|4>'.[/red]")
             return False
        priority_level_str = parts[-1]
        if priority_level_str not in ["1", "2", "3", "4"]:
            print("[red]Invalid priority level. Use 1-4.[/red]")
            return False
        priority_map = {"1": 4, "2": 3, "3": 2, "4": 1}
        todoist_priority = priority_map[priority_level_str]

        # <<< MODIFIED: Get active task via state_manager >>>
        active_task = state_manager.get_active_task()
        if not active_task:
            print(f"[red]Error: Active task not found. Cannot change priority.[/red]")
            return False
        task_id = active_task.get("task_id")
        if not task_id:
             print(f"[red]Error: 'task_id' missing in active task data.[/red]")
             return False

        task = api.get_task(task_id) # Verify task exists
        if not task:
            print(f"[yellow]Task ID {task_id} not found.[/yellow]")
            state_manager.clear_active_task()
            return False

        print(f"[cyan]Changing priority of '{task.content}' to P{priority_level_str}[/cyan]")
        update_success = api.update_task(task_id=task_id, priority=todoist_priority)

        if update_success:
            print(f"[green]Task priority updated to P{priority_level_str}.[/green]")
            # Note: Active task file doesn't store priority, so no update needed there
            return True
        else:
            print(f"[red]Failed to update priority for task ID {task_id} via API.[/red]")
            return False

    except Exception as error:
        print(f"[red]An unexpected error occurred changing priority: {error}[/red]")
        traceback.print_exc()
        return False

# Apply call counter decorator (No changes needed)
module_call_counter.apply_call_counter_to_all(globals(), __name__)