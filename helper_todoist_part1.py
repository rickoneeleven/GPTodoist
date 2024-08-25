import json, dateutil.parser, datetime, sys, os, signal, pyfiglet
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
    try:
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
            task_name = active_task["task_name"]
        if complete_todoist_task_by_id(api, task_id):
            completed_tasks_file = "j_number_of_todays_completed_tasks.json"
            today_str = datetime.date.today().isoformat()
            if not os.path.exists(completed_tasks_file):
                with open(completed_tasks_file, "w") as outfile:
                    json.dump({"total_today": 0, "todays_date": today_str}, outfile, indent=2)
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
        else:
            print(f"[red]DO A MANUAL qq, DON'T TRUST NEXT TASK - Error completing task {task_id}.[/red]")
    except FileNotFoundError:
        print("Active task file not found.")
    except KeyError:
        print("Task ID not found in the active task file.")
    except Exception as error:
        print(f"Error completing active task: {error}")

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
                    new_task_args = {"content": content, "due_string": due_string}
                    if hasattr(task, "project_id") and task.project_id:
                        new_task_args["project_id"] = task.project_id
                    new_task = api.add_task(**new_task_args)
                else:
                    api.update_task(task_id=task.id, due_string=due_string)
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

def update_task_due_date(api, user_message):
    try:
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
            content = active_task["task_name"]
        if content.startswith("postponed recurring - (r)"):
            response = input("You are trying to change the time of a recurring task, are you sure? y to continue: ")
            if response.lower() != 'y':
                print("User aborted...")
                return
        task = api.get_task(task_id)
        if not task:
            print(f"Task {task_id} not found.")
            return
        due_string = user_message.replace("time ", "", 1)
        if due_string.isdigit() and len(due_string) == 4:
            print("[red]bad time format[/red]")
            return
        if not due_string:
            print("No due date provided.")
            return
        api.update_task(task_id=task.id, due_string=due_string)
        print(f"Due date updated to '{due_string}'.")
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
    completed_tasks = [task for task in completed_tasks if parse(task['datetime']).date() > current_date - timedelta(days=2)]
    completed_tasks.append({"datetime": now, "task_name": task_name})
    with open(completed_tasks_file, "w") as file:
        json.dump(completed_tasks, file, indent=2)

module_call_counter.apply_call_counter_to_all(globals(), __name__)