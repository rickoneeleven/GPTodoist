import module_call_counter, helper_todoist_part1, helper_todoist_part2
import re, os
import datetime
import pytz
from dateutil.parser import parse
from fuzzywuzzy import process
from rich import print
from todoist_api_python.api import TodoistAPI
import todoist_compat

api = TodoistAPI(os.environ["TODOIST_API_KEY"])


def complete_todoist_task_by_title(user_message):
    tasks = helper_todoist_part2.fetch_todoist_tasks(api)
    task_id = fuzzy_return_task_id(user_message, tasks)
    if task_id:
        helper_todoist_part1.complete_todoist_task_by_id(api, task_id)
        #print(f"[green]Task ID: {task_id} complete[/green]")

def _format_next_due(due):
    if not due:
        return None
    london = pytz.timezone("Europe/London")
    dt_val = getattr(due, "datetime", None)
    if dt_val is not None:
        try:
            dt = parse(dt_val) if isinstance(dt_val, str) else dt_val
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                try:
                    dt = london.localize(dt, is_dst=None)
                except Exception:
                    pass
            else:
                dt = dt.astimezone(london)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return None
    date_val = getattr(due, "date", None)
    if date_val:
        try:
            d = parse(date_val).date() if isinstance(date_val, str) else date_val
            return f"{d.strftime('%Y-%m-%d')} All day"
        except Exception:
            return str(date_val)
    return None


def search_todoist_tasks(user_message):
    # Strip "|||" from user_message
    search_term = user_message.lstrip("|").strip()
    try:
        tasks = todoist_compat.get_tasks_by_filter(api, f"search:{search_term}")
        
        if not tasks:
            print("[yellow]No matching tasks found[/yellow]")
            return

        print("\n[cyan]Found matching tasks:[/cyan]")
        for task in tasks:
            parts = []
            if task.due:
                if getattr(task.due, "is_recurring", False):
                    parts.append("(r)")
                if getattr(task.due, "string", None):
                    parts.append(task.due.string)
                nxt = _format_next_due(task.due)
                if nxt:
                    parts.append(f"Next: {nxt}")
            due_info = " | ".join(parts)
            
            priority_label = ""
            if task.priority and task.priority < 4:
                priority_label = f"(p{5 - task.priority}) "
                
            prefix = f"{due_info} " if due_info else ""
            print(f"{prefix}{priority_label}{task.content}")
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
