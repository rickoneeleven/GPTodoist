import re, json, pytz, dateutil.parser, datetime, time, sys, os, signal
import helper_parse, module_call_counter, helper_general, helper_regex
from dateutil.parser import parse
from datetime import date, timedelta
from pytz import timezone
from rich import print
from requests.exceptions import HTTPError


def change_active_task():
    # Load the JSON data
    with open("j_todoist_filters.json", "r") as file:
        task_data = json.load(file)

    # Iterate through the tasks and switch the active status
    for task in task_data:
        if task["isActive"] == 1:
            task["isActive"] = 0
        else:
            task["isActive"] = 1

    # Save the updated JSON data
    with open("j_todoist_filters.json", "w") as file:
        json.dump(task_data, file)


def handle_special_commands(user_message, assistant_message, api):
    if user_message.lower().startswith("move task") and "Task ID" in assistant_message:
        task_id = helper_regex.extract_task_id_from_response(assistant_message)
        if task_id is not None:
            update_task_due_date(api, user_message, task_id)
            get_next_todoist_task(api)
        else:
            print("Failed to move the task.")


def add_to_active_task_file(task_name, task_id, task_due):
    active_task = {"task_name": task_name, "task_id": task_id, "task_due": task_due}
    with open("j_active_task.json", "w") as outfile:
        json.dump(active_task, outfile)


def add_todoist_task(api, task_name, task_time, task_day):
    try:
        active_filter, project_id = get_active_filter()

        if not active_filter:
            print("No active filters configured. Update j_todoist_filters.json.")
            return None

        task_params = {"content": task_name}

        # Check for priority flags in task_name and set priority
        if 'p1' in task_name.lower():
            task_params['priority'] = 4
        elif 'p2' in task_name.lower():
            task_params['priority'] = 3
        elif 'p3' in task_name.lower():
            task_params['priority'] = 2

        if project_id and project_id.strip():
            task_params["project_id"] = project_id

        task = api.add_task(**task_params)

        # Fetch current date and time
        due_date = datetime.datetime.now()

        # Check if task is for tomorrow
        if task_day == "tomorrow":
            due_date += datetime.timedelta(days=1)

        # If task_time is not provided, set it to current time
        if not task_time:
            task_time = due_date.strftime("%H:%M:%S")

        due_date_str = due_date.strftime("%Y-%m-%d") + "T" + task_time + "Z"

        # Update the task with due_date
        api.update_task(task_id=task.id, due_string=due_date_str)

        return task
    except Exception as error:
        print(f"Error adding task: {error}")
        return None


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



def fetch_todoist_tasks(api):
    def handler(signum, frame):
        raise Exception("end of time")

    signal.signal(signal.SIGALRM, handler)

    active_filter, project_id = get_active_filter()

    if not active_filter:
        print("No active filters configured. Update j_todoist_filters.json.")
        return

    retries = 0
    while retries < 99:
        try:
            signal.alarm(5)
            tasks = api.get_tasks(filter=active_filter)

            london_tz = pytz.timezone("Europe/London")
            all_tasks = []

            # Capture current time in London timezone
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            now_london = now_utc.astimezone(london_tz).isoformat()

            for task in tasks:
                if task.due and task.due.datetime:
                    utc_dt = parse(task.due.datetime)
                    london_dt = utc_dt.astimezone(london_tz)
                    task.due.datetime = london_dt.isoformat()
                else:
                    task.due = type('Due', (object,), {'datetime': now_london})()

                all_tasks.append(task)

            # Sort tasks by priority, due date, then creation date
            sorted_final_tasks = sorted(
                all_tasks,
                key=lambda t: (
                    -t.priority,
                    t.due.datetime if t.due and hasattr(t.due, 'datetime') else now_london,
                    t.created if hasattr(t, 'created') else ''
                )
            )

            signal.alarm(0)
            return sorted_final_tasks

        except Exception as e:
            retries += 1
            print(f"Attempt {retries}: Failed to fetch tasks. Error: {e}")

            if retries == 99:
                print("[red]Failed to fetch tasks after 10 retries. Exiting with 'end of time'[/red]")
                return None

            time.sleep(1)  # Add a 1-second delay before retrying



def complete_todoist_task_by_id(api, task_id):
    def handler(signum, frame):
        raise Exception("end of time")

    signal.signal(signal.SIGALRM, handler)

    for attempt in range(5):  # 5 retries before exception
        try:
            signal.alarm(5)  # set the signal to raise an Exception in 5 seconds

            task = api.get_task(task_id)
            task_name = task.content
            if task:
                api.close_task(task_id=task_id)
                print(f"[yellow]{task_name}[/yellow] completed")
                signal.alarm(0)  # Disable the alarm
                return True
            else:
                print("No task was found with the given id.")
                signal.alarm(0)  # Disable the alarm
                return False

        except Exception as error:
            if attempt < 4:  # Print "retrying to complete task..." only if it's not the last attempt
                print("retrying to complete task...")
            else:
                print(f"Error: {error}", file=sys.stderr)
                return False


def read_long_term_tasks(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as file:
            json.dump([], file, indent=2)

    with open(filename, "r") as file:
        tasks = json.load(file)

    return tasks


def get_next_todoist_task(api):
    try:
        tasks = fetch_todoist_tasks(api)
        long_term_tasks = read_long_term_tasks("j_long_term_tasks.json")

        if tasks:
            next_task = tasks[0]
            task_name = next_task.content
            task_id = next_task.id
            task_due = (
                next_task.due.datetime
                if next_task.due and next_task.due.datetime
                else None
            )

            # Check if the task is recurring and add "(r) " to the task name
            task = api.get_task(task_id)
            is_recurring = False

            if task and task.due:
                is_recurring = task.due.is_recurring

            if is_recurring:
                task_name = "(r) " + task_name

            add_to_active_task_file(task_name, task_id, task_due)

            print(f"                   [green]{task_name}[/green]")
            if task_due:
                task_due_london = helper_general.convert_to_london_timezone(task_due)
                task_due_london_datetime = datetime.datetime.strptime(
                    task_due_london, "%Y-%m-%d %H:%M:%S"
                )
                task_due_time = task_due_london_datetime.strftime("%H:%M")
                task_due_date = task_due_london_datetime.date()

                if task_due_date < date.today():
                    task_due_str = task_due_london_datetime.strftime("%Y-%m-%d %H:%M")
                else:
                    task_due_str = task_due_time

                #print(f"Task Due: {task_due_str}")
            print()

            x_tasks = [
                lt_task
                for lt_task in long_term_tasks
                if lt_task["task_name"].startswith("x ")
            ]

            if x_tasks:
                print("[bright_black]Spare time focus:[/bright_black]")
                for x_task in x_tasks:
                    print(f"[bright_black]{x_task['task_name']}[/bright_black]")
                print()

        else:
            print("\u2705")
            print()

    except Exception as e:
        if "end of time" in str(e):
            print("An end of time exception occurred.")
            return None
        else:
            raise e


def complete_active_todoist_task(api):
    try:
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
            task_name = active_task["task_name"]

            if complete_todoist_task_by_id(api, task_id):
                #print()
                #print(f"[bright_red] {task_name} [/bright_red] complete")
                print()
            else:
                print(f"Error completing task {task_id}.")
    except FileNotFoundError:
        print("Active task file not found.")
    except KeyError:
        print("Task ID not found in the active task file.")
    except Exception as error:
        print(f"Error completing active task: {error}")


def parse_update_due_date_command(user_message):
    parts = user_message.lower().split()
    if len(parts) < 2 or parts[0] != "time":
        return None
    task_time, task_day = None, None
    for part in parts[1:]:
        if re.match(r"\d{4}", part):
            task_time = part
        elif part in ["today", "tomorrow"]:
            task_day = part
    return task_time, task_day


def update_task_due_date(api, user_message, task_id=False):
    print(user_message)
    try:
        with open("j_active_task.json", "r") as infile:
            if not task_id:
                task_time, task_day = parse_update_due_date_command(user_message)
                print("loading j_active_task.json...")
                active_task = json.load(infile)
                task_id = active_task["task_id"]
                content = active_task["task_name"]
            else:
                (
                    content,
                    task_time,
                    task_day,
                ) = helper_parse.get_taskname_time_day_as_tuple(user_message)

                if task_time is None:
                    print("Invalid command belly")
                    return

            task = api.get_task(task_id)
            if task:
                if task.due is not None:
                    is_recurring = task.due.is_recurring
                else:
                    is_recurring = False

                due_date = datetime.datetime.now()
                if task_day == "tomorrow":
                    due_date += datetime.timedelta(days=1)
                due_date = due_date.strftime("%Y-%m-%d") + " " + task_time

                if is_recurring:
                    api.close_task(task_id=task_id)  # Complete the recurring task
                    # Check for a project ID and include it if present
                    new_task_args = {"content": content, "due_string": due_date}
                    if hasattr(task, "project_id") and task.project_id:
                        new_task_args["project_id"] = task.project_id
                    api.add_task(
                        **new_task_args
                    )  # Create a new task with the new due date
                    print(
                        "Task was a recurring task, so I've completed it for today, and created you a static task with your desired due time."
                    )
                else:
                    api.update_task(task_id=task.id, due_string=due_date)

                    print()
                    print("Due date updated, your next task is: ")
                    print()
            else:
                print(f"Task {task_id} not found.")
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


def display_todoist_tasks(api):
    tasks = fetch_todoist_tasks(api)

    london_tz = pytz.timezone("Europe/London")

    if tasks:
        # Add null check and use current datetime if no due date
        max_due_time_length = max(
            len(format_due_time(task.due.datetime if task.due else None, london_tz))
            for task in tasks
        )
        tab_size = 8

        for task in tasks:
            # Add null check and use current datetime if no due date
            due_time_str = task.due.datetime if task.due else None
            due_time = format_due_time(due_time_str, london_tz).ljust(
                max_due_time_length + tab_size
            )
            task_name = task.content
            print(f"{due_time}{task_name}")


def format_due_time(due_time_str, timezone):
    if due_time_str is None:
        return ""
    due_time = dateutil.parser.parse(due_time_str)
    localized_due_time = due_time.astimezone(timezone)
    friendly_due_time = localized_due_time.strftime("%Y-%m-%d %H:%M")
    return friendly_due_time


module_call_counter.apply_call_counter_to_all(globals(), __name__)
