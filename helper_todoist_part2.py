import re, json, pytz, datetime, time, os, signal, subprocess
# Import timedelta here
from datetime import timedelta
import module_call_counter, helper_todoist_long
from dateutil.parser import parse
from rich import print

# Import necessary functions from part1
from helper_todoist_part1 import (
    get_active_filter,
    complete_todoist_task_by_id,
    format_due_time,
    add_to_active_task_file,
)


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
            # print(f"[purple]Task '{task.content}' successfully added (ID: {task.id}).[/purple]") # Factory handles this
            return task # Return the created task object
        else:
            # Task factory handles its own success/failure messages and logging
            # print("[red]Failed to add task using task factory.[/red]") # Factory handles this
            return None # Indicate failure

    except ImportError:
         print("[red]Error: Could not import helper_task_factory. Task creation failed.[/red]")
         return None
    except Exception as error:
        print(f"[red]An unexpected error occurred adding task: {error}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()
        return None

def fetch_todoist_tasks(api):
    """Fetches and sorts tasks based on the active filter with timeout and retries."""
    # Timeout logic (Unix specific)
    if hasattr(signal, 'SIGALRM'):
        def handler(signum, frame):
            raise TimeoutError("Todoist task fetch timed out after 5 seconds")
    else:
        print("[yellow]Warning: signal.SIGALRM not available. Cannot enforce timeout per attempt.[/yellow]")


    active_filter, project_id = get_active_filter() # project_id not used here, only filter
    if not active_filter:
        # Message handled by get_active_filter
        # print("[yellow]No active filter configured. Cannot fetch tasks.[/yellow]")
        return None # Return None to indicate failure

    retries = 3 # Reduced retries from 99 to a more reasonable number
    retry_delay = 2 # seconds

    for attempt in range(retries):
        try:
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(5) # 5-second timeout for this attempt

            print(f"[cyan]Fetching tasks with filter: '{active_filter}' (Attempt {attempt + 1}/{retries})[/cyan]")
            tasks = api.get_tasks(filter=active_filter)

            if hasattr(signal, 'SIGALRM'): signal.alarm(0) # Disable alarm after successful call

            # Basic validation
            if not isinstance(tasks, list):
                print(f"[red]Error: Todoist API returned unexpected data type: {type(tasks)}[/red]")
                return None # Cannot proceed

            london_tz = pytz.timezone("Europe/London")
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            now_london = now_utc.astimezone(london_tz)

            processed_tasks = []
            for task in tasks:
                # Add error handling for task processing
                try:
                    task.has_time = False # Default
                    # Ensure task.due is not None before accessing attributes
                    if task.due:
                        if task.due.datetime:
                            # Parse and localize datetime
                            utc_dt = parse(task.due.datetime)
                            # Ensure it's timezone-aware before converting
                            if utc_dt.tzinfo is None or utc_dt.tzinfo.utcoffset(utc_dt) is None:
                                utc_dt = pytz.utc.localize(utc_dt) # Assume UTC if naive
                            london_dt = utc_dt.astimezone(london_tz)
                            task.due.datetime_localized = london_dt # Store localized version
                            task.has_time = True
                        elif task.due.date:
                            # Handle date-only tasks - assign a time for sorting (e.g., start of day in London)
                            due_date = parse(task.due.date).date()
                            # Assign noon London time for sorting all-day tasks consistently
                            london_dt = london_tz.localize(datetime.datetime.combine(due_date, datetime.time(12, 0)))
                            task.due.datetime_localized = london_dt
                            task.has_time = False # Still considered 'all-day'
                        else: # Due object exists but no date/datetime (should be rare)
                            # Assign a far future date/time for sorting last
                            task.due.datetime_localized = london_tz.localize(datetime.datetime.max - timedelta(days=1))
                            task.has_time = False

                    else:
                        # Task has no due date at all
                        # Assign a very far future date/time for sorting last
                        task.due = type("Due", (object,), {"datetime_localized": london_tz.localize(datetime.datetime.max - timedelta(days=1))})()
                        task.has_time = False

                    # Add creation time for tie-breaking if available
                    # Use a default far past date if 'created' attribute is missing
                    task.created_at_sortable = parse(task.created_at) if hasattr(task, 'created_at') and task.created_at else datetime.datetime.min.replace(tzinfo=pytz.utc)

                    processed_tasks.append(task)

                except Exception as process_error:
                    # Print specific error for easier debugging
                    print(f"[yellow]Warning: Error processing task ID {getattr(task, 'id', 'N/A')} ('{getattr(task, 'content', 'N/A')}'): {process_error}. Skipping task.[/yellow]")
                    # Log stack trace if needed for complex errors
                    # import traceback
                    # traceback.print_exc()


            # Sort processed tasks
            # Sort by: Priority (high first), Due Date/Time (earliest first), Has Time (no time sorts later), Creation Time (earliest first)
            sorted_final_tasks = sorted(
                processed_tasks,
                key=lambda t: (
                    -getattr(t, 'priority', 1), # Default to lowest priority (P4=1) if missing
                    getattr(t.due, 'datetime_localized', now_london) if t.due else now_london, # Sort by localized time, default now
                    getattr(t, 'has_time', False), # False (no time) sorts after True (has time)
                    getattr(t, 'created_at_sortable', datetime.datetime.min.replace(tzinfo=pytz.utc)) # Earliest created first
                ),
            )

            print(f"[green]Successfully fetched and processed {len(sorted_final_tasks)} tasks.[/green]")
            return sorted_final_tasks # Success

        except TimeoutError as te:
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)
            print(f"[yellow]Attempt {attempt + 1}: Task fetch timed out. {te}. Retrying...[/yellow]")
        except Exception as e:
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)
            print(f"[red]Attempt {attempt + 1}: Error fetching tasks: {e}[/red]")
            # Log stack trace
            import traceback
            traceback.print_exc()
            # Consider returning None immediately on certain API errors (e.g., auth failure)

        # Wait before retrying
        if attempt < retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    # If loop finishes without success
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
                      task_due_iso = next_task.due.datetime_localized.isoformat()
                 except Exception as iso_err:
                      print(f"[yellow]Warning: Could not format localized due date for saving: {iso_err}[/yellow]")


            # Prepare details for active task file
            active_task_details = (original_task_name, task_id, task_due_iso)

            # Display logic
            print("[bold green]--- Next Task ---[/bold green]")
            try:
                # Use the already fetched task data for display
                task_display = next_task

                display_info = get_task_display_info(task_display) # Use helper for formatting
                due_display_str = ""

                # Determine display string for due date/time
                if task_display.due:
                     if hasattr(task_display.due, 'datetime_localized') and task_display.due.datetime_localized:
                         try:
                              # Check if it's the far future date we assigned
                              london_tz = pytz.timezone("Europe/London")
                              far_future = london_tz.localize(datetime.datetime.max - timedelta(days=1))
                              if task_display.due.datetime_localized == far_future:
                                   due_display_str = "(No due date)"
                              elif getattr(task_display, 'has_time', False):
                                   due_display_str = f"(Due: {task_display.due.datetime_localized.strftime('%Y-%m-%d %H:%M')})"
                              else: # All day task
                                   due_display_str = f"(Due: {task_display.due.datetime_localized.strftime('%Y-%m-%d')} All day)"
                         except Exception as fmt_err:
                              print(f"[yellow]Warning: Error formatting due date for display: {fmt_err}[/yellow]")
                              due_display_str = "(Due info error)"
                     elif hasattr(task_display.due, 'string') and task_display.due.string: # Fallback to due string
                          due_display_str = f"(Due: {task_display.due.string})"


                # Check if task is in the future (using localized times)
                is_future = False
                future_time_str = ""
                if task_display.due and hasattr(task_display.due, 'datetime_localized') and task_display.due.datetime_localized:
                    try:
                        london_tz = pytz.timezone("Europe/London")
                        now_london = datetime.datetime.now(london_tz)
                        # Add a small buffer (e.g., 1 minute) to avoid marking tasks due 'right now' as future
                        if task_display.due.datetime_localized > (now_london + timedelta(minutes=1)):
                             # Avoid showing future if it's the 'far future' placeholder date
                             far_future = london_tz.localize(datetime.datetime.max - timedelta(days=1))
                             if task_display.due.datetime_localized != far_future and getattr(task_display, 'has_time', False):
                                  is_future = True
                                  future_time_str = task_display.due.datetime_localized.strftime('%H:%M')
                    except Exception as future_check_err:
                         print(f"[yellow]Warning: Error checking if task is in the future: {future_check_err}[/yellow]")


                # Print the task line
                if is_future:
                    print(f"                   [orange1]{display_info}{original_task_name} (next task due at {future_time_str})[/orange1]")
                else:
                     print(f"                   [green]{display_info}{original_task_name} {due_display_str}[/green]")

                # Print description if it exists
                if getattr(task_display, 'description', None):
                    # Indent description for clarity
                    print(f"                   [italic blue]  Desc: {task_display.description}[/italic blue]")

                print() # Add a newline for spacing

            except Exception as display_error:
                 print(f"[red]Error preparing next task display: {display_error}[/red]")
                 # Log stack trace
                 import traceback
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
        print("[bold cyan]--- Long Term Tasks (Due) ---[/bold cyan]")
        try:
            # Get categorized tasks
            one_shot_tasks, recurring_tasks = helper_todoist_long.get_categorized_tasks(api)

            # Display one-shot tasks
            print("\nOne Shots:")
            if one_shot_tasks:
                for task in one_shot_tasks:
                    formatted_task = helper_todoist_long.format_task_for_display(task)
                    print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
            else:
                print("[dim]  No one-shot tasks due.[/dim]")

            # Display recurring tasks
            print("\nRecurring:")
            if recurring_tasks:
                for task in recurring_tasks:
                    formatted_task = helper_todoist_long.format_task_for_display(task)
                    print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
            else:
                print("[dim]  No recurring tasks due.[/dim]")
            print()
        except Exception as long_term_error:
            print(f"[red]Error processing or displaying long-term tasks: {long_term_error}[/red]")
            # Log stack trace
            # import traceback
            # traceback.print_exc()
            print()

    except Exception as e:
        print(f"[red]An unexpected error occurred in get_next_todoist_task: {e}[/red]")
        # Log stack trace
        import traceback
        traceback.print_exc()
        print("Continuing...")
        print()
        return # Exit function on major error

def get_task_display_info(task):
    """Generates a prefix string for task display including recurring and priority info."""
    display_info = ""
    if not task: return "" # Handle case where task is None

    try:
        # Check recurrence
        is_recurring = False
        if task.due:
             if hasattr(task.due, 'is_recurring') and task.due.is_recurring:
                  is_recurring = True
             elif hasattr(task.due, 'string') and isinstance(task.due.string, str):
                  recurrence_patterns = ['every', 'daily', 'weekly', 'monthly', 'yearly']
                  if any(pattern in task.due.string.lower() for pattern in recurrence_patterns):
                       is_recurring = True

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
    # london_tz = pytz.timezone("Europe/London") # Not needed directly here if fetch_tasks adds localized

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
            prefix = get_task_display_info(task)
            due_display = "(No due date)" # Default

            if task.due and hasattr(task.due, 'datetime_localized') and task.due.datetime_localized:
                 try:
                     london_tz = pytz.timezone("Europe/London") # Define here or pass in
                     far_future = london_tz.localize(datetime.datetime.max - timedelta(days=1))
                     if task.due.datetime_localized != far_future:
                         if getattr(task, 'has_time', False):
                              due_display = task.due.datetime_localized.strftime("%Y-%m-%d %H:%M")
                         else: # All day
                              due_display = task.due.datetime_localized.strftime("%Y-%m-%d") + " All day"
                 except Exception as fmt_err:
                      print(f"[yellow]Warn: Err fmt due for disp {getattr(task, 'id', 'N/A')}: {fmt_err}[/yellow]")
                      due_display = "(Due Error)"

            elif task.due and hasattr(task.due, 'string') and task.due.string: # Fallback
                 due_display = task.due.string


            display_data.append({
                "prefix": prefix,
                "due": due_display,
                "content": getattr(task, 'content', 'Unknown Content'),
                "description": getattr(task, 'description', None)
            })
        except Exception as e:
             print(f"[yellow]Warning: Error processing task {getattr(task, 'id', 'N/A')} for display: {e}[/yellow]")


    # Print formatted tasks - Simpler alignment approach
    max_due_len = 0
    if display_data:
        try:
            max_due_len = max(len(data['due']) for data in display_data)
        except ValueError: # Handle empty display_data case
             pass

    tab = "    " # 4 spaces for indentation

    for data in display_data:
        # Pad due string for alignment
        due_padded = data['due'].ljust(max_due_len)
        line = f"{due_padded}{tab}{data['prefix']}{data['content']}"
        print(line)

        # Display description if it exists, indented
        if data['description']:
            desc_indent = " " * (max_due_len + len(tab)) # Align under content
            for desc_line in data['description'].splitlines():
                 print(f"{desc_indent}[italic blue]Desc: {desc_line}[/italic blue]")

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
                  # print(f"[yellow]Graft file '{graft_file_path}' exists but is empty/invalid. Grafting inactive.[/yellow]")
                  # os.remove(graft_file_path) # Optionally clean up
                  return False
         except (json.JSONDecodeError, IOError) as e:
              print(f"[red]Error reading graft file '{graft_file_path}': {e}. Assuming not grafting.[/red]")
              return False
         except Exception as e:
              print(f"[red]Unexpected error checking graft status: {e}[/red]")
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
        import traceback
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
        import traceback
        traceback.print_exc()
        return False

# Apply call counter decorator to all functions defined in this module
module_call_counter.apply_call_counter_to_all(globals(), __name__)