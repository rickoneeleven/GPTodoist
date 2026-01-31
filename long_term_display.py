import re
import traceback
from datetime import date as date_type, datetime
from dateutil.parser import parse
import pytz
from rich import print
from long_term_core import is_task_recurring
from long_term_indexing import (
    get_categorized_tasks,
)

def _format_due_absolute_for_display(task, now_london: datetime | None = None) -> str:
    """Return a user-facing due suffix with an absolute date (and time if present)."""
    if not task or not getattr(task, "due", None):
        return ""

    london_tz = pytz.timezone("Europe/London")
    if now_london is None:
        now_london = datetime.now(london_tz)

    due_obj = task.due
    due_string = getattr(due_obj, "string", None)
    due_val = getattr(due_obj, "datetime", None) or getattr(due_obj, "date", None)

    due_dt_london: datetime | None = None
    due_d: date_type | None = None

    try:
        if isinstance(due_val, str):
            if "T" in due_val:
                parsed = parse(due_val)
                if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
                    due_dt_london = london_tz.localize(parsed, is_dst=None)
                else:
                    due_dt_london = parsed.astimezone(london_tz)
            else:
                due_d = parse(due_val).date()
        elif isinstance(due_val, datetime):
            if due_val.tzinfo is None or due_val.tzinfo.utcoffset(due_val) is None:
                due_dt_london = london_tz.localize(due_val, is_dst=None)
            else:
                due_dt_london = due_val.astimezone(london_tz)
        elif isinstance(due_val, date_type):
            due_d = due_val
    except Exception:
        due_dt_london = None
        due_d = None

    rendered = None
    if due_dt_london is not None:
        rendered = due_dt_london.strftime("%a %d %b %Y %H:%M")
    elif due_d is not None:
        rendered = due_d.strftime("%a %d %b %Y")

    if not rendered:
        if due_string:
            return f" (Due: {due_string})"
        return ""

    rel = ""
    try:
        base_date = due_dt_london.date() if due_dt_london is not None else due_d
        if base_date is not None:
            days = (base_date - now_london.date()).days
            if days == 0:
                rel = " today"
            elif days == -1:
                rel = " yesterday"
            elif days == 1:
                rel = " tomorrow"
            elif days < 0:
                rel = f" ({abs(days)}d overdue)"
            else:
                rel = f" ({days}d)"
    except Exception:
        rel = ""

    suffix = f" (Due: {rendered}{rel})"
    if due_string:
        suffix += f" [dim](Todoist: '{due_string}')[/dim]"
    return suffix


def format_task_for_display(task):
    """Formats a long-term task for display including index, recurrence schedule, and priority."""
    if not task or not hasattr(task, 'content'):
        return "[red]Invalid Task Object[/red]"

    try:
        match = re.match(r'\s*\[(\d+)\]', task.content)
        task_index_str = "[?]"
        content_without_index = task.content

        if match:
            task_index_str = f"[{match.group(1)}]"
            content_without_index = re.sub(r'^\s*\[\d+\]\s*', '', task.content).strip()
        else:
            print(f"[yellow]Warning: Task '{task.content}' is missing index prefix for display.[/yellow]")

        prefix = ""
        if is_task_recurring(task):
            due_string = getattr(task.due, 'string', None) if task.due else None
            if due_string:
                prefix += f"[cyan](r) {due_string}[/cyan] - "
            else:
                prefix += "[cyan](r)[/cyan] "

        if hasattr(task, 'priority') and isinstance(task.priority, int) and task.priority > 1:
            priority_map = {4: 1, 3: 2, 2: 3}
            display_p = priority_map.get(task.priority)
            if display_p:
                color_map = {1: "red", 2: "orange1", 3: "yellow"}
                color = color_map.get(display_p, "white")
                prefix += f"[bold {color}](p{display_p})[/bold {color}] "

        display_text = f"{task_index_str} {prefix}{content_without_index}"

        return display_text

    except Exception as error:
        print(f"[red]Error formatting task for display (ID: {getattr(task, 'id', 'N/A')}): {error}[/red]")
        traceback.print_exc()
        return f"[?err {getattr(task, 'id', 'N/A')}] {task.content if task else 'N/A'}"


def display_formatted_task_list(title, tasks):
    """Print a list of tasks using the standard format."""
    print(f"\n{title}:")
    if tasks:
        for task in tasks:
            if task is None:
                print("[yellow]  Skipping None task during display.[/yellow]")
                continue
            formatted_task = format_task_for_display(task)
            print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
            if hasattr(task, 'description') and task.description:
                desc_preview = (task.description[:75] + '...') if len(task.description) > 75 else task.description
                print(f"  [italic blue]Desc: {desc_preview.replace(chr(10), ' ')}[/italic blue]")
    else:
        print("[dim]  No tasks in this category.[/dim]")


def display_tasks(api, task_type=None):
    """Displays categorized long-term tasks (One-Shots and Recurring)."""
    if task_type:
        print(f"[yellow]Warning: 'task_type' parameter in display_tasks is ignored.[/yellow]")

    print("\n[bold cyan]--- Long Term Tasks (Due) ---[/bold cyan]")
    try:
        one_shot_tasks, recurring_tasks = get_categorized_tasks(api)

        display_formatted_task_list("Recurring", recurring_tasks)
        display_formatted_task_list("One Shots", one_shot_tasks)

        print()

    except Exception as e:
        print(f"[red]An error occurred displaying long-term tasks: {e}[/red]")
        traceback.print_exc()


    


def display_next_long_task(api):
    """Displays the next due long-term task following current ordering rules.

    Shows up to two tasks at a time: Recurring first (sorted by priority, due, index),
    then One-Shots when no recurring remain. Only due/overdue tasks are considered.
    """
    print("\n[bold cyan]--- Next Long Tasks ---[/bold cyan]")
    try:
        one_shot_tasks, recurring_tasks = get_categorized_tasks(api)
        now_london = datetime.now(pytz.timezone("Europe/London"))

        tasks_to_show = []
        tasks_to_show.extend(recurring_tasks[:2])
        if len(tasks_to_show) < 2:
            tasks_to_show.extend(one_shot_tasks[: (2 - len(tasks_to_show))])

        if not tasks_to_show:
            print("[dim]  No due long-term tasks.[/dim]\n")
            return

        for idx, task in enumerate(tasks_to_show, start=1):
            base_text = format_task_for_display(task)

            # Always append absolute due info for clarity (the recurring schedule remains in base_text).
            due_extra = _format_due_absolute_for_display(task, now_london=now_london)

            print(f"  [green]{base_text}{due_extra}[/green]")

            if hasattr(task, 'description') and task.description:
                desc_preview = (task.description[:120] + '...') if len(task.description) > 120 else task.description
                print(f"    [italic blue]Desc: {desc_preview.replace(chr(10), ' ')}[/italic blue]")
        print()

    except Exception as e:
        print(f"[red]An error occurred displaying next long-term task: {e}[/red]")
        traceback.print_exc()
