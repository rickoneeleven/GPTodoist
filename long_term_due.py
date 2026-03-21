import traceback

from rich import print

from helper_due import extract_due_date, update_task_due_preserving_schedule
from long_term_core import find_task_by_index, get_long_term_project_id


def due_task(api, index: int, due_input: str):
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None

    if not due_input or not isinstance(due_input, str):
        print("[red]Invalid due text provided.[/red]")
        return None

    try:
        target_task = find_task_by_index(api, project_id, index)
        if not target_task:
            print(f"[yellow]No task found with index [{index}] to update due date.[/yellow]")
            return None

        original_effective_date = extract_due_date(target_task)
        original_is_recurring = bool(getattr(getattr(target_task, "due", None), "is_recurring", False))
        updated_task, target_date, effective_date = update_task_due_preserving_schedule(api, target_task, due_input.strip())
        deferred_until_date = getattr(updated_task, "deferred_until_date", None)
        if effective_date == target_date:
            print(
                f"[green]Long task [{index}] due date moved to {target_date.isoformat()} while preserving recurrence/time metadata.[/green]"
            )
        elif deferred_until_date == target_date:
            print(f"[yellow]Requested due date: {target_date.isoformat()}.[/yellow]")
            print(
                f"[green]Long task [{index}] keeps its Todoist recurrence intact at {effective_date}, and the app will defer it locally until {target_date.isoformat()}.[/green]"
            )
        else:
            print(f"[yellow]Requested due date: {target_date.isoformat()}.[/yellow]")
            if original_is_recurring and original_effective_date and target_date <= original_effective_date:
                print(
                    f"[green]Long task [{index}] kept its current next valid recurrence: {effective_date}.[/green]"
                )
                print(
                    "[yellow]The app will not pull a recurring task earlier than its current next occurrence, "
                    "because doing that safely would require re-anchoring the rule.[/yellow]"
                )
            else:
                print(
                    f"[green]Long task [{index}] moved to the first valid recurrence on or after your requested date: {effective_date}.[/green]"
                )
        return updated_task
    except ValueError as error:
        print(f"[red]{error}[/red]")
        return None
    except Exception as error:
        print(f"[red]An unexpected error occurred updating due for long task index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None
