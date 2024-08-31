import re, json, pytz, datetime, time, os, signal, subprocess
import module_call_counter
from dateutil.parser import parse
from rich import print

# Import necessary functions from part1
from helper_todoist_part1 import (
    get_active_filter,
    read_long_term_tasks,
    complete_todoist_task_by_id,
    format_due_time,
    print_beast_mode_complete,
    add_to_active_task_file,
)

def add_todoist_task(api, task_name):
    try:
        active_filter, project_id = get_active_filter()
        if not active_filter:
            print("No active filters configured. Update j_todoist_filters.json.")
            return None
        task_name = task_name.replace("add task ", "").strip()
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
            return None
        if task_time:
            if task_day:
                due_string = f"{task_time} {task_day}".strip()
            else:
                due_string = task_time.strip()
        else:
            due_string = None
        if due_string:
            api.update_task(task_id=task.id, due_string=due_string)
            print(f"Task due date set to '{due_string}'.")
        return task
    except Exception as error:
        print(f"[red] SDSFDSFSDFFF 0088 ++ Error adding task: {error} |||||  SDSFDSFSDFFF 0088 ++ [/red]")
        return None

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
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            now_london = now_utc.astimezone(london_tz).isoformat()
            for task in tasks:
                if task.due and task.due.datetime:
                    utc_dt = parse(task.due.datetime)
                    london_dt = utc_dt.astimezone(london_tz)
                    task.due.datetime = london_dt.isoformat()
                else:
                    if task.due and task.due.date:
                        due_date = parse(task.due.date).date()
                        end_of_due_day = datetime.datetime.combine(due_date, datetime.time(6, 59), tzinfo=london_tz)
                        task.due.datetime = end_of_due_day.isoformat()
                    else:
                        task.due = type("Due", (object,), {"datetime": now_london})()
                all_tasks.append(task)
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
            time.sleep(1)

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
            task = api.get_task(task_id)
            is_recurring = False
            recurrence_info = ""
            if task and task.due:
                is_recurring = task.due.is_recurring
                if is_recurring:
                    recurrence_info = "(r) "
                recurrence_info += task.due.string + " | "
            
            # Add priority label if priority is not 4
            priority_label = ""
            if task.priority and task.priority < 4:
                priority_label = f"(p{5 - task.priority}) "
            
            task_name = priority_label + recurrence_info + task_name
            add_to_active_task_file("postponed recurring - " + task_name, task_id, task_due)
            print(f"                   [green]{task_name}[/green]")
            print()
        else:
            print("\u2705")
            print()
        x_tasks = [
                lt_task
                for lt_task in long_term_tasks
                if lt_task["task_name"].startswith("x_")
            ]
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

def display_todoist_tasks(api):
    tasks = fetch_todoist_tasks(api)
    london_tz = pytz.timezone("Europe/London")
    if tasks:
        max_due_time_length = max(
            len(format_due_time(task.due.datetime if task.due else None, london_tz))
            for task in tasks
        )
        tab_size = 8
        for task in tasks:
            due_time_str = task.due.datetime if task.due else None
            due_time = format_due_time(due_time_str, london_tz).ljust(
                max_due_time_length + tab_size
            )
            
            # Check if the task is recurring
            is_recurring = False
            if task.due and hasattr(task.due, 'string'):
                recurrence_patterns = ['every', 'daily', 'weekly', 'monthly', 'yearly']
                is_recurring = any(pattern in task.due.string.lower() for pattern in recurrence_patterns)
            
            recurrence_prefix = "(r) " if is_recurring else ""
            
            # Add priority label if priority is not 4
            priority_label = ""
            if task.priority and task.priority < 4:
                priority_label = f"(p{5 - task.priority}) "
            
            task_name = f"{recurrence_prefix}{priority_label}{task.content}"
            print(f"{due_time}{task_name}")

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
        new_task_name = user_message[len("rename "):].strip()
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
        task = api.get_task(task_id)
        if task:
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
        priority_level = user_message.split()[-1]
        if priority_level not in ["1", "2", "3", "4"]:
            print("Invalid priority level. Please choose between 1, 2, 3, or 4.")
            return False
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
        todoist_priority = 5 - int(priority_level)
        task = api.get_task(task_id)
        if task:
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