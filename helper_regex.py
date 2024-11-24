import module_call_counter, helper_todoist_part1, helper_todoist_part2
import re, os
from fuzzywuzzy import process
from rich import print
from todoist_api_python.api import TodoistAPI

api = TodoistAPI(os.environ["TODOIST_API_KEY"])


def complete_todoist_task_by_title(user_message):
    tasks = helper_todoist_part2.fetch_todoist_tasks(api)
    task_id = fuzzy_return_task_id(user_message, tasks)
    if task_id:
        helper_todoist_part1.complete_todoist_task_by_id(api, task_id)
        #print(f"[green]Task ID: {task_id} complete[/green]")

def search_todoist_tasks(user_message):
    # Strip "|||" from user_message
    search_term = user_message.lstrip("|").strip()
    try:
        # Use Todoist API's native search
        tasks = api.get_tasks(filter=f"search:{search_term}")
        
        if not tasks:
            print("[yellow]No matching tasks found[/yellow]")
            return

        print("\n[cyan]Found matching tasks:[/cyan]")
        for task in tasks:
            # Format the task display similar to display_todoist_tasks
            due_info = ""
            if task.due:
                if task.due.is_recurring:
                    due_info += "(r) "
                if task.due.string:
                    due_info += f"{task.due.string} | "
            
            priority_label = ""
            if task.priority and task.priority < 4:
                priority_label = f"(p{5 - task.priority}) "
                
            print(f"{due_info}{priority_label}{task.content}")
            if task.description:
                print(f"[italic blue]{task.description}[/italic blue]")
        print()
    except Exception as error:
        print(f"[red]Error searching tasks: {error}[/red]")


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
