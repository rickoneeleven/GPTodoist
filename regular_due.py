from rich import print

import state_manager
from helper_due import extract_due_date, update_task_due_preserving_schedule
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

        original_effective_date = extract_due_date(task)
        original_is_recurring = bool(getattr(getattr(task, "due", None), "is_recurring", False))
        updated_task, target_date, effective_date = update_task_due_preserving_schedule(api, task, due_input)
        add_to_active_task_file(updated_task.content, updated_task.id, _due_datetime_iso(updated_task.due))
        deferred_until_date = getattr(updated_task, "deferred_until_date", None)
        if effective_date == target_date:
            print(
                f"[green]Task due date moved to {target_date.isoformat()} while preserving recurrence/time metadata.[/green]"
            )
        elif deferred_until_date == target_date:
            print(f"[yellow]Requested due date: {target_date.isoformat()}.[/yellow]")
            print(
                f"[green]Recurring schedule stays intact in Todoist at {effective_date}, and the app will defer it locally until {target_date.isoformat()}.[/green]"
            )
        else:
            print(
                f"[yellow]Requested due date: {target_date.isoformat()}.[/yellow]"
            )
            if original_is_recurring and original_effective_date and target_date <= original_effective_date:
                print(
                    f"[green]Recurring schedule kept its current next valid occurrence: {effective_date}.[/green]"
                )
                print(
                    "[yellow]The app will not pull a recurring task earlier than its current next occurrence, "
                    "because doing that safely would require re-anchoring the rule.[/yellow]"
                )
            else:
                print(
                    f"[green]Recurring schedule moved to the first valid occurrence on or after your requested date: {effective_date}.[/green]"
                )
        return True
    except Exception as error:
        print(f"[red]Failed to apply due update: {error}[/red]")
        return False
