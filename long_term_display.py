import re
import traceback
from rich import print
from long_term_core import is_task_recurring
from long_term_indexing import (
    get_categorized_tasks,
    get_all_long_tasks_sorted_by_index,
    get_next_due_long_task,
)


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


def display_all_long_tasks(api):
    """Fetches and displays ALL long-term tasks, sorted by index."""
    print("\n[bold magenta]--- All Long Term Tasks (by Index) ---[/bold magenta]")
    try:
        all_tasks = get_all_long_tasks_sorted_by_index(api)
        display_formatted_task_list("All Tasks", all_tasks)
        print()

    except Exception as e:
        print(f"[red]An error occurred displaying all long-term tasks: {e}[/red]")
        traceback.print_exc()


def display_next_long_task(api):
    """Displays the next due long-term task following current ordering rules.

    Shows one task at a time: Recurring first (sorted by priority, due, index),
    then One-Shots when no recurring remain. Only due/overdue tasks are considered.
    """
    print("\n[bold cyan]--- Next Long Task ---[/bold cyan]")
    try:
        task = get_next_due_long_task(api)
        if not task:
            print("[dim]  No due long-term tasks.[/dim]\n")
            return

        base_text = format_task_for_display(task)

        # Append due info for non-recurring tasks (recurring already include schedule in base_text)
        due_extra = ""
        try:
            if not is_task_recurring(task) and getattr(task, 'due', None):
                due_obj = task.due
                due_str = getattr(due_obj, 'string', None)
                due_date_val = getattr(due_obj, 'date', None)
                if due_str:
                    due_extra = f" (Due: {due_str})"
                elif due_date_val:
                    due_extra = f" (Due: {due_date_val})"
        except Exception:
            pass

        print(f"  [green]{base_text}{due_extra}[/green]")

        if hasattr(task, 'description') and task.description:
            desc_preview = (task.description[:120] + '...') if len(task.description) > 120 else task.description
            print(f"    [italic blue]Desc: {desc_preview.replace(chr(10), ' ')}[/italic blue]")
        print()

    except Exception as e:
        print(f"[red]An error occurred displaying next long-term task: {e}[/red]")
        traceback.print_exc()
