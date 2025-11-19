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
import traceback
import state_manager # <<< ADDED: Import state manager
import todoist_compat
from helper_display import get_task_display_info
import helper_hide # Import helper_hide to filter hidden tasks

# Import necessary functions from part1 or state_manager
from helper_todoist_part1 import (
    complete_todoist_task_by_id,
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

        project_name = _extract_primary_project_name(active_filter_query)

        task = helper_task_factory.create_task(
            api=api,
            task_content=task_content,
            task_type="normal",
            options={"project_id": project_id, "project_name": project_name} # Pass identifiers for fallback logic
        )

        if task and getattr(task, "id", None):
            # Task factory handles success/failure messages
            # Consider displaying tasks after adding?
            # display_todoist_tasks(api)
            task_id = getattr(task, 'id', 'N/A')
            due_string = getattr(getattr(task, 'due', None), 'string', None)
            # Attempt to find a concrete next due datetime; prefer the SDK's datetime/ date
            due_obj = getattr(task, 'due', None)
            next_due = None
            if due_obj is not None:
                # Todoist SDK v2 may expose 'datetime' (ISO string) or 'date'
                next_due = getattr(due_obj, 'datetime', None) or getattr(due_obj, 'date', None)
            schedule_str = due_string if due_string else ''
            next_due_str = next_due if next_due else ''
            details = []
            details.append(f"id={task_id}")
            if schedule_str:
                details.append(f"schedule: {schedule_str}")
            if next_due_str:
                details.append(f"next due: {next_due_str}")
            info = ", ".join(details)
            print(f"[green]Task created successfully. {info}[/green]")
            return task
        else:
            print("[red]Task creation failed.[/red]")
            return None

    except ImportError:
         print("[red]Error: Could not import helper_task_factory. Task creation failed.[/red]")
         return None
    except Exception as error:
        print(f"[red]An unexpected error occurred adding task: {error}[/red]")
        traceback.print_exc()
        return None


def _extract_primary_project_name(filter_query: str | None) -> str | None:
    if not filter_query:
        return None
    matches = re.findall(r"#([A-Za-z0-9_\-]+)", filter_query)
    return matches[0] if matches else None


def fetch_todoist_tasks(api):
    """Fetches and sorts tasks based on the active filter (obtained via state_manager)."""
    # Timeout logic remains
    if hasattr(signal, 'SIGALRM'):
        def handler(signum, frame):
            raise TimeoutError("Todoist task fetch timed out after 5 seconds")
    # else: # Warning printed elsewhere

    active_filter_query, _ = state_manager.get_active_filter_details()
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

            tasks = todoist_compat.get_tasks_by_filter(api, active_filter_query)

            if hasattr(signal, 'SIGALRM'): signal.alarm(0)

            if not isinstance(tasks, list):
                print(f"[red]Error: API returned unexpected data type: {type(tasks)}[/red]")
                return None

            # --- Filter out hidden tasks ---
            hidden_task_ids = helper_hide.get_hidden_task_ids_for_today()
            if hidden_task_ids:
                original_count = len(tasks)
                tasks = [task for task in tasks if getattr(task, 'id', None) not in hidden_task_ids]
                if original_count > len(tasks):
                    print(f"[dim yellow]Filtered out {original_count - len(tasks)} hidden tasks for today.[/dim yellow]")
            # --- End filter out hidden tasks ---

            # Timezone processing logic remains the same...
            london_tz = pytz.timezone("Europe/London")
            now_utc = datetime.datetime.now(timezone.utc)
            now_london = now_utc.astimezone(london_tz)
            processed_tasks = []
            for task in tasks:
                try:
                    task.has_time = False
                    # Default fields
                    task.due_string_raw = None
                    task.is_recurring_flag = False

                    if getattr(task, 'due', None):
                        task.due_string_raw = getattr(task.due, 'string', None)
                        task.is_recurring_flag = getattr(task.due, 'is_recurring', False)

                        due_val = getattr(task.due, 'date', None)
                        london_dt = None
                        # due_val may be a string or a datetime depending on SDK parsing
                        if due_val is not None:
                            if isinstance(due_val, str):
                                try:
                                    # If the string contains time (T), parse as datetime; else parse as date
                                    if 'T' in due_val:
                                        dt = parse(due_val)
                                        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                                            try:
                                                london_dt = london_tz.localize(dt, is_dst=None)
                                            except pytz.exceptions.AmbiguousTimeError:
                                                london_dt = london_tz.localize(dt, is_dst=True)
                                            except pytz.exceptions.NonExistentTimeError:
                                                london_dt = dt
                                        else:
                                            london_dt = dt.astimezone(london_tz)
                                        task.has_time = True
                                    else:
                                        d = parse(due_val).date()
                                        if d <= now_london.date():
                                            london_dt = london_tz.localize(datetime.datetime.combine(d, now_london.time()))
                                        else:
                                            london_dt = london_tz.localize(datetime.datetime.combine(d, datetime.time(0, 1)))
                                        task.has_time = False
                                except Exception as e:
                                    # Fall back to now if parsing fails
                                    london_dt = now_london
                                    task.has_time = False
                            elif isinstance(due_val, datetime.datetime):
                                dt = due_val
                                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                                    try:
                                        london_dt = london_tz.localize(dt, is_dst=None)
                                    except pytz.exceptions.AmbiguousTimeError:
                                        london_dt = london_tz.localize(dt, is_dst=True)
                                    except pytz.exceptions.NonExistentTimeError:
                                        london_dt = dt
                                else:
                                    london_dt = dt.astimezone(london_tz)
                                task.has_time = True
                            elif isinstance(due_val, datetime.date):
                                d = due_val
                                if d <= now_london.date():
                                    london_dt = london_tz.localize(datetime.datetime.combine(d, now_london.time()))
                                else:
                                    london_dt = london_tz.localize(datetime.datetime.combine(d, datetime.time(0, 1)))
                                task.has_time = False
                            else:
                                # Unexpected type; default
                                london_dt = now_london
                                task.has_time = False
                        else:
                            london_dt = now_london
                            task.has_time = False

                        # Attach the computed localized datetime for downstream display/sorting
                        setattr(task.due, 'datetime_localized', london_dt)
                    else:
                        # Create a lightweight due-like object to simplify rendering logic
                        task.due = type('Due', (object,), { 'datetime_localized': now_london, 'string': None, 'is_recurring': False })()
                        task.has_time = False

                    # created_at can be string or datetime per SDK; normalize to datetime for sorting
                    created_val = getattr(task, 'created_at', None)
                    if isinstance(created_val, str):
                        try:
                            task.created_at_sortable = parse(created_val)
                        except Exception:
                            task.created_at_sortable = datetime.datetime.min.replace(tzinfo=pytz.utc)
                    elif isinstance(created_val, datetime.datetime):
                        task.created_at_sortable = created_val
                    else:
                        task.created_at_sortable = datetime.datetime.min.replace(tzinfo=pytz.utc)

                    processed_tasks.append(task)
                except Exception as process_error:
                    print(f"[yellow]Warn: Err processing task {getattr(task, 'id', 'N/A')}: {process_error}. Skip.[/yellow]")

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

        # Display the next long-term task (one at a time)
        try:
            helper_todoist_long.display_next_long_task(api)
        except Exception as long_term_error:
            print(f"[red]Error displaying next long-term task: {long_term_error}[/red]")
            # traceback.print_exc() # Can be verbose
            print()

    except Exception as e:
        print(f"[red]An unexpected error occurred in get_next_todoist_task: {e}[/red]")
        traceback.print_exc()
        print("Continuing...\n")


# moved: display_todoist_tasks


from helper_display import check_if_grafting


from helper_task_edit import rename_todoist_task


from helper_task_edit import change_active_task_priority

# Apply call counter decorator (No changes needed)
module_call_counter.apply_call_counter_to_all(globals(), __name__)
