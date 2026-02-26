from rich import print

import state_manager
from helper_due import update_task_due_preserving_schedule
from helper_todoist_part1 import add_to_active_task_file, _due_datetime_iso


def due_active_task(api, user_message: str) -> bool:
    active_task = state_manager.get_active_task()
    if not active_task:
        print("[red]No active task set. Cannot update due date.[/red]")
        return False

    task_id = active_task.get("task_id")
    if not task_id:
        print("[red]Invalid active task state (missing task_id).[/red]")
        state_manager.clear_active_task()
        return False

    due_input = user_message.replace("due ", "", 1).strip()
    if not due_input:
        print("[yellow]No due date provided. Usage: due <due_text>[/yellow]")
        return False

    try:
        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]Active task ID {task_id} not found in Todoist.[/yellow]")
            state_manager.clear_active_task()
            return False

        updated_task, target_date, effective_date = update_task_due_preserving_schedule(api, task, due_input)
        add_to_active_task_file(updated_task.content, updated_task.id, _due_datetime_iso(updated_task.due))
        if effective_date == target_date:
            print(
                f"[green]Task due date moved to {target_date.isoformat()} while preserving recurrence/time metadata.[/green]"
            )
        else:
            print(
                f"[yellow]Requested due date: {target_date.isoformat()}.[/yellow]"
            )
            print(
                f"[green]Recurrence preserved, but Todoist set next occurrence to: {effective_date}.[/green]"
            )
        return True
    except Exception as error:
        print(f"[red]Failed to apply due update: {error}[/red]")
        return False
