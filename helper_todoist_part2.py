# File: helper_todoist_part2.py

import re, json, pytz, datetime, time, os, signal, subprocess
# Import timedelta
from datetime import timedelta, timezone # Ensure timezone is imported
import module_call_counter, helper_todoist_long
from dateutil.parser import parse
from rich import print
import traceback # Import traceback for logging

# Import necessary functions from part1
from helper_todoist_part1 import (
    get_active_filter,
    complete_todoist_task_by_id,
    format_due_time,
    add_to_active_task_file,
)
# Import API type hint if needed
# from todoist_api_python.api import TodoistAPI


def add_todoist_task(api, user_message):
    """Adds a new task to Todoist based on the active filter's project ID."""
    try:
        # Import locally to avoid circular dependency issues at module level
        import helper_task_factory

        active_filter, project_id = get_active_filter() # Fetches filter string and project ID
        # No need to check active_filter string here, but project_id is needed

        # Extract task content from user message
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
            print("[cyan]No project ID set in active filter; task will be added to Inbox (or default project).[/cyan]")

        # Use the factory to create the task
        # Pass only necessary options
        task = helper_task_factory.create_task(
            api=api,
            task_content=task_content,
            task_type="normal", # Explicitly normal task type
            options={"project_id": project_id} # Pass project_id from filter
        )

        if task:
            # Task factory handles its own success/failure messages and logging
            return task # Return the created task object
        else:
            # Task factory handles its own success/failure messages and logging
            return None # Indicate failure

    except ImportError:
         print("[red]Error: Could not import helper_task_factory. Task creation failed.[/red]")
         return None
    except Exception as error:
        print(f"[red]An unexpected error occurred adding task: {error}[/red]")
        # Log stack trace
        traceback.print_exc()
        return None


def fetch_todoist_tasks(api):
    """Fetches and sorts tasks based on the active filter with timeout, retries, and correct timezone handling."""
    # Timeout logic (Unix specific)
    if hasattr(signal, 'SIGALRM'):
        def handler(signum, frame):
            raise TimeoutError("Todoist task fetch timed out after 5 seconds")
    else:
        print("[yellow]Warning: signal.SIGALRM not available. Cannot enforce timeout per attempt.[/yellow]")


    active_filter, project_id = get_active_filter() # project_id not used here, only filter
    if not active_filter:
        return None # Return None to indicate failure

    retries = 3
    retry_delay = 2 # seconds

    for attempt in range(retries):
        try:
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(5) # 5-second timeout for this attempt

            tasks = api.get_tasks(filter=active_filter)

            if hasattr(signal, 'SIGALRM'): signal.alarm(0) # Disable alarm after successful call

            if not isinstance(tasks, list):
                print(f"[red]Error: Todoist API returned unexpected data type: {type(tasks)}[/red]")
                return None

            london_tz = pytz.timezone("Europe/London")
            now_utc = datetime.datetime.now(timezone.utc) # Use timezone.utc
            now_london = now_utc.astimezone(london_tz)

            processed_tasks = []
            for task in tasks:
                try:
                    task.has_time = False # Default
                    if task.due:
                        task.due_string_raw = getattr(task.due, 'string', None)
                        task.is_recurring_flag = getattr(task.due, 'is_recurring', False)

                        if task.due.datetime:
                            parsed_dt = parse(task.due.datetime)

                            # --- CORRECTED TIMEZONE LOGIC ---
                            if parsed_dt.tzinfo is None or parsed_dt.tzinfo.utcoffset(parsed_dt) is None:
                                # Naive datetime from API: ASSUME it's in the user's local timezone (London)
                                try:
                                    london_dt = london_tz.localize(parsed_dt, is_dst=None) # is_dst=None handles DST ambiguity automatically
                                except pytz.exceptions.AmbiguousTimeError:
                                     print(f"[yellow]Warning: Ambiguous time encountered for task {task.id} ('{task.content}') during DST changeover. Using first occurrence.[/yellow]")
                                     london_dt = london_tz.localize(parsed_dt, is_dst=True) # Or False, depending on preferred handling
                                except pytz.exceptions.NonExistentTimeError:
                                     print(f"[yellow]Warning: Non-existent time encountered for task {task.id} ('{task.content}') during DST changeover. Skipping time assignment.[/yellow]")
                                     # Assign a default or skip setting time? For now, let's assign the parsed naive time.
                                     london_dt = parsed_dt # Keep it naive, will sort later but display might be odd
                            else:
                                # Aware datetime from API (e.g., UTC 'Z'): Convert to London time
                                london_dt = parsed_dt.astimezone(london_tz)
                            # --- END CORRECTED TIMEZONE LOGIC ---

                            task.due.datetime_localized = london_dt # Store localized/converted version
                            task.has_time = True
                        elif task.due.date:
                            # Handle date-only tasks
                            due_date = parse(task.due.date).date()

                            # If due date is today or earlier, set the time to current time
                            # so it appears in the correct position relative to time-specific tasks
                            if due_date <= now_london.date():
                                # Use current time for today's or overdue all-day tasks
                                london_dt = london_tz.localize(datetime.datetime.combine(due_date, now_london.time()))
                            else:
                                # Future all-day tasks still get early morning time
                                london_dt = london_tz.localize(datetime.datetime.combine(due_date, datetime.time(0, 1)))

                            task.due.datetime_localized = london_dt
                            task.has_time = False
                        else: # Due object exists but no date/datetime
                            # --- CHANGE HERE: Assign current time instead of max date ---
                            task.due.datetime_localized = now_london
                            task.has_time = False # No specific user-set time
                            task.due_string_raw = None
                            task.is_recurring_flag = False

                    else:
                        # Task has no due date at all
                        task.due = type("Due", (object,), {
                            # --- CHANGE HERE: Assign current time instead of max date ---
                            "datetime_localized": now_london,
                            "string": None,
                            "is_recurring": False
                            })()
                        task.has_time = False # No specific user-set time
                        task.due_string_raw = None
                        task.is_recurring_flag = False

                    task.created_at_sortable = parse(task.created_at) if hasattr(task, 'created_at') and task.created_at else datetime.datetime.min.replace(tzinfo=pytz.utc)
                    processed_tasks.append(task)

                except Exception as process_error:
                    print(f"[yellow]Warning: Error processing task ID {getattr(task, 'id', 'N/A')} ('{getattr(task, 'content', 'N/A')}'): {process_error}. Skipping task.[/yellow]")
                    traceback.print_exc()

            # Sort processed tasks (Sort key remains the same)
            sorted_final_tasks = sorted(
                processed_tasks,
                key=lambda t: (
                    -getattr(t, 'priority', 1),
                    getattr(t.due, 'datetime_localized', now_london) if t.due else now_london, # Use the assigned datetime_localized
                    getattr(t, 'has_time', False),
                    getattr(t, 'created_at_sortable', datetime.datetime.min.replace(tzinfo=pytz.utc))
                ),
            )

            return sorted_final_tasks # Success

        except TimeoutError as te:
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)
            print(f"[yellow]Attempt {attempt + 1}: Task fetch timed out. {te}. Retrying...[/yellow]")
        except Exception as e:
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)
            print(f"[red]Attempt {attempt + 1}: Error fetching tasks: {e}[/red]")
            traceback.print_exc()

        if attempt < retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    print(f"[red]Failed to fetch tasks after {retries} attempts.[/red]")
    return None


def get_next_todoist_task(api):
    """Gets the next task, displays it, and saves it as the active task."""
    try:
        tasks = fetch_todoist_tasks(api)
        if tasks is None: # Handle fetch failure
            print("[yellow]Unable to fetch tasks to determine the next one.[/yellow]")
            print()
            return # Cannot proceed

        active_task_details = None # To store details of the task to be set as active

        if tasks:
            next_task = tasks[0]
            original_task_name = getattr(next_task, 'content', 'Unknown Task')
            task_id = getattr(next_task, 'id', None)

            if not task_id:
                 print("[red]Error: Could not determine ID of the next task. Cannot proceed.[/red]")
                 return

            # Use the localized datetime for storing if available
            task_due_iso = None
            if next_task.due and hasattr(next_task.due, 'datetime_localized') and next_task.due.datetime_localized:
                 try:
                    # Define now_london within this scope for comparison
                    london_tz = pytz.timezone("Europe/London")
                    now_utc = datetime.datetime.now(timezone.utc) # Use timezone.utc
                    now_london = now_utc.astimezone(london_tz)
                    # Avoid saving the 'now' timestamp we assigned to non-dated tasks
                    if next_task.due.datetime_localized != now_london:
                        # Ensure the datetime object is not naive before calling isoformat if pytz errors occurred during localize
                        if hasattr(next_task.due.datetime_localized, 'tzinfo') and next_task.due.datetime_localized.tzinfo is not None:
                            task_due_iso = next_task.due.datetime_localized.isoformat()
                        else:
                            print(f"[yellow]Warning: Skipping ISO format save for task {task_id} due to missing timezone info after processing.[/yellow]")
                 except Exception as iso_err:
                      print(f"[yellow]Warning: Could not format localized due date for saving: {iso_err}[/yellow]")


            # Prepare details for active task file
            active_task_details = (original_task_name, task_id, task_due_iso)

            # Display logic
            print("[bold green]--- Next Task ---[/bold green]")
            try:
                # Use the already fetched task data for display
                task_display = next_task

                # Get base display info (priority)
                # We handle the (r) marker and schedule string separately now
                base_display_info = get_task_display_info(task_display, include_recurring_marker=False)
                due_display_str = ""
                recurring_schedule_prefix = "" # Holds '(r) schedule - ' if applicable

                # Check if recurring and build prefix
                is_recurring = getattr(task_display, 'is_recurring_flag', False)
                due_string = getattr(task_display, 'due_string_raw', None)

                if is_recurring:
                    if due_string:
                        recurring_schedule_prefix = f"[cyan](r) {due_string}[/cyan] - "
                    else:
                        recurring_schedule_prefix = "[cyan](r)[/cyan] " # Fallback if no string

                # Determine display string for due date/time
                if task_display.due:
                     if hasattr(task_display.due, 'datetime_localized') and task_display.due.datetime_localized:
                         try:
                              # Define now_london within this scope for comparison
                              london_tz = pytz.timezone("Europe/London")
                              now_utc = datetime.datetime.now(timezone.utc) # Use timezone.utc
                              now_london = now_utc.astimezone(london_tz)

                              # Check if datetime_localized is aware before comparing/formatting
                              if hasattr(task_display.due.datetime_localized, 'tzinfo') and task_display.due.datetime_localized.tzinfo is not None:
                                  # Check if it's the 'now' timestamp we assigned
                                  # Need a small buffer for comparison due to potential microsecond differences
                                  time_diff = abs(task_display.due.datetime_localized - now_london)
                                  is_effectively_now = time_diff < timedelta(seconds=1)

                                  if is_effectively_now and not getattr(task_display, 'has_time', False): # Check if it was originally undated
                                       due_display_str = "(No due date)"
                                  elif getattr(task_display, 'has_time', False):
                                       due_display_str = f"(Due: {task_display.due.datetime_localized.strftime('%Y-%m-%d %H:%M')})"
                                  else: # All day task (not assigned 'now')
                                       due_display_str = f"(Due: {task_display.due.datetime_localized.strftime('%Y-%m-%d')} All day)"
                              else: # It remained naive after processing (e.g., NonExistentTimeError)
                                   due_display_str = f"(Due: {task_display.due.datetime_localized.strftime('%Y-%m-%d %H:%M')} ?TZ?)" # Indicate missing TZ

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
                        # Define now_london within this scope for comparison
                        london_tz = pytz.timezone("Europe/London")
                        now_utc = datetime.datetime.now(timezone.utc) # Use timezone.utc
                        now_london = now_utc.astimezone(london_tz)
                        # Check if aware before comparing
                        if hasattr(task_display.due.datetime_localized, 'tzinfo') and task_display.due.datetime_localized.tzinfo is not None:
                            if task_display.due.datetime_localized > (now_london + timedelta(minutes=1)):
                                # Avoid showing future if it's effectively 'now' and was originally undated
                                time_diff = abs(task_display.due.datetime_localized - now_london)
                                is_effectively_now = time_diff < timedelta(seconds=1)
                                if not (is_effectively_now and not getattr(task_display, 'has_time', False)) and getattr(task_display, 'has_time', False):
                                     is_future = True
                                     future_time_str = task_display.due.datetime_localized.strftime('%H:%M')
                    except Exception as future_check_err:
                         print(f"[yellow]Warning: Error checking if task is in the future: {future_check_err}[/yellow]")


                # Print the task line, incorporating the recurring schedule prefix
                if is_future:
                    print(f"                   [orange1]{base_display_info}{recurring_schedule_prefix}{original_task_name} (next task due at {future_time_str})[/orange1]")
                else:
                     # Added due_display_str here for context
                     print(f"                   [green]{base_display_info}{recurring_schedule_prefix}{original_task_name} {due_display_str}[/green]")

                # Print description if it exists
                if getattr(task_display, 'description', None):
                    # Indent description for clarity
                    print(f"                   [italic blue]  Desc: {task_display.description}[/italic blue]")

                print() # Add a newline for spacing

            except Exception as display_error:
                 print(f"[red]Error preparing next task display: {display_error}[/red]")
                 # Log stack trace
                 traceback.print_exc()
                 # Fallback display
                 print(f"                   [green]{original_task_name}[/green]")
                 print()

        else:
            # No tasks found matching the filter
            print("\u2705 [bold green]All tasks complete! \u2705[/bold green]")
            print()
            # Clear active task file if no tasks are left
            active_task_file = "j_active_task.json"
            if os.path.exists(active_task_file):
                try:
                    os.remove(active_task_file)
                    print(f"[cyan]Cleared active task file as no tasks remain.[/cyan]")
                except OSError as e:
                    print(f"[red]Error clearing active task file {active_task_file}: {e}[/red]")


        # Save the identified next task (or clear if none) - outside display logic
        if active_task_details:
            try:
                name, tid, tdue = active_task_details
                add_to_active_task_file(name, tid, tdue)
                # print(f"[cyan]Saved '{name}' as active task.[/cyan]") # Optional confirmation
            except Exception as save_error:
                # add_to_active_task_file handles its own errors, but catch unexpected ones here
                print(f"[red]Unexpected error saving active task file: {save_error}[/red]")


        # Display long-term tasks (consider making this optional or a separate command)
        try:
            # Display long term tasks (function now handles its own title printing)
            helper_todoist_long.display_tasks(api)
        except Exception as long_term_error:
            print(f"[red]Error processing or displaying long-term tasks: {long_term_error}[/red]")
            # Log stack trace
            traceback.print_exc()
            print()

    except Exception as e:
        print(f"[red]An unexpected error occurred in get_next_todoist_task: {e}[/red]")
        # Log stack trace
        traceback.print_exc()
        print("Continuing...")
        print()
        return # Exit function on major error


def get_task_display_info(task, include_recurring_marker=True):
    """
    Generates a prefix string for task display including recurring (optional) and priority info.
    """
    display_info = ""
    if not task: return "" # Handle case where task is None

    try:
        # Check recurrence if requested
        if include_recurring_marker:
            is_recurring = getattr(task, 'is_recurring_flag', False)
            if is_recurring:
                display_info += "[cyan](r)[/cyan] "

        # Check priority
        priority = getattr(task, 'priority', None)
        if isinstance(priority, int) and priority > 1: # P1, P2, P3 (Todoist values 4, 3, 2)
             priority_map = {4: 1, 3: 2, 2: 3}
             display_p = priority_map.get(priority)
             if display_p:
                 color_map = {1: "red", 2: "orange1", 3: "yellow"}
                 color = color_map.get(display_p, "white")
                 display_info += f"[bold {color}](p{display_p})[/bold {color}] "

    except Exception as e:
         # Log error but don't crash the display
         print(f"[yellow]Warning: Error generating display info for task {getattr(task, 'id', 'N/A')}: {e}[/yellow]")

    return display_info


def display_todoist_tasks(api):
    """Fetches and displays all tasks from the active filter, formatted."""
    print("[cyan]Fetching tasks for display...[/cyan]")
    tasks = fetch_todoist_tasks(api) # Reuse the main fetching logic

    if tasks is None:
        print("[red]Could not fetch tasks to display.[/red]")
        return
    if not tasks:
        print("[green]No tasks found matching the active filter.[/green]")
        return

    print("[bold magenta]--- Current Tasks ---[/bold magenta]")
    display_data = []

    # Pre-process tasks for display data
    for task in tasks:
        try:
            # Get base info (priority)
            base_display_info = get_task_display_info(task, include_recurring_marker=False)
            recurring_schedule_prefix = ""
            due_display = "(No due date)" # Default

            # Check recurring and build prefix
            is_recurring = getattr(task, 'is_recurring_flag', False)
            due_string = getattr(task, 'due_string_raw', None)
            if is_recurring:
                if due_string:
                    recurring_schedule_prefix = f"[cyan](r) {due_string}[/cyan] - "
                else:
                    recurring_schedule_prefix = "[cyan](r)[/cyan] "

            # Format due date/time
            if task.due and hasattr(task.due, 'datetime_localized') and task.due.datetime_localized:
                 try:
                    # Define now_london within this scope for comparison
                    london_tz = pytz.timezone("Europe/London")
                    now_utc = datetime.datetime.now(timezone.utc) # Use timezone.utc
                    now_london = now_utc.astimezone(london_tz)

                    # Check if datetime_localized is aware before comparing/formatting
                    if hasattr(task.due.datetime_localized, 'tzinfo') and task.due.datetime_localized.tzinfo is not None:
                        # Check if it's the 'now' timestamp we assigned
                        time_diff = abs(task.due.datetime_localized - now_london)
                        is_effectively_now = time_diff < timedelta(seconds=1)

                        if not (is_effectively_now and not getattr(task, 'has_time', False)): # Check if it was originally undated
                            if getattr(task, 'has_time', False):
                                due_display = task.due.datetime_localized.strftime("%Y-%m-%d %H:%M")
                            else: # All day
                                due_display = task.due.datetime_localized.strftime("%Y-%m-%d") + " All day"
                         # else: keep due_display as "(No due date)"

                    else: # Remained naive
                         due_display = f"{task.due.datetime_localized.strftime('%Y-%m-%d %H:%M')} ?TZ?" # Indicate TZ issue

                 except Exception as fmt_err:
                      print(f"[yellow]Warn: Err fmt due for disp {getattr(task, 'id', 'N/A')}: {fmt_err}[/yellow]")
                      due_display = "(Due Error)"
            elif due_string: # Fallback to raw string
                 due_display = due_string


            display_data.append({
                "prefix": base_display_info, # Just priority marker
                "recurring_prefix": recurring_schedule_prefix, # (r) schedule -
                "due": due_display,
                "content": getattr(task, 'content', 'Unknown Content'),
                "description": getattr(task, 'description', None)
            })
        except Exception as e:
             print(f"[yellow]Warning: Error processing task {getattr(task, 'id', 'N/A')} for display: {e}[/yellow]")
             traceback.print_exc() # Log stack trace for processing errors


    # Print formatted tasks - Simpler alignment approach
    max_due_len = 0
    if display_data:
        try:
            # Find max length considering only the date/time part for alignment
            max_due_len = max(len(data['due']) for data in display_data)
        except ValueError: # Handle empty display_data case
             pass

    tab = "    " # 4 spaces for indentation

    for data in display_data:
        try:
            # Pad due string for alignment
            due_padded = data['due'].ljust(max_due_len)
            # Combine prefixes and content
            full_prefix = data['prefix'] + data['recurring_prefix']
            line = f"{due_padded}{tab}{full_prefix}{data['content']}"
            print(line)

            # Display description if it exists, indented
            if data['description']:
                # Calculate indent based on padded due length and tab
                desc_indent = " " * (max_due_len + len(tab))
                for desc_line in data['description'].splitlines():
                     print(f"{desc_indent}[italic blue]Desc: {desc_line}[/italic blue]")
        except Exception as e:
            print(f"[red]Error printing line for task '{data.get('content', 'N/A')}': {e}[/red]")
            traceback.print_exc()


    print("[bold magenta]---------------------[/bold magenta]")


def check_if_grafting(api):
     """Checks if the graft file exists and displays graft status."""
     graft_file_path = "j_grafted_tasks.json"
     if os.path.exists(graft_file_path):
         try:
             with open(graft_file_path, "r") as file:
                 grafted_tasks = json.load(file)
             if isinstance(grafted_tasks, list) and grafted_tasks:
                 print("[bold red]*** GRAFT MODE ACTIVE ***[/bold red]")
                 print("[yellow]Focus on these tasks:[/yellow]")
                 for i, task in enumerate(grafted_tasks):
                      if isinstance(task, dict) and "task_name" in task:
                           index = task.get("index", i + 1)
                           print(f"  {index}. {task['task_name']}")
                      else:
                           print(f"[yellow]  Warning: Invalid entry in graft file: {task}[/yellow]")

                 print()
                 return True
             else:
                  # File exists but is empty or invalid
                  # Optionally remove empty/invalid file
                  if os.path.getsize(graft_file_path) == 0 or not isinstance(grafted_tasks, list):
                      try:
                          os.remove(graft_file_path)
                          # print(f"[cyan]Removed empty/invalid graft file: {graft_file_path}[/cyan]")
                      except OSError as e:
                           print(f"[red]Error removing empty/invalid graft file {graft_file_path}: {e}[/red]")
                  return False
         except (json.JSONDecodeError, IOError) as e:
              print(f"[red]Error reading graft file '{graft_file_path}': {e}. Assuming not grafting.[/red]")
              return False
         except Exception as e:
              print(f"[red]Unexpected error checking graft status: {e}[/red]")
              traceback.print_exc() # Log unexpected errors
              return False
     else:
         return False


def rename_todoist_task(api, user_message):
    """Renames the active Todoist task."""
    active_task_file = "j_active_task.json"
    try:
        # 1. Extract New Name
        if not user_message.lower().startswith("rename "):
            print("[red]Invalid command format. Use 'rename <new task name>'.[/red]")
            return False
        new_task_name = user_message[len("rename "):].strip()
        if not new_task_name:
            print("[yellow]No new task name provided.[/yellow]")
            return False

        # 2. Get Active Task ID
        try:
            with open(active_task_file, "r") as infile:
                active_task = json.load(infile)
            task_id = active_task.get("task_id")
            old_task_name = active_task.get("task_name", "Unknown task")
            if not task_id:
                 print(f"[red]Error: 'task_id' missing in {active_task_file}. Cannot rename.[/red]")
                 return False
        except FileNotFoundError:
            print(f"[red]Error: Active task file '{active_task_file}' not found. Cannot rename.[/red]")
            return False
        except json.JSONDecodeError:
            print(f"[red]Error: Could not decode JSON from {active_task_file}. Cannot rename.[/red]")
            return False

        # 3. Verify Task Exists (Optional but good practice)
        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]Task ID {task_id} ('{old_task_name}') not found in Todoist. Cannot rename.[/yellow]")
            try: os.remove(active_task_file)
            except OSError as e: print(f"[red]Err removing stale file {active_task_file}: {e}[/red]")
            return False

        # 4. Update Task Content
        print(f"[cyan]Renaming task '{task.content}' to '{new_task_name}'[/cyan]")
        update_success = api.update_task(task_id=task_id, content=new_task_name)

        if update_success:
            print(f"[green]Task successfully renamed to: '{new_task_name}'[/green]")
            # Update the active task file with the new name
            add_to_active_task_file(new_task_name, task_id, active_task.get("task_due"))
            return True
        else:
            print(f"[red]Failed to rename task ID {task_id} via API.[/red]")
            return False

    except Exception as error:
        print(f"[red]An unexpected error occurred renaming task: {error}[/red]")
        # Log stack trace
        traceback.print_exc()
        return False


def change_active_task_priority(api, user_message):
    """Changes the priority of the active Todoist task."""
    active_task_file = "j_active_task.json"
    try:
        # 1. Extract Priority Level
        parts = user_message.lower().split()
        if len(parts) < 2 or not parts[-1].isdigit():
             print("[red]Invalid command format. Use 'priority <1|2|3|4>'.[/red]")
             return False
        priority_level_str = parts[-1]
        if priority_level_str not in ["1", "2", "3", "4"]:
            print("[red]Invalid priority level. Use 1 (P1), 2 (P2), 3 (P3), or 4 (P4).[/red]")
            return False
        priority_map = {"1": 4, "2": 3, "3": 2, "4": 1}
        todoist_priority = priority_map[priority_level_str]

        # 2. Get Active Task ID
        try:
            with open(active_task_file, "r") as infile:
                active_task = json.load(infile)
            task_id = active_task.get("task_id")
            task_name = active_task.get("task_name", "Unknown task")
            if not task_id:
                 print(f"[red]Error: 'task_id' missing in {active_task_file}. Cannot change priority.[/red]")
                 return False
        except FileNotFoundError:
            print(f"[red]Error: Active task file '{active_task_file}' not found.[/red]")
            return False
        except json.JSONDecodeError:
            print(f"[red]Error: Could not decode JSON from {active_task_file}.[/red]")
            return False

        # 3. Verify Task Exists (Optional)
        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]Task ID {task_id} ('{task_name}') not found in Todoist.[/yellow]")
            try: os.remove(active_task_file)
            except OSError as e: print(f"[red]Err removing stale file {active_task_file}: {e}[/red]")
            return False

        # 4. Update Task Priority
        print(f"[cyan]Changing priority of task '{task.content}' to P{priority_level_str}[/cyan]")
        update_success = api.update_task(task_id=task_id, priority=todoist_priority)

        if update_success:
            print(f"[green]Task priority successfully updated to P{priority_level_str}.[/green]")
            return True
        else:
            print(f"[red]Failed to update priority for task ID {task_id} via API.[/red]")
            return False

    except Exception as error:
        print(f"[red]An unexpected error occurred changing task priority: {error}[/red]")
        # Log stack trace
        traceback.print_exc()
        return False

# Apply call counter decorator to all functions defined in this module
module_call_counter.apply_call_counter_to_all(globals(), __name__)