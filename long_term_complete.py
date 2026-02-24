import traceback

from rich import print

import state_manager
import todoist_compat
from long_term_core import get_long_term_project_id, find_task_by_index


def complete_task(api, task_index: int, skip_logging: bool = False):
    """
    Completes a long-term task by its [index].

    - Recurring tasks: Todoist will auto-recreate the next instance per the recurrence rule.
    - Non-recurring tasks: task is completed and should not show up again.
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None

    try:
        target_task = find_task_by_index(api, project_id, task_index)
        if not target_task:
            print(f"[yellow]No task found with index [{task_index}] to complete.[/yellow]")
            return None

        print(f"[cyan]Completing long task: '{target_task.content}' (ID: {target_task.id})[/cyan]")
        success = todoist_compat.complete_task(api, target_task.id)
        if not success:
            print(f"[red]Todoist API indicated failure to close task ID: {target_task.id}.[/red]")
            return None

        if not skip_logging:
            state_manager.add_completed_task_log(
                {"task_name": f"(Completed Long Task) {target_task.content}"}
            )

        status = "SKIPPED" if skip_logging else "COMPLETED"
        print(f"[yellow]{target_task.content}[/yellow] -- {status}")
        return target_task

    except Exception as error:
        print(f"[red]An unexpected error occurred completing long task index [{task_index}]: {error}[/red]")
        traceback.print_exc()
        return None

