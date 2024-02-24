import module_call_counter, helper_todoist
import re, os
from fuzzywuzzy import process
from rich import print
from todoist_api_python.api import TodoistAPI

api = TodoistAPI(os.environ["TODOIST_API_KEY"])


def complete_todoist_task_by_title(user_message):
    tasks = helper_todoist.fetch_todoist_tasks(api)
    task_id = fuzzy_return_task_id(user_message, tasks)
    if task_id:
        helper_todoist.complete_todoist_task_by_id(api, task_id)
        #print(f"[green]Task ID: {task_id} complete[/green]")


def fuzzy_return_task_id(user_message, tasks):
    # stripping "~~" from user_message
    user_message = user_message.lstrip("~~~").strip()

    # dictionary to hold tasks as key-value pairs of task content and id
    tasks_dict = {task.content: task.id for task in tasks}

    # Fuzzy matching to get the closest match
    highest = process.extractOne(user_message, tasks_dict.keys())

    if highest is not None:
        return tasks_dict[highest[0]]
    else:
        print("NO MATCHES FOUND!!!!!111")
        return False


module_call_counter.apply_call_counter_to_all(globals(), __name__)
