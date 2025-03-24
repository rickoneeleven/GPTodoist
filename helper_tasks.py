import os, json, time
import module_call_counter, helper_general, helper_todoist_part1
from datetime import datetime, timedelta
from rich import print


def add_completed_task(user_message):
    # Remove the "xx " prefix from the user message
    task_content = user_message[3:].strip()

    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Load existing tasks or create an empty list if the file doesn't exist
    try:
        with open("j_todays_completed_tasks.json", "r") as file:
            completed_tasks = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        completed_tasks = []

    # Find the maximum ID in the existing tasks
    max_id = max([task.get('id', 0) for task in completed_tasks], default=0)

    # Create the task entry with a new ID
    task_entry = {
        "id": max_id + 1,
        "datetime": timestamp,
        "task_name": task_content
    }

    # Add the new task to the list
    completed_tasks.append(task_entry)

    # Save the updated list back to the JSON file
    with open("j_todays_completed_tasks.json", "w") as file:
        json.dump(completed_tasks, file, indent=2)

    print(f"[bright_magenta]Task added to completed daily tasks:[/bright_magenta] {task_content} (ID: {task_entry['id']})")


def display_completed_tasks():
    completed_tasks_file = "j_todays_completed_tasks.json"

    # Check if the file exists
    if not os.path.exists(completed_tasks_file):
        print("No completed tasks found for today.")
        return

    # Read the tasks from the file and print them
    with open(completed_tasks_file, "r") as file:
        completed_tasks = json.load(file)
        for task in completed_tasks:
            print(f"{task['datetime']} - {task['task_name']}")
    print(" +++++++++ END FINISHED TASKS +++++++++")


def reset_task_indices(tasks: list):
    from datetime import datetime

    # Sort tasks in-place in increasing order of "added" date
    tasks.sort(key=lambda task: datetime.strptime(task["added"], "%Y-%m-%d %H:%M:%S"))

    # Reset task indices
    for i, task in enumerate(tasks):
        task["index"] = i


def add_to_completed_tasks(task):
    completed_tasks_file = "j_todays_completed_tasks.json"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(completed_tasks_file, "r") as file:
            completed_tasks = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        completed_tasks = []
    
    # Find the first available ID
    existing_ids = set(task.get('id', 0) for task in completed_tasks)
    new_id = 1
    while new_id in existing_ids:
        new_id += 1
    
    completed_tasks.append({
        "id": new_id,
        "datetime": now,
        "task_name": f"(Deleted long task) {task['task_name']}"
    })
    
    with open(completed_tasks_file, "w") as file:
        json.dump(completed_tasks, file, indent=2)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
