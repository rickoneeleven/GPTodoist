import re, json, pytz, dateutil.parser, datetime, time, sys, os
import helper_parse, module_call_counter, helper_general, helper_regex
from dateutil.parser import parse
from datetime import date, timedelta
from pytz import timezone
from rich import print
from requests.exceptions import HTTPError


def handle_special_commands(user_message, assistant_message, api):
    if "~~~" in user_message.lower() and "Task ID" in assistant_message:
        task_id = helper_regex.extract_task_id_from_response(assistant_message)
        if task_id is not None:
            task = api.get_task(task_id=task_id)
            if task is not None:
                task_name = task.content
                time_complete = helper_general.get_timestamp()

                if complete_todoist_task_by_id(api, task_id):
                    print(
                        f"[green] Task with ID {task_id} successfully marked as complete. [/green]"
                    )
                    update_todays_completed_tasks(task_name, task_id, time_complete)
                else:
                    print("Failed to complete the task.")
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
        task = api.add_task(task_name)
        if task_time:
            due_date = datetime.datetime.now()
            if task_day == "tomorrow":
                due_date += datetime.timedelta(days=1)
            due_date = due_date.strftime("%Y-%m-%d") + " " + task_time
            api.update_task(task_id=task.id, due_string=due_date)
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
                }
            ]
            json.dump(mock_data, json_file, indent=2)

    with open(filter_file_path, "r") as json_file:
        filters = json.load(json_file)

    active_filter = None
    for filter in filters:
        if filter["isActive"]:
            active_filter = filter["filter"]
            break

    return active_filter


def fetch_todoist_tasks(api):
    retries = 0
    max_retries = 5
    backoff_factor = 2

    active_filter = get_active_filter()

    if not active_filter:
        print(
            "No active filters configured, see j_todoist_filters.json, add your filter and set to active and try again"
        )
        return

    while retries < max_retries:
        try:
            london_tz = pytz.timezone("Europe/London")
            tasks = api.get_tasks(filter=active_filter)

            tasks_with_due_dates = []
            tasks_without_due_dates = []

            for task in tasks:
                if task.due and task.due.datetime:
                    utc_dt = parse(task.due.datetime)
                    london_dt = utc_dt.astimezone(london_tz)
                    task.due.datetime = london_dt.isoformat()
                    tasks_with_due_dates.append(task)
                else:
                    tasks_without_due_dates.append(task)

            sorted_tasks_with_due_dates = sorted(
                tasks_with_due_dates, key=lambda t: t.due.datetime
            )

            # Combine tasks without due dates and tasks with due dates
            sorted_tasks = tasks_without_due_dates + sorted_tasks_with_due_dates

            return sorted_tasks
        except HTTPError as http_error:
            error_msg = f"An HTTP error occurred: {http_error}\nURL: {http_error.response.url}\nStatus code: {http_error.response.status_code}"
            print(error_msg, file=sys.stderr)
            time.sleep(backoff_factor * (2**retries))
            retries += 1
        except Exception as error:
            print(f"An unexpected error occurred: {error}", file=sys.stderr)
            time.sleep(backoff_factor * (2**retries))
            retries += 1

    print("Failed to fetch tasks after multiple retries", file=sys.stderr)
    return None


def complete_todoist_task_by_id(api, task_id):
    retries = 0
    max_retries = 5
    backoff_factor = 2

    while retries < max_retries:
        try:
            task = api.get_task(task_id)
            if task:
                api.close_task(task_id=task_id)
                return True
            else:
                return False
        except HTTPError as http_error:
            error_msg = f"An HTTP error occurred: {http_error}\nURL: {http_error.response.url}\nStatus code: {http_error.response.status_code}"
            print(error_msg, file=sys.stderr)
            time.sleep(backoff_factor * (2**retries))
            retries += 1
        except Exception as error:
            print(f"An unexpected error occurred: {error}", file=sys.stderr)
            time.sleep(backoff_factor * (2**retries))
            retries += 1

    print("Failed to complete task after multiple retries", file=sys.stderr)
    return False


def read_long_term_tasks(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as file:
            json.dump([], file, indent=2)

    with open(filename, "r") as file:
        tasks = json.load(file)

    return tasks


def get_next_todoist_task(api):
    tasks = fetch_todoist_tasks(api)
    long_term_tasks = read_long_term_tasks("j_long_term_tasks.json")

    if tasks:
        next_task = tasks[0]
        task_name = next_task.content
        task_id = next_task.id
        task_due = (
            next_task.due.datetime if next_task.due and next_task.due.datetime else None
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

            print(f"Task Due: {task_due_str}")
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


def complete_active_todoist_task(api):
    try:
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
            task_name = active_task["task_name"]

            if complete_todoist_task_by_id(api, task_id):
                print()
                print(f"[bright_red] {task_name} [/bright_red] complete")
                print()
                london_tz = timezone("Europe/London")
                now = datetime.datetime.now(london_tz)
                time_complete = now.isoformat()
                update_todays_completed_tasks(task_name, task_id, time_complete)

                todays_completed_tasks = get_todays_completed_tasks()

                yesterday = date.today() - timedelta(days=1)
                yesterday_tasks = [
                    task
                    for task in todays_completed_tasks
                    if date.fromisoformat(task["time_complete"][:10]) == yesterday
                ]

                if yesterday_tasks:
                    print(
                        "Fantastic day yesterday, here are all the tasks you completed, go you!"
                    )
                    for task in yesterday_tasks:
                        print(
                            f"Task: {task['task_name']}, Completed Time: {task['time_complete']}"
                        )

                    todays_completed_tasks = [
                        task
                        for task in todays_completed_tasks
                        if date.fromisoformat(task["time_complete"][:10]) != yesterday
                    ]
                    with open("j_todays_completed_tasks.json", "w") as outfile:
                        json.dump(todays_completed_tasks, outfile, indent=2)

            else:
                print(f"Error completing task {task_id}.")
    except FileNotFoundError:
        print("Active task file not found.")
    except KeyError:
        print("Task ID not found in the active task file.")
    except Exception as error:
        print(f"Error completing active task: {error}")


def update_todays_completed_tasks(task_name, task_id, time_complete):
    completed_tasks = get_todays_completed_tasks()
    completed_tasks.append(
        {"task_name": task_name, "task_id": task_id, "time_complete": time_complete}
    )
    with open("j_todays_completed_tasks.json", "w") as outfile:
        json.dump(completed_tasks, outfile, indent=2)


def get_todays_completed_tasks():
    try:
        with open("j_todays_completed_tasks.json", "r") as infile:
            return json.load(infile)
    except FileNotFoundError:
        return []


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
                task_name = active_task["task_name"]
            else:
                (
                    task_name,
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
                    api.add_task(
                        task_name, due_string=due_date
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


def insert_tasks_into_system_prompt(api, messages):
    tasks = fetch_todoist_tasks(api)
    if tasks:
        task_list = "\n".join(
            [f"- {task.content} [Task ID: {task.id}]" for task in tasks]
        )
        todoist_tasks_message = f"My outstanding tasks today:\n{task_list}"
        messages.append({"role": "system", "content": todoist_tasks_message})
    else:
        todoist_tasks_message = "Active Tasks:\n [All tasks complete!]"
        messages.append({"role": "system", "content": todoist_tasks_message})


module_call_counter.apply_call_counter_to_all(globals(), __name__)
