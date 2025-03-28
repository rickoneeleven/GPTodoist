import json, dateutil.parser, datetime, sys, os, signal, pyfiglet, time, uuid
import hashlib, platform
import module_call_counter
from dateutil.parser import parse
from datetime import timedelta
from rich import print

def print_beast_mode_complete():
    ascii_banner = pyfiglet.figlet_format("BEAST MODE COMPLETE")
    print(ascii_banner)

def change_active_task():
    with open("j_todoist_filters.json", "r") as file:
        task_data = json.load(file)
    for task in task_data:
        task["isActive"] = 1 if task["isActive"] == 0 else 0
    with open("j_todoist_filters.json", "w") as file:
        json.dump(task_data, file)

def add_to_active_task_file(task_name, task_id, task_due):
    active_task = {
        "task_name": task_name,
        "task_id": task_id,
        "task_due": task_due,
        "device_id": get_device_id(),
        "last_updated": datetime.datetime.now().isoformat()
    }
    with open("j_active_task.json", "w") as outfile:
        json.dump(active_task, outfile, indent=2)

def get_device_id():
    # Collect system-specific information
    system_info = [
        platform.node(),  # Network name of the machine
        platform.machine(),  # Machine type (e.g., 'x86_64')
        platform.processor(),  # Processor type
        str(uuid.getnode()),  # MAC address as a 48-bit integer
    ]
    
    # Create a unique string from the system information
    unique_string = ':'.join(system_info)
    
    # Generate a hash of the unique string
    device_id = hashlib.md5(unique_string.encode()).hexdigest()
    
    return device_id

def get_active_filter():
    filter_file_path = "j_todoist_filters.json"
    if not os.path.exists(filter_file_path):
        with open(filter_file_path, "w") as json_file:
            mock_data = [
                {
                    "id": 1,
                    "filter": "(no due date | today | overdue) & !#Team Virtue",
                    "isActive": 1,
                    "project_id": "",
                }
            ]
            json.dump(mock_data, json_file, indent=2)
    with open(filter_file_path, "r") as json_file:
        filters = json.load(json_file)
        for filter_data in filters:
            if filter_data["isActive"]:
                return filter_data["filter"], filter_data.get("project_id", None)

def read_long_term_tasks(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as file:
            json.dump([], file, indent=2)
    with open(filename, "r") as file:
        tasks = json.load(file)
    return tasks

def complete_todoist_task_by_id(api, task_id):
    def handler(signum, frame):
        raise Exception("end of time")
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(30)
    try:
        task = api.get_task(task_id)
        task_name = task.content
        if task:
            api.close_task(task_id=task_id)
            log_completed_task(task_name)
            print(f"[yellow]{task_name} [/yellow] -- COMPLETED")
        else:
            print("No task was found with the given id.")
            return False
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return False
    finally:
        signal.alarm(0)
    return True

def complete_active_todoist_task(api, skip_logging=False):
    def handler(signum, frame):
        raise Exception("end of time")

    signal.signal(signal.SIGALRM, handler)

    max_retries = 3
    retry_delay = 1  # seconds

    for retry in range(max_retries):
        try:
            signal.alarm(5)  # 5-second timeout

            with open("j_active_task.json", "r") as infile:
                active_task = json.load(infile)
                task_id = active_task["task_id"]
                task_name = active_task["task_name"]

            task = api.get_task(task_id)
            if task:
                api.close_task(task_id=task_id)
                if not skip_logging:
                    log_completed_task(task_name)
                    # Update completed tasks count
                    update_completed_tasks_count()
                print(f"[yellow]{task_name}[/yellow] {'-- SKIPPED' if skip_logging else '-- COMPLETED'}")
                
                signal.alarm(0)
                return True
            else:
                print("No task was found with the given id.")
                signal.alarm(0)
                return False

        except FileNotFoundError:
            print("Active task file not found.")
            signal.alarm(0)
            return False
        except KeyError:
            print("Task ID not found in the active task file.")
            signal.alarm(0)
            return False
        except Exception as error:
            signal.alarm(0)
            print(f"Attempt {retry + 1}: Failed to complete task. Error: {error}")
            if retry < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("[red]Failed to complete task after all retries.[/red]")
                return False

    return False

def update_completed_tasks_count():
    completed_tasks_file = "j_number_of_todays_completed_tasks.json"
    today_str = datetime.date.today().isoformat()
    
    try:
        with open(completed_tasks_file, "r+") as file:
            data = json.load(file)
            if data["todays_date"] == today_str:
                data["total_today"] += 1
            else:
                data["total_today"] = 1
                data["todays_date"] = today_str
            file.seek(0)
            file.truncate()
            json.dump(data, file, indent=2)
    except FileNotFoundError:
        with open(completed_tasks_file, "w") as outfile:
            json.dump({"total_today": 1, "todays_date": today_str}, outfile, indent=2)
    except json.JSONDecodeError:
        print("Error reading the task count file. Resetting count.")
        with open(completed_tasks_file, "w") as outfile:
            json.dump({"total_today": 1, "todays_date": today_str}, outfile, indent=2)

def postpone_due_date(api, user_message):
    try:
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
            content = active_task["task_name"]
        task = api.get_task(task_id)
        if task:
            due_string = user_message.replace("postpone ", "", 1)
            if due_string.isdigit() and len(due_string) == 4:
                print("[red]bad time format[/red]")
                return
            if due_string:
                if task.due and task.due.is_recurring:
                    api.close_task(task_id=task_id)
                    new_task_args = {
                        "content": content,
                        "due_string": due_string,
                        "description": task.description
                    }
                    if hasattr(task, "project_id") and task.project_id:
                        new_task_args["project_id"] = task.project_id
                    new_task = api.add_task(**new_task_args)
                    if new_task:
                        print(f"Recurring task postponed to '{due_string}' and description preserved.")
                    else:
                        print("Failed to create new recurring task.")
                else:
                    updated_task = api.update_task(
                        task_id=task.id,
                        due_string=due_string,
                        description=task.description
                    )
                    if updated_task:
                        print(f"Task postponed to '{due_string}' and description preserved.")
                    else:
                        print("Failed to update task.")
            else:
                print("No due date provided.")
        else:
            print(f"Task {task_id} not found.")
    except FileNotFoundError:
        print("Active task file not found.")
    except KeyError:
        print("Task ID not found in the active task file.")
    except Exception as error:
        print(f"Error updating active task due date: {error}")


def get_active_task():
    try:
        with open("j_active_task.json", "r") as infile:
            return json.load(infile)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def verify_device_id_before_command():
    try:
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
    except (FileNotFoundError, json.JSONDecodeError):
        print("[red]No active task found. Please set an active task first.[/red]")
        return False

    current_device_id = get_device_id()
    task_device_id = active_task.get("device_id")
    
    if task_device_id != current_device_id:
        print("[red]Warning: Active task was last updated on another device.[/red]")
        print(f"Last update: {active_task.get('last_updated', 'Unknown')}")
        print("Please refresh the active task on this device before proceeding.")
        print(f"Current active task: {active_task['task_name']}")
        return False
    
    return True

def update_task_due_date(api, task_id, due_string):
    # Existing implementation
    api.update_task(task_id=task_id, due_string=due_string)
    print(f"Due date updated to '{due_string}'.")

# New function to get full task details
def get_full_task_details(api, task_id):
    return api.get_task(task_id)

def check_and_update_task_due_date(api, user_message):
    try:
        active_task = get_active_task()
        if not active_task:
            print("[red]No active task found.[/red]")
            return False

        task_id = active_task["task_id"]
        content = active_task["task_name"]

        # Get full task details and show original state
        original_task = get_full_task_details(api, task_id)
        print("\n[yellow]Debug - Original task state:[/yellow]")
        print(f"Content: {original_task.content}")
        print(f"Due: {original_task.due.string if original_task.due else 'None'}")
        print(f"Is recurring: {original_task.due.is_recurring if original_task.due else 'None'}")
        
        if not original_task:
            print(f"[red]Task {task_id} not found.[/red]")
            return False

        # Check if the task is recurring
        is_recurring = original_task.due.is_recurring if original_task.due else False

        if is_recurring:
            response = input("You are trying to change the time of a recurring task, are you sure? y to continue: ")
            if response.lower() != 'y':
                print("User aborted...")
                return False

        due_string = user_message.replace("time ", "", 1)
        if due_string.isdigit() and len(due_string) == 4:
            print("[red]bad time format[/red]")
            return False
        if not due_string:
            print("No due date provided.")
            return False

        print(f"\n[yellow]Debug - Attempting to update with due_string: '{due_string}'[/yellow]")

        try:
            # Update the task with the new due date and preserve the description
            updated_task = api.update_task(
                task_id=task_id,
                due_string=due_string,
                description=original_task.description
            )

            # Wait a moment for API consistency
            time.sleep(1)

            # Verify the update by fetching the task again
            verification_task = api.get_task(task_id)
            
            if verification_task and verification_task.due and verification_task.due.string:
                print(f"[green]Task due date successfully updated to '{due_string}' and verified.[/green]")
                return True
            else:
                # For recurring tasks, the update might succeed even if we can't verify immediately
                if is_recurring:
                    print(f"[green]Recurring task update initiated. Please verify the change manually.[/green]")
                    return True
                print("[red]Failed to verify task update.[/red]")
                return False

        except AttributeError as ae:
            # Handle the case where 'due' attribute is temporarily missing
            if is_recurring:
                print(f"[green]Recurring task update initiated. Please verify the change manually.[/green]")
                return True
            raise ae  # Re-raise if it's not a recurring task
            
        except Exception as api_error:
            print(f"[red]Error from Todoist API while updating task: {api_error}[/red]")
            print(f"Error type: {type(api_error)}")
            return False

    except FileNotFoundError:
        print("[red]Active task file not found.[/red]")
        return False
    except KeyError as ke:
        print(f"[red]Task ID not found in the active task file. Key: {ke}[/red]")
        return False
    except Exception as error:
        print(f"[red]Error updating active task due date: {error}[/red]")
        print(f"Error type: {type(error)}")
        return False

def delete_todoist_task(api):
    try:
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
            task_name = active_task["task_name"]
        task = api.get_task(task_id)
        if task:
            api.delete_task(task_id=task_id)
            print()
            print(f"[bright_red] {task_name} [/bright_red] - deleted. Next task: ")
            print()
            return True
        else:
            print(f"Task {task_id} not found.")
            return False
    except FileNotFoundError:
        print("Active task file not found.")
    except KeyError:
        print("Task ID not found in the active task file.")
    except Exception as error:
        print(f"Error deleting task: {error}")
        return False

def format_due_time(due_time_str, timezone):
    if due_time_str is None:
        return ""
    due_time = dateutil.parser.parse(due_time_str)
    localized_due_time = due_time.astimezone(timezone)
    friendly_due_time = localized_due_time.strftime("%Y-%m-%d %H:%M")
    return friendly_due_time

def print_completed_tasks_count():
    try:
        with open("j_number_of_todays_completed_tasks.json", "r") as file:
            data = json.load(file)
            print(f"Tasks completed today: {data['total_today']}")
    except FileNotFoundError:
        print("No tasks completed today.")
    except json.JSONDecodeError:
        print("Error reading the task count file.")
    except KeyError:
        print("Error retrieving task count data.")

def log_completed_task(task_name):
    completed_tasks_file = "j_todays_completed_tasks.json"
    today = datetime.date.today()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(completed_tasks_file, "r") as file:
            completed_tasks = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        completed_tasks = []
    
    current_date = datetime.datetime.now().date()
    completed_tasks = [task for task in completed_tasks if parse(task['datetime']).date() > current_date - timedelta(days=30)]
    
    # Find the first available ID
    existing_ids = set(task.get('id', 0) for task in completed_tasks)
    new_id = 1
    while new_id in existing_ids:
        new_id += 1
    
    completed_tasks.append({
        "id": new_id,
        "datetime": now,
        "task_name": task_name
    })
    
    with open(completed_tasks_file, "w") as file:
        json.dump(completed_tasks, file, indent=2)


def update_recurrence_patterns(api):
    """
    Update recurring long tasks that use 'every' to 'every!' in their due string
    to ensure they maintain the original schedule regardless of completion date.
    
    Args:
        api: Todoist API instance
    """
    try:
        # Import here to avoid circular imports
        import helper_todoist_long
        
        # Get the Long Term Tasks project ID
        project_id = helper_todoist_long.get_long_term_project_id(api)
        if not project_id:
            return
        
        # Get all tasks in the Long Term Tasks project
        tasks = api.get_tasks(project_id=project_id)
        
        # Find recurring tasks with 'every' but not 'every!' in due string
        tasks_to_update = []
        for task in tasks:
            if task.due and hasattr(task.due, 'string'):
                due_string = task.due.string.lower()
                # Check if it contains 'every ' but not 'every!'
                if 'every ' in due_string and 'every!' not in due_string:
                    tasks_to_update.append(task)
        
        # Update each task and show a message
        for task in tasks_to_update:
            try:
                # Get the current due string and replace 'every ' with 'every! '
                current_due_string = task.due.string
                new_due_string = current_due_string.replace('every ', 'every! ')
                
                # Update the task
                api.update_task(
                    task_id=task.id,
                    due_string=new_due_string,
                    description=task.description  # Preserve description
                )
                
                # Show a message about the update
                print(f"[cyan]Updated long task recurrence pattern: '{task.content}'[/cyan]")
                print(f"[cyan]Changed from '{current_due_string}' to '{new_due_string}'[/cyan]")
                
            except Exception as e:
                print(f"[yellow]Error updating recurrence pattern for task '{task.content}': {str(e)}[/yellow]")
                
    except Exception as e:
        print(f"[yellow]Error in recurrence pattern update process: {str(e)}[/yellow]")


module_call_counter.apply_call_counter_to_all(globals(), __name__)