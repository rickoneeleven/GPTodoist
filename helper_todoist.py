import re, json, pytz, dateutil.parser, datetime, time, sys, os, signal, subprocess
import pyfiglet
import helper_parse, module_call_counter, helper_general
from dateutil.parser import parse
from datetime import date
from rich import print


def print_beast_mode_complete():
    ascii_banner = pyfiglet.figlet_format("BEAST MODE COMPLETE")
    print(ascii_banner)

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
        if "p1" in task_name.lower():
            task_params["priority"] = 4
        elif "p2" in task_name.lower():
            task_params["priority"] = 3
        elif "p3" in task_name.lower():
            task_params["priority"] = 2

        if project_id and project_id.strip():
            task_params["project_id"] = project_id

        task = api.add_task(**task_params)
        if task:
            print(f"[purple]Task '{task.content}' successfully added.[/purple]")
        else:
            print("Failed to add task.")

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
                    task.due = type("Due", (object,), {"datetime": now_london})()

                all_tasks.append(task)

            # Sort tasks by priority, due date, then creation date
            sorted_final_tasks = sorted(
                all_tasks,
                key=lambda t: (
                    -t.priority,
                    t.due.datetime
                    if t.due and hasattr(t.due, "datetime")
                    else now_london,
                    t.created if hasattr(t, "created") else "",
                ),
            )

            signal.alarm(0)
            return sorted_final_tasks

        except Exception as e:
            retries += 1
            print(f"Attempt {retries}: Failed to fetch tasks. Error: {e}")

            if retries == 99:
                print(
                    "[red]Failed to fetch tasks after 10 retries. Exiting with 'end of time'[/red]"
                )
                return None

            time.sleep(1)  # Add a 1-second delay before retrying


def complete_todoist_task_by_id(api, task_id):
    def handler(signum, frame):
        raise Exception("end of time")

    signal.signal(signal.SIGALRM, handler)

    # Set the signal to raise an Exception in 30 seconds
    # removed retry logic, as when it was "timing out" to complete task, it actually had complete it
    # in a lot of instances, then when it was retrying, it would complete the recurring task a few times too
    signal.alarm(30)

    try:
        task = api.get_task(task_id)
        task_name = task.content
        if task:
            api.close_task(task_id=task_id)
            print(f"[yellow]{task_name} completed[/yellow]")
        else:
            print("No task was found with the given id.")
            return False
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return False
    finally:
        signal.alarm(0)  # Disable the alarm

    return True


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

            if task_due:
                task_due_london = helper_general.convert_to_london_timezone(task_due)
                task_due_london_datetime = datetime.datetime.strptime(
                    task_due_london, "%Y-%m-%d %H:%M:%S"
                )
                task_due_time = task_due_london_datetime.strftime("%H:%M")
                task_due_date = task_due_london_datetime.date()

                if task_due_date < date.today():
                    task_due_str = task_due_london_datetime.strftime("%Y-%m-%d %H:%M")
                    task_name = task_name + " | " + task_due_str
                else:
                    task_due_str = task_due_time
                    task_name = task_name + " | " + task_due_str

                # print(f"Task Due: {task_due_str}")
            else:
                task_name = task_name + " | No due date"
            
            #show priority for tasks other than p4 (normal). the api stores the tasks in reverse order, this the bit below corrects it
            priority_prefix = f"\[p{5 - task.priority}]" if task.priority and task.priority > 1 else ""
            print(f"                   [green]{priority_prefix} {task_name}[/green]")
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
                # Update the j_number_of_todays_completed_tasks.json logic
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


def update_task_due_date(api, user_message):
    try:
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
            content = active_task["task_name"]
            #print(f"Loaded task_id: {task_id}, content: {content}")

        #print(f"Fetching task with ID: {task_id}")
        task = api.get_task(task_id)
        if task:
            #print(f"Task found: {task.content}")
            due_string = user_message.replace("time ", "", 1)
            #print(f"Extracted due_string: '{due_string}'")
            if due_string:
                if task.due and task.due.is_recurring:
                    #print("Task is recurring, completing current instance and creating a new task.")
                    api.close_task(task_id=task_id)
                    new_task_args = {"content": content, "due_string": due_string}
                    if hasattr(task, "project_id") and task.project_id:
                        new_task_args["project_id"] = task.project_id
                    new_task = api.add_task(**new_task_args)
                    print(f"New task '{new_task.content}' created with due date '{due_string}'.")
                else:
                    #print("Updating due date of non-recurring task.")
                    api.update_task(task_id=task.id, due_string=due_string)
                    print(f"Due date updated to '{due_string}'. Your next task is:")
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


def graft(api, user_message):
    try:
        if user_message.strip().lower() == "graft":
            if os.path.exists("j_grafted_tasks.json"):
                print("You're already grafting. Would you like to reset current graft and pick again? (y/n): ")
                response = input().strip().lower()
                if response != "y":
                    print("Continuing with current graft.")
                    return
            tasks = fetch_todoist_tasks(api)
            if tasks:
                for index, task in enumerate(tasks, start=1):
                    print(f"{index}. {task.content}")
                print("Please type the numbers of the 3 hardest tasks in order of difficulty (e.g., 4,7,9): ")
                selected_indexes = input()
                selected_indexes = [int(i) for i in selected_indexes.split(',')]
                selected_tasks = [tasks[i-1] for i in selected_indexes]
                grafted_tasks = [{"task_name": task.content, "task_id": task.id, "index": i} for i, task in enumerate(selected_tasks, start=1)]
                with open("j_grafted_tasks.json", "w") as file:
                    json.dump(grafted_tasks, file, indent=2)
            else:
                print("No tasks available to graft.")
        elif user_message.strip().lower() == "graft delete":
            if os.path.exists("j_grafted_tasks.json"):
                os.remove("j_grafted_tasks.json")
                print("Grafting process reset successfully.")
            else:
                print("No grafting process found to reset.")
        elif user_message.startswith("graft "):
            index_to_complete = int(user_message.split()[1])
            with open("j_grafted_tasks.json", "r") as file:
                grafted_tasks = json.load(file)
            task_to_complete = next((task for task in grafted_tasks if task["index"] == index_to_complete), None)
            if task_to_complete:
                if complete_todoist_task_by_id(api, task_to_complete["task_id"]):
                    grafted_tasks.remove(task_to_complete)
                    if grafted_tasks:
                        with open("j_grafted_tasks.json", "w") as file:
                            json.dump(grafted_tasks, file, indent=2)
                    else:
                        os.remove("j_grafted_tasks.json")
                        subprocess.call("reset")
                        print_beast_mode_complete()
                else:
                    print("Failed to complete the task with Todoist API.")
            else:
                print("Task index not found in grafted tasks.")
    except Exception as e:
        print(f"An error occurred: {e}")


def check_if_grafting(api):
    graft_file_path = "j_grafted_tasks.json"
    if os.path.exists(graft_file_path):
        with open(graft_file_path, "r") as file:
            grafted_tasks = json.load(file)
            subprocess.call("reset")
            print(f"[red]YOU'RE IN GRAFT MODE BABY, LETS GOOOOoooooooooo![/red]")
            for task in grafted_tasks:
                print(f"{task['index']}. {task['task_name']}")
        return True
    else:
        return False


def rename_todoist_task(api, user_message):
    try:
        # Extract the new task name from the user message
        new_task_name = user_message[len("rename "):].strip()

        # Load the current active task from the JSON file
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]

        # Fetch the task to be renamed using the Todoist API
        task = api.get_task(task_id)
        if task:
            # Update the task with the new name
            api.update_task(task_id=task_id, content=new_task_name)
            print(f"Task renamed to: {new_task_name}")
            return True
        else:
            print(f"Task with ID {task_id} not found.")
            return False
    except FileNotFoundError:
        print("Active task file not found.")
        return False
    except KeyError:
        print("Task ID not found in the active task file.")
        return False
    except Exception as error:
        print(f"Error renaming task: {error}")
        return False


def change_active_task_priority(api, user_message):
    try:
        # Extract the priority level from the user message
        priority_level = user_message.split()[-1]  # Assumes the last word is the priority level
        if priority_level not in ["1", "2", "3", "4"]:
            print("Invalid priority level. Please choose between 1, 2, 3, or 4.")
            return False

        # Load the current active task from the JSON file
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]

        # Map the priority level to Todoist's priority system
        todoist_priority = 5 - int(priority_level)  # Todoist's priority levels are 1 (normal) to 4 (urgent)

        # Fetch the task to be updated using the Todoist API
        task = api.get_task(task_id)
        if task:
            # Update the task with the new priority
            api.update_task(task_id=task_id, priority=todoist_priority)
            print(f"Task priority updated to p{priority_level}.")
            return True
        else:
            print(f"Task with ID {task_id} not found.")
            return False
    except FileNotFoundError:
        print("Active task file not found.")
        return False
    except KeyError:
        print("Task ID not found in the active task file.")
        return False
    except Exception as error:
        print(f"Error updating task priority: {error}")
        return False


module_call_counter.apply_call_counter_to_all(globals(), __name__)
