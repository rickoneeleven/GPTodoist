import json, dateutil.parser, datetime, sys, os, signal, pyfiglet, time, uuid
import hashlib, platform
import module_call_counter
from dateutil.parser import parse
from datetime import timedelta
from rich import print

# Removed unused function: print_beast_mode_complete
# Removed unused function: datetime_to_str

def change_active_task():
    # Check if file exists before reading
    filter_file_path = "j_todoist_filters.json"
    if not os.path.exists(filter_file_path):
        print("[yellow]Filter file 'j_todoist_filters.json' not found. Cannot change active task.[/yellow]")
        # Optionally, create a default file here if desired
        return

    try:
        with open(filter_file_path, "r") as file:
            task_data = json.load(file)
        # Ensure task_data is a list
        if not isinstance(task_data, list):
             print(f"[red]Error: Expected a list in {filter_file_path}, found {type(task_data)}.[/red]")
             return

        # Check if 'isActive' key exists before accessing
        active_found = False
        for task in task_data:
            if isinstance(task, dict) and "isActive" in task:
                task["isActive"] = 1 - task["isActive"] # Simplified toggle
                active_found = True # Mark that we potentially changed something
            else:
                print(f"[yellow]Warning: Skipping invalid entry in {filter_file_path}: {task}[/yellow]")

        if not active_found:
            print(f"[yellow]Warning: No entries with 'isActive' key found in {filter_file_path}.[/yellow]")
            # Decide if you want to add a default active task here if none found

        with open(filter_file_path, "w") as file:
            json.dump(task_data, file, indent=2) # Added indent for consistency

    except json.JSONDecodeError:
        print(f"[red]Error reading JSON from {filter_file_path}. File might be corrupted.[/red]")
    except IOError as e:
        print(f"[red]Error accessing file {filter_file_path}: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred in change_active_task: {e}[/red]")


def add_to_active_task_file(task_name, task_id, task_due):
    active_task = {
        "task_name": task_name,
        "task_id": task_id,
        "task_due": task_due,
        "device_id": get_device_id(),
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat() # Use UTC for consistency
    }
    active_task_file = "j_active_task.json"
    try:
        with open(active_task_file, "w") as outfile:
            json.dump(active_task, outfile, indent=2)
    except IOError as e:
        print(f"[red]Error writing to active task file {active_task_file}: {e}[/red]")
    except Exception as e:
        # Log unexpected errors during file write
        print(f"[red]Unexpected error saving active task: {e}[/red]")
        # Potentially log stack trace here if needed for debugging
        # import traceback
        # traceback.print_exc()

def get_device_id():
    # Using a more robust set of identifiers if possible
    # Consider adding things like OS version, boot time if consistent enough
    try:
        system_info = [
            platform.node(),            # Network name
            platform.machine(),         # Machine type (e.g., 'x86_64')
            platform.processor(),       # Processor type (can be generic)
            str(uuid.getnode()),        # MAC address
            platform.system(),          # OS type (e.g., 'Linux', 'Windows')
            # platform.platform(),      # More detailed platform info (can vary)
            # os.getlogin(),            # Login name (might change)
        ]
        # Filter out potentially empty strings
        system_info = [info for info in system_info if info]

        if not system_info:
             # Fallback if no info could be gathered
             print("[yellow]Warning: Could not gather system info for device ID. Using random UUID.[/yellow]")
             return str(uuid.uuid4())

        unique_string = ':'.join(system_info)

        # Using SHA256 for better collision resistance than MD5
        device_id = hashlib.sha256(unique_string.encode()).hexdigest()

        return device_id
    except Exception as e:
        print(f"[red]Error generating device ID: {e}. Falling back to random UUID.[/red]")
        # Log stack trace if needed
        # import traceback
        # traceback.print_exc()
        return str(uuid.uuid4())

def get_active_filter():
    filter_file_path = "j_todoist_filters.json"
    default_filter = "(no due date | today | overdue) & !#Team Virtue" # Default if file missing/corrupt
    default_project_id = None

    if not os.path.exists(filter_file_path):
        print(f"[yellow]Filter file '{filter_file_path}' not found. Creating default.[/yellow]")
        try:
            with open(filter_file_path, "w") as json_file:
                mock_data = [
                    {
                        "id": 1, # Consider using UUIDs for IDs if adding/removing filters often
                        "filter": default_filter,
                        "isActive": 1,
                        "project_id": default_project_id,
                    }
                ]
                json.dump(mock_data, json_file, indent=2)
            return default_filter, default_project_id
        except IOError as e:
            print(f"[red]Error creating default filter file {filter_file_path}: {e}[/red]")
            print(f"[yellow]Using hardcoded default filter: '{default_filter}'[/yellow]")
            return default_filter, default_project_id # Fallback to hardcoded default

    try:
        with open(filter_file_path, "r") as json_file:
            filters = json.load(json_file)
        if not isinstance(filters, list):
            print(f"[red]Error: Expected a list in {filter_file_path}, found {type(filters)}. Using default.[/red]")
            return default_filter, default_project_id

        active_filter_data = None
        for filter_data in filters:
            # Validate structure before accessing keys
            if isinstance(filter_data, dict) and filter_data.get("isActive") == 1: # Use .get for safer access
                 if "filter" in filter_data:
                     active_filter_data = filter_data
                     break # Found the first active filter
                 else:
                     print(f"[yellow]Warning: Active filter found without 'filter' key in {filter_file_path}: {filter_data}[/yellow]")

        if active_filter_data:
            # Use .get with default values for safer access
            return active_filter_data.get("filter", default_filter), active_filter_data.get("project_id") # Return None if project_id missing
        else:
            print(f"[yellow]No active filter found in {filter_file_path}. Using default: '{default_filter}'[/yellow]")
            # Optionally, prompt user or automatically set the first filter as active
            return default_filter, default_project_id # Fallback to default

    except json.JSONDecodeError:
        print(f"[red]Error reading JSON from {filter_file_path}. Using default.[/red]")
        return default_filter, default_project_id
    except IOError as e:
        print(f"[red]Error accessing filter file {filter_file_path}: {e}. Using default.[/red]")
        return default_filter, default_project_id
    except Exception as e:
        print(f"[red]An unexpected error occurred reading filters: {e}. Using default.[/red]")
        # Log stack trace if needed
        # import traceback
        # traceback.print_exc()
        return default_filter, default_project_id

def read_long_term_tasks(filename="j_long_term_tasks.json"): # Default filename added
    # Renamed from j_long_term_tasks.json if that's the convention
    if not os.path.exists(filename):
        print(f"[yellow]Long term tasks file '{filename}' not found. Creating empty file.[/yellow]")
        try:
            with open(filename, "w") as file:
                json.dump([], file, indent=2)
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


def complete_todoist_task_by_id(api, task_id, skip_logging=False):
    """Completes a Todoist task by its ID with timeout and error handling."""
    # Timeout logic using signal (Unix specific)
    # Consider threading.Timer for cross-platform timeout if needed
    if hasattr(signal, 'SIGALRM'): # Check if SIGALRM is available
        def handler(signum, frame):
            # Use a more specific exception if possible
            raise TimeoutError(f"Todoist API call timed out after 30 seconds for task ID {task_id}")
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(30) # 30 second timeout
    else:
        print("[yellow]Warning: signal.SIGALRM not available on this platform. Cannot enforce timeout.[/yellow]")

    try:
        task = api.get_task(task_id) # Fetch task details first
        if not task:
            print(f"[yellow]No task found with ID: {task_id}[/yellow]")
            return False # Task doesn't exist

        task_name = task.content # Get name before closing

        # Close the task
        success = api.close_task(task_id=task_id)

        if success:
            if not skip_logging:
                log_completed_task(task_name) # Log using the fetched name
            status = 'SKIPPED' if skip_logging else 'COMPLETED'
            print(f"[yellow]{task_name}[/yellow] -- {status}")
            return True
        else:
            # This case might indicate an API issue where close_task returns False/None
            print(f"[red]Todoist API indicated failure to close task ID: {task_id}. Please check Todoist.[/red]")
            return False

    except TimeoutError as te:
        print(f"[red]Error: {te}[/red]")
        return False
    except Exception as error:
        # Catch specific API errors if possible, otherwise log generic error
        print(f"[red]Error completing task ID {task_id}: {error}[/red]")
        # Log stack trace for unexpected errors
        # import traceback
        # traceback.print_exc()
        return False
    finally:
        # Always disable the alarm
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)


def complete_active_todoist_task(api, skip_logging=False):
    """Completes the active Todoist task with retries and timeout."""
    active_task_file = "j_active_task.json"
    max_retries = 3
    retry_delay = 1  # seconds

    # Timeout logic (Unix specific)
    if hasattr(signal, 'SIGALRM'):
        def handler(signum, frame):
            raise TimeoutError("Todoist API call timed out after 5 seconds for active task")
    else:
        print("[yellow]Warning: signal.SIGALRM not available. Cannot enforce timeout per attempt.[/yellow]")


    # 1. Read Active Task File (Outside Retry Loop)
    try:
        with open(active_task_file, "r") as infile:
            active_task = json.load(infile)
        # Validate required keys
        task_id = active_task.get("task_id")
        task_name = active_task.get("task_name")
        if not task_id or not task_name:
             print(f"[red]Error: 'task_id' or 'task_name' missing in {active_task_file}.[/red]")
             return False
    except FileNotFoundError:
        print(f"[red]Error: Active task file '{active_task_file}' not found.[/red]")
        return False
    except json.JSONDecodeError:
        print(f"[red]Error: Could not decode JSON from {active_task_file}.[/red]")
        return False
    except Exception as e:
        print(f"[red]Error reading active task file {active_task_file}: {e}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()
        return False

    # 2. API Interaction Loop (With Retries)
    for attempt in range(max_retries):
        try:
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(5)  # 5-second timeout for this attempt

            # Verify task exists before trying to close (optional but good practice)
            task = api.get_task(task_id)
            if not task:
                print(f"[yellow]Active task (ID: {task_id}, Name: '{task_name}') no longer exists in Todoist.[/yellow]")
                # Consider clearing the active task file here
                if hasattr(signal, 'SIGALRM'): signal.alarm(0)
                return False # Task gone, no point retrying

            # Attempt to close the task
            success = api.close_task(task_id=task_id)

            if hasattr(signal, 'SIGALRM'): signal.alarm(0) # Disable alarm immediately after successful call

            if success:
                if not skip_logging:
                    log_completed_task(task_name)
                    update_completed_tasks_count() # Only update count if logged
                status = 'SKIPPED' if skip_logging else 'COMPLETED'
                print(f"[yellow]{task_name}[/yellow] -- {status}")
                return True # Success! Exit the function.
            else:
                # Handle cases where close_task might return False/None
                 print(f"[yellow]Attempt {attempt + 1}: Todoist API indicated failure closing task ID {task_id}. Retrying...[/yellow]")
                 # Continue to retry logic

        except TimeoutError as te:
             if hasattr(signal, 'SIGALRM'): signal.alarm(0)
             print(f"[yellow]Attempt {attempt + 1}: API call timed out. {te}. Retrying...[/yellow]")
        except Exception as error:
            if hasattr(signal, 'SIGALRM'): signal.alarm(0)
            print(f"[red]Attempt {attempt + 1}: Error completing task ID {task_id}: {error}[/red]")
            # Log stack trace for unexpected errors
            # import traceback
            # traceback.print_exc()
            # Consider breaking loop on certain non-recoverable errors

        # Wait before retrying (if not the last attempt)
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    # If loop finishes without returning True, all retries failed
    print(f"[red]Failed to complete active task '{task_name}' (ID: {task_id}) after {max_retries} attempts.[/red]")
    return False


def update_completed_tasks_count():
    completed_tasks_file = "j_number_of_todays_completed_tasks.json"
    today_str = datetime.date.today().isoformat()
    default_data = {"total_today": 1, "todays_date": today_str}

    try:
        # Try reading first
        try:
            with open(completed_tasks_file, "r") as file:
                data = json.load(file)
            # Basic validation
            if not isinstance(data, dict) or "todays_date" not in data or "total_today" not in data:
                print(f"[yellow]Warning: Invalid data found in {completed_tasks_file}. Resetting.[/yellow]")
                data = default_data
            elif data.get("todays_date") == today_str:
                # Ensure total_today is an int before incrementing
                data["total_today"] = int(data.get("total_today", 0)) + 1
            else:
                # Reset for the new day
                data = default_data
        except (FileNotFoundError, json.JSONDecodeError):
            # If file not found or corrupt, initialize with default
            print(f"[yellow]'{completed_tasks_file}' not found or invalid. Initializing count.[/yellow]")
            data = default_data

        # Write the updated data back
        with open(completed_tasks_file, "w") as file:
            json.dump(data, file, indent=2)

    except IOError as e:
        print(f"[red]Error accessing task count file {completed_tasks_file}: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred updating task count: {e}[/red]")
        # Log stack trace if needed
        # import traceback
        # traceback.print_exc()


def postpone_due_date(api, user_message):
    active_task_file = "j_active_task.json"
    try:
        # 1. Read Active Task
        try:
            with open(active_task_file, "r") as infile:
                active_task = json.load(infile)
            task_id = active_task.get("task_id")
            content = active_task.get("task_name") # Original content from file
            if not task_id or not content:
                 print(f"[red]Error: 'task_id' or 'task_name' missing in {active_task_file}.[/red]")
                 return
        except FileNotFoundError:
            print(f"[red]Error: Active task file '{active_task_file}' not found.[/red]")
            return
        except json.JSONDecodeError:
            print(f"[red]Error: Could not decode JSON from {active_task_file}.[/red]")
            return

        # 2. Extract Due String
        due_string = user_message.replace("postpone ", "", 1).strip()
        if not due_string:
            print("[yellow]No postpone date/time provided. Usage: postpone <due_string>[/yellow]")
            return
        # Basic validation (can be enhanced)
        if due_string.isdigit() and len(due_string) == 4:
            print("[red]Invalid time format for postpone. Use formats like 'tomorrow 9am', 'next week', etc.[/red]")
            return

        # 3. Get Full Task Details from API
        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]Task ID {task_id} (from {active_task_file}) not found in Todoist.[/yellow]")
            # Consider clearing the active task file here
            return

        # 4. Handle Recurring vs. Non-Recurring
        is_recurring = task.due and task.due.is_recurring

        if is_recurring:
            # Close original, create new
            print(f"[cyan]Postponing recurring task '{task.content}' by creating a new instance.[/cyan]")
            close_success = api.close_task(task_id=task.id)
            if not close_success:
                 print(f"[yellow]Warning: Failed to close original recurring task ID {task.id}. Creating new task anyway.[/yellow]")

            new_task_args = {
                "content": task.content, # Use content from fetched task, not potentially stale file content
                "due_string": due_string,
                "description": task.description,
                "priority": task.priority, # Preserve priority
                # Add other relevant fields like labels if needed
                # "labels": task.labels
            }
            if hasattr(task, "project_id") and task.project_id:
                new_task_args["project_id"] = task.project_id

            new_task = api.add_task(**new_task_args)
            if new_task:
                print(f"[green]Recurring task '{task.content}' effectively postponed to '{due_string}'. New task ID: {new_task.id}[/green]")
                # Update active task file to the new task? Depends on desired behavior.
                # add_to_active_task_file(new_task.content, new_task.id, new_task.due.datetime if new_task.due else None)
            else:
                print(f"[red]Error: Failed to create new task instance for recurring task '{task.content}'.[/red]")
        else:
            # Update existing task
            print(f"[cyan]Postponing non-recurring task '{task.content}' to '{due_string}'.[/cyan]")
            updated_task = api.update_task(
                task_id=task.id,
                due_string=due_string
                # description=task.description # description is preserved by default if not provided
            )
            if updated_task:
                print(f"[green]Task '{task.content}' postponed successfully to '{due_string}'.[/green]")
                # Update the active task file with potentially new due date info
                add_to_active_task_file(task.content, task.id, updated_task.due.datetime if updated_task.due else None)
            else:
                print(f"[red]Error: Failed to update task '{task.content}' due date via API.[/red]")

    except Exception as error:
        print(f"[red]An unexpected error occurred during postpone: {error}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()


def get_active_task():
    """Reads and returns the active task data from the JSON file."""
    active_task_file = "j_active_task.json"
    try:
        with open(active_task_file, "r") as infile:
            active_task = json.load(infile)
        # Basic validation
        if not isinstance(active_task, dict) or "task_id" not in active_task:
            print(f"[yellow]Warning: Invalid or missing data in {active_task_file}.[/yellow]")
            return None
        return active_task
    except FileNotFoundError:
        # It's okay if the file doesn't exist initially
        return None
    except json.JSONDecodeError:
        print(f"[red]Error decoding JSON from {active_task_file}.[/red]")
        return None
    except IOError as e:
        print(f"[red]Error reading active task file {active_task_file}: {e}[/red]")
        return None
    except Exception as e:
        print(f"[red]Unexpected error getting active task: {e}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()
        return None


def verify_device_id_before_command():
    """Checks if the active task was last updated on the current device."""
    active_task = get_active_task() # Reuse the getter function

    if not active_task:
        # get_active_task handles logging if file is missing/invalid
        # print("[yellow]No active task found to verify device ID.[/yellow]")
        return True # Allow command if no active task is set

    try:
        current_device_id = get_device_id()
        task_device_id = active_task.get("device_id")
        last_updated_str = active_task.get("last_updated", "Unknown time")
        task_name = active_task.get("task_name", "Unknown task")

        if task_device_id and task_device_id != current_device_id:
            print("[bold red]Warning: Active task mismatch![/bold red]")
            print(f"  Task: '{task_name}'")
            print(f"  Last updated on a different device ({last_updated_str}).")
            print("[yellow]Recommendation:[/yellow] Refresh tasks or set a new active task on *this* device before proceeding.")
            # Ask for confirmation?
            # confirm = input("Continue anyway? (y/N): ").lower()
            # return confirm == 'y'
            return False # Default to blocking the command
        else:
            # Device ID matches or task has no device ID (allow)
            return True

    except Exception as e:
        print(f"[red]Error verifying device ID: {e}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()
        return False # Safer to block command on error

# This function seems redundant if api.update_task is used directly elsewhere.
# Kept for now as it's called by check_and_update_task_due_date.
# Consider replacing calls to this with direct api.update_task calls if appropriate.
def update_task_due_date(api, task_id, due_string):
    """Updates the due date of a specific task."""
    try:
        # Optional: Fetch task first to ensure it exists?
        # task = api.get_task(task_id)
        # if not task:
        #     print(f"[yellow]Task {task_id} not found. Cannot update due date.[/yellow]")
        #     return False

        updated_task = api.update_task(task_id=task_id, due_string=due_string)
        if updated_task:
             print(f"Task ID {task_id} due date updated to '{due_string}'.")
             return True
        else:
             print(f"[red]Failed to update due date for task ID {task_id} via API.[/red]")
             return False
    except Exception as e:
        print(f"[red]Error updating due date for task ID {task_id}: {e}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()
        return False


def get_full_task_details(api, task_id):
    """Fetches the full details of a task by its ID."""
    try:
        task = api.get_task(task_id)
        if not task:
            # Don't print error here, let the caller handle None return
            # print(f"[yellow]Task with ID {task_id} not found.[/yellow]")
            return None
        return task
    except Exception as e:
        print(f"[red]Error fetching full details for task ID {task_id}: {e}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()
        return None


def check_and_update_task_due_date(api, user_message):
    """Checks the active task and updates its due date based on user message."""
    try:
        # 1. Get Active Task
        active_task = get_active_task()
        if not active_task:
            print("[red]No active task set. Cannot update due date.[/red]")
            return False # Indicate failure

        task_id = active_task.get("task_id")
        if not task_id:
             print(f"[red]Error: 'task_id' missing in active task file.[/red]")
             return False

        # 2. Extract Due String
        due_string = user_message.replace("time ", "", 1).strip()
        if not due_string:
            print("[yellow]No due date/time provided. Usage: time <due_string>[/yellow]")
            return False
        if due_string.isdigit() and len(due_string) == 4:
            print("[red]Invalid time format. Use formats like '9am', 'tomorrow 14:00', etc.[/red]")
            return False

        # 3. Get Original Task Details (for comparison and checks)
        original_task = get_full_task_details(api, task_id)
        if not original_task:
            print(f"[yellow]Active task ID {task_id} not found in Todoist.[/yellow]")
            # Consider clearing active task file
            return False

        print("\n[cyan]Original task state:[/cyan]")
        print(f"  Content: {original_task.content}")
        print(f"  Due: {original_task.due.string if original_task.due else 'None'}")
        print(f"  Recurring: {original_task.due.is_recurring if original_task.due else 'No'}")
        print(f"  Description: {'Yes' if original_task.description else 'No'}")

        # 4. Handle Recurring Task Confirmation
        is_recurring = original_task.due and original_task.due.is_recurring
        if is_recurring:
            # Use a more robust input method if possible
            response = input(f"Task '{original_task.content}' is recurring. Modifying its date might break recurrence. Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled by user.")
                return False # Indicate cancellation/failure

        # 5. Attempt Update
        print(f"\n[cyan]Attempting to update task '{original_task.content}' to due: '{due_string}'[/cyan]")
        try:
            # Update the task - description is preserved by default
            updated_task = api.update_task(
                task_id=task_id,
                due_string=due_string
            )

            if not updated_task:
                 # API call itself might have failed without raising exception
                 print("[red]API call to update task did not return updated task details. Update might have failed.[/red]")
                 return False

            # 6. Verification (Optional but recommended)
            print("[cyan]Verifying update...[/cyan]")
            time.sleep(1) # Short delay for API consistency
            verification_task = api.get_task(task_id)

            if verification_task and verification_task.due and verification_task.due.string:
                # Compare due string (may not be exact match due to API parsing, e.g., 'today' -> date)
                print(f"[green]Task due date successfully updated. Verified due: '{verification_task.due.string}'[/green]")
                 # Update active task file with new due info
                add_to_active_task_file(verification_task.content, verification_task.id, verification_task.due.datetime if verification_task.due else None)
                return True # Indicate success
            else:
                # Verification failed
                if is_recurring:
                    # Updates to recurring tasks might sometimes be hard to verify immediately via due string
                    print(f"[yellow]Recurring task update initiated. Verification inconclusive, please check Todoist manually.[/yellow]")
                    # Assume success for recurring tasks if API didn't error out
                    # Update active task file optimistically
                    add_to_active_task_file(original_task.content, task_id, None) # Due date uncertain after update
                    return True
                else:
                    print("[red]Failed to verify task update. Please check Todoist.[/red]")
                    return False # Indicate failure

        except Exception as api_error:
            print(f"[red]Error during Todoist API update call: {api_error}[/red]")
            # Log stack trace
            # import traceback
            # traceback.print_exc()
            return False # Indicate failure

    except Exception as error:
        print(f"[red]An unexpected error occurred checking/updating task due date: {error}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()
        return False # Indicate failure


def delete_todoist_task(api):
    """Deletes the active Todoist task."""
    active_task_file = "j_active_task.json"
    try:
        # 1. Read Active Task
        try:
            with open(active_task_file, "r") as infile:
                active_task = json.load(infile)
            task_id = active_task.get("task_id")
            task_name = active_task.get("task_name", "Unknown task") # Get name for logging
            if not task_id:
                 print(f"[red]Error: 'task_id' missing in {active_task_file}. Cannot delete.[/red]")
                 return False
        except FileNotFoundError:
            print(f"[red]Error: Active task file '{active_task_file}' not found. Cannot delete.[/red]")
            return False
        except json.JSONDecodeError:
            print(f"[red]Error: Could not decode JSON from {active_task_file}. Cannot delete.[/red]")
            return False

        # 2. Verify Task Exists (Optional but good practice)
        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]Task ID {task_id} ('{task_name}') not found in Todoist. Already deleted?[/yellow]")
            # Clean up the active task file as it's stale
            try:
                os.remove(active_task_file)
                print(f"[cyan]Removed stale active task file: {active_task_file}[/cyan]")
            except OSError as e:
                print(f"[red]Error removing stale active task file {active_task_file}: {e}[/red]")
            return True # Consider it success if already gone

        # 3. Delete Task
        success = api.delete_task(task_id=task_id)

        if success:
            print()
            print(f"[bright_red]'{task_name}' (ID: {task_id}) deleted.[/bright_red]")
            print()
             # Clean up the active task file
            try:
                os.remove(active_task_file)
                # print(f"[cyan]Removed active task file: {active_task_file}[/cyan]")
            except OSError as e:
                print(f"[red]Error removing active task file {active_task_file} after deletion: {e}[/red]")
            return True
        else:
            print(f"[red]Failed to delete task '{task_name}' (ID: {task_id}) via API. Please check Todoist.[/red]")
            return False

    except Exception as error:
        print(f"[red]An unexpected error occurred deleting task: {error}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()
        return False

def format_due_time(due_time_str, timezone):
    """Formats a due date/time string into a user-friendly format in the specified timezone."""
    if due_time_str is None:
        return ""
    try:
        # Parse the timestamp string
        due_time = dateutil.parser.parse(due_time_str)

        # Convert to the target timezone
        # Ensure timezone object is valid (pytz object expected here)
        if not isinstance(timezone, datetime.tzinfo):
             print(f"[red]Error: Invalid timezone object provided to format_due_time: {type(timezone)}[/red]")
             # Fallback to UTC or local system time? For now, return raw string
             return due_time_str

        localized_due_time = due_time.astimezone(timezone)

        # Format it (adjust format string as needed)
        friendly_due_time = localized_due_time.strftime("%Y-%m-%d %H:%M")
        return friendly_due_time
    except (ValueError, TypeError) as e:
        # Handle parsing errors or invalid input
        print(f"[yellow]Warning: Could not parse or format due time '{due_time_str}': {e}[/yellow]")
        return due_time_str # Return original string as fallback
    except Exception as e:
        print(f"[red]Unexpected error formatting due time '{due_time_str}': {e}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()
        return due_time_str # Fallback

def print_completed_tasks_count():
    """Reads and prints the number of tasks completed today from the JSON file."""
    completed_tasks_file = "j_number_of_todays_completed_tasks.json"
    today_str = datetime.date.today().isoformat()

    try:
        with open(completed_tasks_file, "r") as file:
            data = json.load(file)

        # Validate data structure and date
        if isinstance(data, dict) and data.get("todays_date") == today_str:
            count = data.get("total_today", 0)
            print(f"Tasks completed today: {count}")
        else:
            # Data is for a previous day or invalid
            print("Tasks completed today: 0") # Assume 0 if date mismatch or invalid

    except FileNotFoundError:
        print("Tasks completed today: 0") # Assume 0 if file doesn't exist
    except json.JSONDecodeError:
        print("[red]Error reading task count file. Count may be inaccurate.[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred reading task count: {e}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()


def log_completed_task(task_name):
    """Logs a completed task with timestamp and unique ID to a JSON file, purging old entries."""
    completed_tasks_file = "j_todays_completed_tasks.json"
    purge_days = 30 # Keep tasks for 30 days
    now = datetime.datetime.now() # Use timezone-aware if possible: datetime.now(datetime.timezone.utc)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    cutoff_date = now.date() - timedelta(days=purge_days)

    try:
        # Read existing tasks
        try:
            with open(completed_tasks_file, "r") as file:
                completed_tasks = json.load(file)
            if not isinstance(completed_tasks, list):
                 print(f"[yellow]Warning: Invalid data in {completed_tasks_file}. Resetting.[/yellow]")
                 completed_tasks = []
        except (FileNotFoundError, json.JSONDecodeError):
            completed_tasks = []

        # Purge old tasks
        original_count = len(completed_tasks)
        # Safer date parsing within list comprehension
        def parse_task_date(task):
            try:
                # Ensure 'datetime' key exists and is a string
                dt_str = task.get('datetime')
                if isinstance(dt_str, str):
                    return parse(dt_str).date()
            except (ValueError, TypeError, KeyError):
                # Handle tasks with missing/invalid datetime
                print(f"[yellow]Warning: Skipping task with invalid/missing datetime during purge: {task.get('task_name', 'N/A')}[/yellow]")
            return None # Return None for invalid dates

        purged_tasks = [
            task for task in completed_tasks
            if (task_date := parse_task_date(task)) and task_date > cutoff_date
        ]
        purged_count = original_count - len(purged_tasks)
        if purged_count > 0:
            print(f"[cyan]Purged {purged_count} completed tasks older than {purge_days} days.[/cyan]")

        # Find the next available ID (more robustly)
        existing_ids = set(task.get('id', 0) for task in purged_tasks if isinstance(task.get('id'), int))
        new_id = 1
        while new_id in existing_ids:
            new_id += 1

        # Add the new task
        purged_tasks.append({
            "id": new_id,
            "datetime": now_str,
            "task_name": task_name
        })

        # Save the updated list
        with open(completed_tasks_file, "w") as file:
            json.dump(purged_tasks, file, indent=2)

    except IOError as e:
        print(f"[red]Error accessing completed tasks file {completed_tasks_file}: {e}[/red]")
    except Exception as e:
        print(f"[red]An unexpected error occurred logging completed task: {e}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()


def update_recurrence_patterns(api):
    """
    Updates recurring long tasks using 'every ' to 'every! ' for consistent scheduling.
    Logs actions and errors clearly.
    """
    print("[cyan]Checking long-term task recurrence patterns...[/cyan]")
    updated_count = 0
    error_count = 0
    try:
        # Import locally to prevent potential circular dependencies at module level
        import helper_todoist_long

        project_id = helper_todoist_long.get_long_term_project_id(api)
        if not project_id:
            # Message already printed by get_long_term_project_id
            return # Cannot proceed without project ID

        tasks = api.get_tasks(project_id=project_id)
        if tasks is None: # Check if API call failed
             print("[yellow]Could not retrieve tasks from 'Long Term Tasks' project.[/yellow]")
             return

        tasks_to_update = []
        for task in tasks:
            # Check if task has due date and due string properties
            if task.due and hasattr(task.due, 'string') and isinstance(task.due.string, str):
                due_string = task.due.string.lower()
                # Ensure it's a recurring task with 'every ' but not 'every!'
                # Also check is_recurring flag for certainty
                if task.due.is_recurring and 'every ' in due_string and 'every!' not in due_string:
                    tasks_to_update.append(task)

        if not tasks_to_update:
            print("[cyan]No long-term tasks found needing recurrence pattern update.[/cyan]")
            return

        print(f"[cyan]Found {len(tasks_to_update)} long-term tasks to potentially update ('every ' -> 'every!').[/cyan]")

        for task in tasks_to_update:
            try:
                current_due_string = task.due.string
                # More robust replacement to avoid partial word matches if needed
                # Use regex if complex patterns arise, but simple replace is likely fine here
                new_due_string = current_due_string.replace('every ', 'every! ')

                if new_due_string == current_due_string:
                     # Should not happen with the checks above, but safety first
                     print(f"[yellow]Skipping task '{task.content}' - due string unchanged after replacement.[/yellow]")
                     continue

                print(f"  Updating task: '{task.content}'")
                print(f"    From due: '{current_due_string}'")
                print(f"    To due:   '{new_due_string}'")

                # Update the task
                update_success = api.update_task(
                    task_id=task.id,
                    due_string=new_due_string
                    # description=task.description # Description preserved by default
                )

                if update_success:
                    print(f"  [green]Successfully updated.[/green]")
                    updated_count += 1
                else:
                    print(f"  [red]API indicated failure updating task ID {task.id}.[/red]")
                    error_count += 1

            except Exception as e:
                print(f"[red]Error updating recurrence for task '{task.content}' (ID: {task.id}): {e}[/red]")
                # Log stack trace for debugging
                # import traceback
                # traceback.print_exc()
                error_count += 1

        print(f"[cyan]Recurrence pattern check finished. Updated: {updated_count}, Errors: {error_count}[/cyan]")

    except Exception as e:
        print(f"[red]An unexpected error occurred during the recurrence pattern update process: {e}[/red]")
        # Log stack trace
        # import traceback
        # traceback.print_exc()


# Apply call counter decorator to all functions defined in this module
module_call_counter.apply_call_counter_to_all(globals(), __name__)