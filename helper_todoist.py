import re, json, pytz, dateutil.parser, datetime, time, sys, os, signal, subprocess
import pyfiglet
import module_call_counter
from dateutil.parser import parse
from datetime import timedelta
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


def add_todoist_task(api, task_name):
    try:
        active_filter, project_id = get_active_filter()

        if not active_filter:
            print("No active filters configured. Update j_todoist_filters.json.")
            return None

        # Remove the "add task " prefix from the task name
        task_name = task_name.replace("add task ", "").strip()

        # Regex to handle the format, capturing the time "XX:XX" and all following text, if any
        time_day_pattern = re.compile(r"^(.*?)(\d{2}:\d{2})(.*)$")
        match = time_day_pattern.match(task_name)
        if match:
            pre_time_text = match.group(1).strip() if match.group(1) else ''
            task_time = match.group(2).strip() if match.group(2) else None
            task_day = match.group(3).strip() if match.group(3) else None
            task_name = pre_time_text
        else:
            task_time = None
            task_day = None
            print("No time pattern found.")

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

        # Create the task initially without a due date
        task = api.add_task(**task_params)
        if task:
            print(f"[purple]Task '{task.content}' successfully added.[/purple]")
        else:
            print("Failed to add task.")
            return None

        # Construct due_string using the extracted time and day
        if task_time:
            if task_day:  # Only add task_day if it is not None and not an empty string
                due_string = f"{task_time} {task_day}".strip()
            else:
                due_string = task_time.strip()  # Use just the time if no day is specified
        else:
            due_string = None

        # Update the task with due_string if it's specified
        if due_string:
            api.update_task(task_id=task.id, due_string=due_string)
            print(f"Task due date set to '{due_string}'.")

        return task
    except Exception as error:
        print(f"[red] SDSFDSFSDFFF 0088 ++ Error adding task: {error} |||||  SDSFDSFSDFFF 0088 ++ [/red]")
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
                    # If the task is due yesterday or earlier without a specific time, set it to the end of that day
                    if task.due and task.due.date:
                        due_date = parse(task.due.date).date()
                        end_of_due_day = datetime.datetime.combine(due_date, datetime.time(6, 59), tzinfo=london_tz)
                        task.due.datetime = end_of_due_day.isoformat()
                    else:
                        # If no due date is provided, use the current time in London
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
            log_completed_task(task_name)
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
        today = datetime.date.today()

        if tasks:
            next_task = tasks[0]
            task_name = next_task.content
            task_id = next_task.id
            task_due = (
                next_task.due.datetime
                if next_task.due and next_task.due.datetime
                else None
            )
            
            # Fetch the task again to check for recurrence
            task = api.get_task(task_id)
            is_recurring = False
            recurrence_info = ""

            if task and task.due:
                is_recurring = task.due.is_recurring
                recurrence_info = task.due.string + " | "  # Includes the recurrence pattern

            task_name = recurrence_info + task_name  # Prepend recurrence info to task name
            add_to_active_task_file("postponed recurring - " + task_name, task_id, task_due)
            
            # Show priority for tasks other than p4
            priority_prefix = f"[p{5 - task.priority}]" if task.priority and task.priority > 1 else ""
            print(f"                   [green]{priority_prefix} {task_name}[/green]")
            print()

        else:
            print("\u2705")
            print()
            
        x_tasks = [
                lt_task
                for lt_task in long_term_tasks
                if lt_task["task_name"].startswith("x_")
            ]
        
        # Sort x_tasks based on the added date in ascending order
        x_tasks.sort(key=lambda x: datetime.datetime.strptime(x["added"], "%Y-%m-%d %H:%M:%S"))

        if x_tasks:
            print("Complete in your own time:")
            for x_task in x_tasks:
                print(f"[{x_task['index']}][dodger_blue1] {x_task['task_name']}[/dodger_blue1]")
            print()

        y_tasks = [
            lt_task
            for lt_task in long_term_tasks
            if lt_task["task_name"].startswith("y_") and datetime.datetime.strptime(lt_task["added"], "%Y-%m-%d %H:%M:%S").date() < today
        ]
        
        # Sort y_tasks based on the added date in ascending order
        y_tasks.sort(key=lambda x: datetime.datetime.strptime(x["added"], "%Y-%m-%d %H:%M:%S"))

        if y_tasks:
            print("Daily tasks:")
            for y_task in y_tasks:
                print(f"[{y_task['index']}][dodger_blue1] {y_task['task_name']}[/dodger_blue1]")
            print()
        else:
            print("you've completed all of your daily, nib, nibs. Well done \o/")
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


def postpone_due_date(api, user_message):
    try:
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
            content = active_task["task_name"]

        task = api.get_task(task_id)
        if task:
            due_string = user_message.replace("postpone ", "", 1)
            # Check if due_string is in HHMM format
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
                    #print(f"New task '{new_task.content}' created with due date '{due_string}'.")
                else:
                    api.update_task(task_id=task.id, due_string=due_string)
                    #print(f"Due date updated to '{due_string}'. Your next task is:")
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
        # Load the current active task details
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
            content = active_task["task_name"]

        # Retrieve the task from Todoist
        task = api.get_task(task_id)
        if not task:
            print(f"Task {task_id} not found.")
            return

        # Extract and validate the due date string
        due_string = user_message.replace("time ", "", 1)
        if due_string.isdigit() and len(due_string) == 4:
            print("[red]bad time format[/red]")
            return

        if not due_string:
            print("No due date provided.")
            return

        # Update the task with new due date
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
        subprocess.call("reset")
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
            print(f"[red]YOU'RE IN GRAFT MODE BABY, LETS GOOOOoooooooooo![/red]")
            print()
            print()
            for task in grafted_tasks:
                print(f"{task['index']}. {task['task_name']}")
            print()
            print()
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


def log_completed_task(task_name):
    # Define the file path for storing completed tasks
    completed_tasks_file = "j_todays_completed_tasks.json"
    today = datetime.date.today()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Human-readable format

    # Check if the file exists and read existing data; if not, initialize with an empty list
    try:
        with open(completed_tasks_file, "r") as file:
            completed_tasks = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        completed_tasks = []

    # Get the current date
    current_date = datetime.datetime.now().date()
    # Filter tasks, only keep those from the last two days
    completed_tasks = [task for task in completed_tasks if parse(task['datetime']).date() > current_date - timedelta(days=2)]

    # Append the new task with the current datetime
    completed_tasks.append({"datetime": now, "task_name": task_name})

    # Write the updated list back to the file
    with open(completed_tasks_file, "w") as file:
        json.dump(completed_tasks, file, indent=2)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
