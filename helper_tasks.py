import os, json, time
import module_call_counter, helper_general
from datetime import datetime


def add_long_term_task(user_message):
    task_name = user_message[8:].strip()
    added = helper_general.get_timestamp()

    if os.path.exists("j_long_term_tasks.json"):
        with open("j_long_term_tasks.json", "r") as file:
            tasks = json.load(file)
            index = len(tasks)
    else:
        tasks = []
        index = 0

    task = {"index": index, "task_name": task_name, "added": added}

    tasks.append(task)

    with open("j_long_term_tasks.json", "w") as file:
        json.dump(tasks, file, indent=2)
    helper_general.backup_json_files()


def print_tasks() -> None:
    filename = "j_long_term_tasks.json"

    with open(filename, "r") as f:
        tasks = json.load(f)

    grouped_tasks = {}
    for task in tasks:
        first_word = task["task_name"].split()[0]
        if first_word not in grouped_tasks:
            grouped_tasks[first_word] = []

        grouped_tasks[first_word].append(task)

    for first_word in sorted(grouped_tasks.keys()):
        tasks_with_same_first_word = sorted(
            grouped_tasks[first_word], key=lambda task: task["index"]
        )

        if len(tasks_with_same_first_word) > 1:
            print(f"{'':8}{first_word}:")

        for task in tasks_with_same_first_word:
            index = f"[{task['index']}]".ljust(6)
            task_name = task["task_name"].ljust(90)
            added = helper_general.convert_to_london_timezone(task["added"])

            if task_name.strip().lower().startswith("x"):
                print(f"  {index} \033[31m{task_name}\033[0m {added}")
            else:
                print(f"  {index} {task_name} {added}")

        if len(tasks_with_same_first_word) > 1:
            print()


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
    for i, task in enumerate(tasks):
        if task["index"] == id:
            del tasks[i]
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
    time.sleep(2)


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
            break

    # Write back to the json file
    with open("j_long_term_tasks.json", "w") as f:
        json.dump(tasks, f)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
