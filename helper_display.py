import datetime
from datetime import timedelta, timezone
import pytz
from rich import print
import traceback
import state_manager
from typing import Optional


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


def _extract_due_date(task) -> Optional[datetime.date]:
    due = getattr(task, "due", None)
    if due is None:
        return None
    due_date_val = getattr(due, "date", None)
    if isinstance(due_date_val, datetime.date):
        return due_date_val
    if isinstance(due_date_val, str):
        try:
            return datetime.date.fromisoformat(due_date_val)
        except ValueError:
            return None
    due_datetime_val = getattr(due, "datetime", None)
    if isinstance(due_datetime_val, datetime.datetime):
        return due_datetime_val.date()
    if isinstance(due_datetime_val, str):
        try:
            return datetime.date.fromisoformat(due_datetime_val[:10])
        except ValueError:
            return None
    return None


def _format_due_str(task) -> str:
    due_date = _extract_due_date(task)
    if due_date is None:
        return "(No due date)"
    due = getattr(task, "due", None)
    dt_local = getattr(due, "datetime_localized", None) if due is not None else None
    if isinstance(dt_local, datetime.datetime) and getattr(task, "has_time", False):
        try:
            return f"(Due: {dt_local.strftime('%Y-%m-%d %H:%M')})"
        except Exception:
            return "(Due info error)"
    return f"(Due: {due_date.isoformat()} All day)"


def _task_bucket_for_objective(task, *, today: datetime.date) -> str:
    due_date = _extract_due_date(task)
    if due_date is None:
        return "No Due Date"
    if due_date < today:
        return "Overdue"
    if due_date == today:
        return "Due Today"
    return "Due Later"


def _sort_key_for_objective(task):
    priority = getattr(task, "priority", 1)
    if not isinstance(priority, int):
        priority = 1
    due = getattr(task, "due", None)
    due_dt = getattr(due, "datetime_localized", None) if due is not None else None
    if not isinstance(due_dt, datetime.datetime):
        due_dt = datetime.datetime.max.replace(tzinfo=pytz.utc)
    created = getattr(task, "created_at_sortable", None)
    if not isinstance(created, datetime.datetime):
        created = datetime.datetime.min.replace(tzinfo=pytz.utc)
    has_time = bool(getattr(task, "has_time", False))
    return (-priority, due_dt, not has_time, created)


def _group_tasks_for_objective(tasks: list, *, today: datetime.date) -> dict:
    grouped = {
        "Overdue": {"Recurring": [], "One-shot": []},
        "Due Today": {"Recurring": [], "One-shot": []},
        "No Due Date": {"Tasks": []},
        "Due Later": {"Recurring": [], "One-shot": []},
    }
    for task in tasks:
        bucket = _task_bucket_for_objective(task, today=today)
        is_recurring = bool(getattr(task, "is_recurring_flag", False))
        if bucket == "No Due Date":
            grouped[bucket]["Tasks"].append(task)
        else:
            key = "Recurring" if is_recurring else "One-shot"
            grouped[bucket][key].append(task)
    for bucket, sub in grouped.items():
        for key, items in sub.items():
            items.sort(key=_sort_key_for_objective)
    return grouped


def display_todoist_tasks_grouped_for_objective(api, filter_query_override: str | None = None):
    print("[cyan]Fetching tasks for display...[/cyan]")
    try:
        from helper_todoist_part2 import fetch_todoist_tasks
    except Exception as e:
        print(f"[red]Error importing task fetcher: {e}[/red]")
        return

    tasks = fetch_todoist_tasks(api, filter_query_override=filter_query_override)
    if tasks is None:
        print("[yellow]Unable to fetch tasks.[/yellow]")
        return
    if not tasks:
        print("\n[bold magenta]--- No tasks in active filter ---[/bold magenta]")
        print("[bold magenta]---------------------[/bold magenta]")
        return

    london_tz = pytz.timezone("Europe/London")
    today = datetime.datetime.now(timezone.utc).astimezone(london_tz).date()
    grouped = _group_tasks_for_objective(tasks, today=today)

    print("\n[bold magenta]--- Active Filter Tasks (Grouped) ---[/bold magenta]")

    def _print_task_line(task):
        prefix = get_task_display_info(task, include_recurring_marker=False)
        due_string = getattr(task, "due_string_raw", None)
        is_recurring = bool(getattr(task, "is_recurring_flag", False))
        recurring_prefix = f"[cyan](r) {due_string}[/cyan] - " if is_recurring and due_string else ("[cyan](r)[/cyan] " if is_recurring else "")
        task_name = getattr(task, "content", "Unknown Task")
        print(f"{prefix}{recurring_prefix}{task_name} {_format_due_str(task)}")

    def _print_bucket(title, sections):
        any_items = any(sections[k] for k in sections)
        if not any_items:
            return
        total = sum(len(sections[k]) for k in sections)
        print(f"\n[bold cyan]{title}[/bold cyan] [dim]({total})[/dim]")
        for section_name, items in sections.items():
            if not items:
                continue
            if section_name != "Tasks":
                print(f"[dim]{section_name}[/dim]")
            for task in items:
                _print_task_line(task)

    _print_bucket("Overdue", grouped["Overdue"])
    _print_bucket("Due Today", grouped["Due Today"])
    _print_bucket("No Due Date", grouped["No Due Date"])
    _print_bucket("Due Later", grouped["Due Later"])
    print("[bold magenta]---------------------[/bold magenta]")


def display_todoist_tasks(api, filter_query_override: str | None = None, header_label: str = "--- All Tasks ---", empty_label: str = "--- No tasks in active filter ---"):
    print("[cyan]Fetching tasks for display...[/cyan]")
    try:
        from helper_todoist_part2 import fetch_todoist_tasks
    except Exception as e:
        print(f"[red]Error importing task fetcher: {e}[/red]")
        return

    tasks = fetch_todoist_tasks(api, filter_query_override=filter_query_override)
    if tasks is None:
        print("[yellow]Unable to fetch tasks.[/yellow]")
        return
    if not tasks:
        print(f"\n[bold magenta]{empty_label}[/bold magenta]")
        print("[bold magenta]---------------------[/bold magenta]")
        return

    print(f"\n[bold magenta]{header_label}[/bold magenta]")
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


def _derive_today_overdue_query(active_filter_query: str | None) -> str:
    if not active_filter_query:
        return "today | overdue"
    if active_filter_query.strip().lower() == "today | overdue":
        return "today | overdue"
    return f"(today | overdue) & ({active_filter_query})"


def display_today_and_overdue_tasks(api):
    active_filter_query, _ = state_manager.get_active_filter_details()
    derived_query = _derive_today_overdue_query(active_filter_query)
    display_todoist_tasks(
        api,
        filter_query_override=derived_query,
        header_label="--- Today and Overdue Tasks ---",
        empty_label="--- No tasks due today or overdue ---",
    )


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
