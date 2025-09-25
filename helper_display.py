import datetime
from datetime import timedelta, timezone
import pytz
from rich import print
import traceback
import state_manager


def get_task_display_info(task, include_recurring_marker: bool = True) -> str:
    display_info = ""
    if not task:
        return ""
    try:
        if include_recurring_marker and getattr(task, "is_recurring_flag", False):
            display_info += "[cyan](r)[/cyan] "
        priority = getattr(task, "priority", None)
        if isinstance(priority, int) and priority > 1:
            priority_map = {4: 1, 3: 2, 2: 3}
            display_p = priority_map.get(priority)
            if display_p:
                color_map = {1: "red", 2: "orange1", 3: "yellow"}
                color = color_map.get(display_p, "white")
                display_info += f"[bold {color}](p{display_p})[/bold {color}] "
    except Exception as e:
        print(f"[yellow]Warn: Err gen display info {getattr(task, 'id', 'N/A')}: {e}[/yellow]")
    return display_info


def display_todoist_tasks(api):
    print("[cyan]Fetching tasks for display...[/cyan]")
    try:
        from helper_todoist_part2 import fetch_todoist_tasks
    except Exception as e:
        print(f"[red]Error importing task fetcher: {e}[/red]")
        return

    tasks = fetch_todoist_tasks(api)
    if tasks is None:
        print("[yellow]Unable to fetch tasks.[/yellow]")
        return
    if not tasks:
        print("\n[bold magenta]--- No tasks in active filter ---[/bold magenta]")
        print("[bold magenta]---------------------[/bold magenta]")
        return

    print("\n[bold magenta]--- All Tasks ---[/bold magenta]")
    for data in tasks:
        try:
            prefix = get_task_display_info(data, include_recurring_marker=False)
            due_str = ""
            is_recurring = getattr(data, "is_recurring_flag", False)
            due_string = getattr(data, "due_string_raw", None)
            recurring_prefix = f"[cyan](r) {due_string}[/cyan] - " if is_recurring and due_string else ("[cyan](r)[/cyan] " if is_recurring else "")

            if data.due and hasattr(data.due, "datetime_localized") and data.due.datetime_localized:
                try:
                    london_tz = pytz.timezone("Europe/London")
                    now_utc = datetime.datetime.now(timezone.utc)
                    now_london = now_utc.astimezone(london_tz)
                    if getattr(data.due.datetime_localized, "tzinfo", None) is not None:
                        time_diff = abs(data.due.datetime_localized - now_london)
                        is_now = time_diff < timedelta(seconds=1)
                        if is_now and not getattr(data, "has_time", False):
                            due_str = "(No due date)"
                        elif getattr(data, "has_time", False):
                            due_str = f"(Due: {data.due.datetime_localized.strftime('%Y-%m-%d %H:%M')})"
                        else:
                            due_str = f"(Due: {data.due.datetime_localized.strftime('%Y-%m-%d')} All day)"
                    else:
                        due_str = f"(Due: {data.due.datetime_localized.strftime('%Y-%m-%d %H:%M')} ?TZ?)"
                except Exception as fmt_err:
                    print(f"[yellow]Warning: Error formatting due date for display: {fmt_err}[/yellow]")
                    due_str = "(Due info error)"
            elif due_string:
                due_str = f"(Due: {due_string})"

            task_name = getattr(data, "content", "Unknown Task")
            print(f"{prefix}{recurring_prefix}{task_name} {due_str}")
            if getattr(data, "description", None):
                print(f"[italic blue]  Desc: {data.description}[/italic blue]")
        except Exception as e:
            print(f"[red]Err print line '{data.get('content', 'N/A') if isinstance(data, dict) else 'N/A'}': {e}[/red]")
            traceback.print_exc()
    print("[bold magenta]---------------------[/bold magenta]")


def check_if_grafting(api):
    grafted_tasks = state_manager.get_grafted_tasks()
    if grafted_tasks is None:
        return False
    if not grafted_tasks:
        return False
    print("[bold red]*** GRAFT MODE ACTIVE ***[/bold red]")
    print("[yellow]Focus on these tasks:[/yellow]")
    for i, task in enumerate(grafted_tasks):
        index = task.get("index", i + 1)
        print(f"  {index}. {task['task_name']}")
    print()
    return True

