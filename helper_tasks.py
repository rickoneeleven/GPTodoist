import os, json, time
import module_call_counter, helper_general, helper_todoist_part1
from datetime import datetime, timedelta
from rich import print


def add_long_term_task(user_message):
    task_name = user_message[8:].strip()  # Extracts the task name from the message
    timestamp_str = helper_general.get_timestamp()  # Gets the current timestamp as a string
    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")  # Convert timestamp string to datetime object
    added = timestamp - timedelta(days=1)  # Subtract 1 day from timestamp, show it shows up on todays y_ tasks

    if os.path.exists("j_long_term_tasks.json"):
        with open("j_long_term_tasks.json", "r") as file:
            tasks = json.load(file)
            # Find the maximum index currently in use and increment by 1
            if tasks:  # Ensure the list is not empty
                max_index = max(task["index"] for task in tasks) + 1
            else:
                max_index = 0
    else:
        tasks = []
        max_index = 0  # Start from 0 if no tasks exist yet

    # Create the new task with a unique index
    task = {"index": max_index, "task_name": task_name, "added": added.strftime("%Y-%m-%d %H:%M:%S")}
    tasks.append(task)

    # Save the updated tasks list back to the JSON file
    with open("j_long_term_tasks.json", "w") as file:
        json.dump(tasks, file, indent=2)
    
    helper_general.backup_json_files()

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

    print(f"Task added to completed daily tasks: {task_content} (ID: {task_entry['id']})")
    
    
def print_tasks() -> None:
    filename = "j_long_term_tasks.json"

    with open(filename, "r") as f:
        tasks = json.load(f)

    # Filter out tasks starting with "x_" or "y_"
    filtered_tasks = [task for task in tasks if not (task["task_name"].startswith("x_") or task["task_name"].startswith("y_"))]
    #actually don't filter out tasks starting with x_ and y_
    filtered_tasks = [task for task in tasks]

    # Sort tasks by 'added' date in ascending order
    sorted_tasks = sorted(filtered_tasks, key=lambda task: datetime.strptime(task["added"], "%Y-%m-%d %H:%M:%S"))

    # Print the sorted list
    for task in sorted_tasks:
        index = f"[{task['index']}]".ljust(6)
        task_name = task["task_name"].ljust(90)
        added = task["added"]
        print(f"{index} {task_name} {added}")


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


def rename_long_task(user_message: str) -> None:
    if not os.path.exists("j_long_term_tasks.json"):
        print("No tasks available to rename.")
        return

    tokens = user_message.split()
    if len(tokens) < 4:
        print("Invalid input format. Usage: 'rename long <index> <new_name>'.")
        return

    try:
        id = int(tokens[2])
    except ValueError:
        print("Invalid index value. Please provide a valid integer.")
        return

    new_name = " ".join(tokens[3:])

    with open("j_long_term_tasks.json", "r") as file:
        tasks = json.load(file)

    task_found = False
    for task in tasks:
        if task["index"] == id:
            task["task_name"] = new_name
            task_found = True
            break

    if not task_found:
        print(f"Task with index {id} not found.")
        return

    with open("j_long_term_tasks.json", "w") as file:
        json.dump(tasks, file, indent=2)

    print(f"Task with index {id} renamed to '{new_name}'.")
    helper_general.backup_json_files()


def reset_task_indices(tasks: list):
    from datetime import datetime

    # Sort tasks in-place in increasing order of "added" date
    tasks.sort(key=lambda task: datetime.strptime(task["added"], "%Y-%m-%d %H:%M:%S"))

    # Reset task indices
    for i, task in enumerate(tasks):
        task["index"] = i


def delete_long_task(user_message: str) -> None:
    if not os.path.exists("j_long_term_tasks.json"):
        print("No tasks available to delete.")
        return

    tokens = user_message.split()
    if len(tokens) != 3:
        print("Invalid input format. Usage: 'delete long <index>'.")
        return

    helper_general.backup_json_files()
    try:
        id = int(tokens[2])
    except ValueError:
        print("Invalid index value. Please provide a valid integer.")
        return

    with open("j_long_term_tasks.json", "r") as file:
        tasks = json.load(file)

    task_found = False
    deleted_task = None
    for i, task in enumerate(tasks):
        if task["index"] == id:
            deleted_task = tasks.pop(i)
            task_found = True
            break

    if not task_found:
        print(f"Task with index {id} not found.")
        return

    # Update task indices after deletion
    reset_task_indices(tasks)

    with open("j_long_term_tasks.json", "w") as file:
        json.dump(tasks, file, indent=2)

    print(f"Task with index {id} deleted.")

    # Add the deleted task to j_todays_completed_tasks.json
    if deleted_task:
        add_to_completed_tasks(deleted_task)

    time.sleep(2)

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


def touch_long_date(user_message):
    # Extract the index from the message
    index = int(user_message.split(" ")[-1])
    # Load the json file
    with open("j_long_term_tasks.json", "r") as f:
        tasks = json.load(f)

    # Get the max index and increase it by 1
    max_index = max(task["index"] for task in tasks) + 1

    # Update the index and timestamp of the task
    for task in tasks:
        if task["index"] == index:
            task["index"] = max_index
            task["added"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            helper_todoist_part1.log_completed_task(task["task_name"])
            break

    # Write back to the json file
    with open("j_long_term_tasks.json", "w") as f:
        json.dump(tasks, f)

def untouch_long_date(user_message):
    # Extract the index from the message
    index = int(user_message.split(" ")[-1])
    # Load the json file
    with open("j_long_term_tasks.json", "r") as f:
        tasks = json.load(f)

    # Get the max index and increase it by 1
    max_index = max(task["index"] for task in tasks) + 1

    # Update the index and timestamp of the task
    for task in tasks:
        if task["index"] == index:
            task["index"] = max_index
            one_year_ago = datetime.now() - timedelta(days=365)
            task["added"] = one_year_ago.strftime("%Y-%m-%d %H:%M:%S")
            break

    # Write back to the json file
    with open("j_long_term_tasks.json", "w") as f:
        json.dump(tasks, f)

module_call_counter.apply_call_counter_to_all(globals(), __name__)
