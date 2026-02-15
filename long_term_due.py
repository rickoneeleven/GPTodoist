import traceback

from rich import print

from helper_due import update_task_due_preserving_schedule
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

        updated_task, target_date = update_task_due_preserving_schedule(api, target_task, due_input.strip())
        print(
            f"[green]Long task [{index}] due date moved to {target_date.isoformat()} while preserving recurrence/time metadata.[/green]"
        )
        return updated_task
    except Exception as error:
        print(f"[red]An unexpected error occurred updating due for long task index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None
