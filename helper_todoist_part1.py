import json, dateutil.parser, datetime, sys, os, signal, pyfiglet, time
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
    active_task = {"task_name": task_name, "task_id": task_id, "task_due": task_due}
    with open("j_active_task.json", "w") as outfile:
        json.dump(active_task, outfile)

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
            print(f"[yellow]{task_name} completed[/yellow]")
        else:
            print("No task was found with the given id.")
            return False
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return False
    finally:
        signal.alarm(0)
    return True

def complete_active_todoist_task(api):
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
                log_completed_task(task_name)
                print(f"[yellow]{task_name} completed[/yellow]")
                
                # Update completed tasks count
                update_completed_tasks_count()
                
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
    with open("j_active_task.json", "r") as infile:
        return json.load(infile)

def update_task_due_date(api, task_id, due_string):
    # Existing implementation
    api.update_task(task_id=task_id, due_string=due_string)
    print(f"Due date updated to '{due_string}'.")

# New function to get full task details
def get_full_task_details(api, task_id):
    return api.get_task(task_id)

# New wrapper function
def check_and_update_task_due_date(api, user_message):
    try:
        active_task = get_active_task()
        task_id = active_task["task_id"]
        content = active_task["task_name"]

        # Get full task details
        task = get_full_task_details(api, task_id)
        
        if not task:
            print(f"Task {task_id} not found.")
            return

        # Check if the task is recurring
        is_recurring = task.due.is_recurring if task.due else False

        if is_recurring:
            response = input("You are trying to change the time of a recurring task, are you sure? y to continue: ")
            if response.lower() != 'y':
                print("User aborted...")
                return

        due_string = user_message.replace("time ", "", 1)
        if due_string.isdigit() and len(due_string) == 4:
            print("[red]bad time format[/red]")
            return
        if not due_string:
            print("No due date provided.")
            return

        # Update the task with the new due date and preserve the description
        updated_task = api.update_task(
            task_id=task.id,
            due_string=due_string,
            description=task.description
        )

        if updated_task:
            print(f"Task due date updated to '{due_string}' and description preserved.")
        else:
            print("Failed to update task.")

    except FileNotFoundError:
        print("Active task file not found.")
    except KeyError:
        print("Task ID not found in the active task file.")
    except Exception as error:
        print(f"Error updating active task due date: {error}")

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

module_call_counter.apply_call_counter_to_all(globals(), __name__)