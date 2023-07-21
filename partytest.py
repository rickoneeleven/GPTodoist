import helper_todoist
import os, pprint
from todoist_api_python.api import TodoistAPI
from fuzzywuzzy import process


# function definition
def fuzzy_return_task_id(user_message, tasks):
    # stripping "~~" from user_message
    user_message = user_message.lstrip("~~").strip()

    # dictionary to hold tasks as key-value pairs of task content and id
    tasks_dict = {task.content: task.id for task in tasks}

    # Fuzzy matching to get the closest match
    highest = process.extractOne(user_message, tasks_dict.keys())

    if highest is not None:
        return tasks_dict[highest[0]]
    else:
        print("NO MATCHES FOUND!!!!!111")
        return False


api = TodoistAPI(os.environ["TODOIST_API_KEY"])

tasks = helper_todoist.fetch_todoist_tasks(api)

# usage
user_message = "~~ omega and"
print("task id is: ", fuzzy_return_task_id(user_message, tasks))

# pprint.pprint(tasks)
