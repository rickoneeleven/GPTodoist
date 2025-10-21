import re
import pytz
import traceback
from datetime import datetime, date, time
from dateutil.parser import parse
from rich import print
from long_term_core import get_long_term_project_id, is_task_recurring, is_task_due_today_or_earlier
from long_term_hide import get_hidden_indices_for_today
import todoist_compat


def get_sort_index(task):
    """Extract the numerical index for sorting. Returns float('inf') if no index."""
    if not hasattr(task, 'content') or not isinstance(task.content, str):
        return float('inf')
    match = re.match(r'\s*\[(\d+)\]', task.content)
    try:
        return int(match.group(1)) if match else float('inf')
    except ValueError:
        return float('inf')


def get_due_sort_key(task, now_london, london_tz):
    if not task:
        return datetime.max.replace(tzinfo=pytz.utc)

    sort_dt = datetime.max.replace(tzinfo=pytz.utc)
    due = getattr(task, 'due', None)
    if not due:
        return sort_dt

    dv = getattr(due, 'date', None)
    if dv is None:
        return sort_dt

    try:
        if isinstance(dv, str):
            if 'T' in dv:
                dt = parse(dv)
                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                    sort_dt = london_tz.localize(dt, is_dst=None)
                else:
                    sort_dt = dt.astimezone(london_tz)
            else:
                d = parse(dv).date()
                t = now_london.time() if d <= now_london.date() else time.min
                sort_dt = london_tz.localize(datetime.combine(d, t))
        elif isinstance(dv, datetime):
            dt = dv
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                sort_dt = london_tz.localize(dt, is_dst=None)
            else:
                sort_dt = dt.astimezone(london_tz)
        elif isinstance(dv, date):
            t = now_london.time() if dv <= now_london.date() else time.min
            sort_dt = london_tz.localize(datetime.combine(dv, t))
    except Exception:
        pass

    return sort_dt


def fetch_and_index_long_tasks(api, project_id):
    """
    Fetches all tasks from the project and ensures they have indices.
    Returns a dictionary map of task_id: task_object for indexed tasks.
    """
    indexed_tasks_map = {}
    indices = set()
    unindexed_tasks = []

    try:
        tasks = todoist_compat.get_tasks_by_project(api, project_id)
        if tasks is None:
            print(f"[red]Error retrieving tasks for project ID {project_id}.[/red]")
            return {}

        for task in tasks:
            if not hasattr(task, 'content') or not hasattr(task, 'id'):
                print(f"[yellow]Warning: Skipping unexpected item in task list (type: {type(task)}): {task}[/yellow]")
                continue

            match = re.match(r'\s*\[(\d+)\]', task.content)
            if match:
                try:
                    index_num = int(match.group(1))
                    if index_num in indices:
                        print(f"[yellow]Warning: Duplicate index [{index_num}] found! Task: '{task.content}'. Manual fix needed.[/yellow]")
                    indices.add(index_num)
                    indexed_tasks_map[task.id] = task
                except ValueError:
                    print(f"[yellow]Warning: Invalid index format in task '{task.content}'. Treating as unindexed.[/yellow]")
                    if task.id not in indexed_tasks_map:
                        unindexed_tasks.append(task)
            else:
                if task.id not in indexed_tasks_map:
                    unindexed_tasks.append(task)

        fixed_indices_count = 0
        if unindexed_tasks:
            print(f"[yellow]Found {len(unindexed_tasks)} long-term tasks without a '[index]' prefix. Auto-fixing...[/yellow]")
            next_index = 0
            for task in unindexed_tasks:
                while next_index in indices:
                    next_index += 1

                new_content = f"[{next_index}] {task.content}"
                print(f"  Assigning index [{next_index}] to task '{task.content}' (ID: {task.id})")
                try:
                    update_success = api.update_task(task_id=task.id, content=new_content)
                    if update_success:
                        task.content = new_content
                        indices.add(next_index)
                        indexed_tasks_map[task.id] = task
                        fixed_indices_count += 1
                        next_index += 1
                    else:
                        print(f"  [red]API failed to update index for task ID {task.id}.[/red]")
                except Exception as index_error:
                    print(f"  [red]Error assigning index [{next_index}] to task ID {task.id}: {index_error}[/red]")

            if fixed_indices_count > 0:
                print(f"[green]Finished auto-indexing. Assigned indices to {fixed_indices_count} tasks.[/green]")
            elif unindexed_tasks:
                print(f"[yellow]Could not assign indices to {len(unindexed_tasks) - fixed_indices_count} tasks due to errors.[/yellow]")

        return indexed_tasks_map

    except Exception as error:
        print(f"[red]An unexpected error occurred fetching and indexing tasks: {error}[/red]")
        traceback.print_exc()
        return {}


def get_categorized_tasks(api):
    """Fetches, auto-fixes indices, filters by due date, and categorizes long-term tasks."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return [], []

    london_tz = pytz.timezone("Europe/London")
    now_london = datetime.now(london_tz)

    try:
        indexed_tasks_map = fetch_and_index_long_tasks(api, project_id)
        if not indexed_tasks_map:
            return [], []

        hidden_today = get_hidden_indices_for_today()

        filtered_tasks = [
            task for task in indexed_tasks_map.values()
            if is_task_due_today_or_earlier(task) and get_sort_index(task) not in hidden_today
        ]

        one_shot_tasks = []
        recurring_tasks = []
        for task in filtered_tasks:
            if is_task_recurring(task):
                recurring_tasks.append(task)
            else:
                one_shot_tasks.append(task)

        def sort_key_priority_due_index(task):
            # Priority: 4=P1 (highest), 3=P2, 2=P3, 1=P4 (lowest/default)
            # We negate to sort high priority first
            priority = -getattr(task, 'priority', 1)
            return (priority, get_due_sort_key(task, now_london, london_tz), get_sort_index(task))

        one_shot_tasks.sort(key=sort_key_priority_due_index)
        recurring_tasks.sort(key=sort_key_priority_due_index)

        return one_shot_tasks, recurring_tasks

    except Exception as error:
        print(f"[red]An unexpected error occurred fetching and categorizing tasks: {error}[/red]")
        traceback.print_exc()
        return [], []


def get_all_long_tasks_sorted_by_index(api):
    """Fetches, auto-fixes indices, and returns ALL long-term tasks sorted by index."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return []

    try:
        indexed_tasks_map = fetch_and_index_long_tasks(api, project_id)
        if not indexed_tasks_map:
            return []

        all_tasks_list = list(indexed_tasks_map.values())
        all_tasks_list.sort(key=get_sort_index)

        return all_tasks_list

    except Exception as error:
        print(f"[red]An unexpected error occurred getting all long tasks: {error}[/red]")
        traceback.print_exc()
        return []


def fetch_tasks(api, prefix=None):
    """DEPRECATED: Use get_categorized_tasks instead. Fetches raw long-term tasks."""
    print("[yellow]Warning: fetch_tasks is deprecated. Use get_categorized_tasks.[/yellow]")
    project_id = get_long_term_project_id(api)
    if not project_id:
        return []

    london_tz = pytz.timezone("Europe/London")
    now_london = datetime.now(london_tz)

    try:
        indexed_tasks_map = fetch_and_index_long_tasks(api, project_id)
        if not indexed_tasks_map:
            return []

        all_tasks_list = list(indexed_tasks_map.values())
        filtered_tasks = [task for task in all_tasks_list if is_task_due_today_or_earlier(task)]

        def sort_key_priority_due_index(task):
            # Priority: 4=P1 (highest), 3=P2, 2=P3, 1=P4 (lowest/default)
            # We negate to sort high priority first
            priority = -getattr(task, 'priority', 1)
            return (priority, get_due_sort_key(task, now_london, london_tz), get_sort_index(task))

        filtered_tasks.sort(key=sort_key_priority_due_index)
        return filtered_tasks

    except Exception as error:
        print(f"[red]Error fetching tasks (deprecated method): {error}[/red]")
        return []


def get_next_due_long_task(api):
    """Returns the next due long-term task following ordering rules.

    Ordering:
    - Consider only tasks due today or earlier (handled by get_categorized_tasks).
    - Prioritize Recurring tasks; if none remain, use One-Shots.
    - Within each category: priority(desc), then due date/time(asc), then index(asc).
    """
    try:
        one_shot_tasks, recurring_tasks = get_categorized_tasks(api)
        if recurring_tasks:
            return recurring_tasks[0]
        if one_shot_tasks:
            return one_shot_tasks[0]
        return None
    except Exception as error:
        print(f"[red]An unexpected error occurred selecting next due long task: {error}[/red]")
        traceback.print_exc()
        return None
