import traceback

from rich import print

from helper_due import update_task_due_preserving_schedule
from long_term_core import find_task_by_index, get_long_term_project_id

def _has_starting_anchor(due_string: str | None) -> bool:
    if not isinstance(due_string, str):
        return False
    return " starting " in due_string.lower()


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

        due_obj = getattr(target_task, "due", None)
        if due_obj and getattr(due_obj, "is_recurring", False):
            if _has_starting_anchor(getattr(due_obj, "string", None)):
                print(
                    "[bold yellow]Warning:[/bold yellow] this task's recurrence rule contains "
                    "'starting YYYY-MM-DD', which can stop Todoist from advancing the recurrence on completion."
                )
                print("[yellow]This command will normalize the recurrence rule by stripping the starting anchor.[/yellow]")

        updated_task, target_date, effective_date = update_task_due_preserving_schedule(api, target_task, due_input.strip())
        if effective_date == target_date:
            print(
                f"[green]Long task [{index}] due date moved to {target_date.isoformat()} while preserving recurrence/time metadata.[/green]"
            )
        else:
            print(f"[yellow]Requested due date: {target_date.isoformat()}.[/yellow]")
            print(
                f"[green]Recurrence preserved, but Todoist set next occurrence to: {effective_date}.[/green]"
            )
        return updated_task
    except ValueError as error:
        print(f"[red]{error}[/red]")
        return None
    except Exception as error:
        print(f"[red]An unexpected error occurred updating due for long task index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None
