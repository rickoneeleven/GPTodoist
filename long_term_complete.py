import traceback
from datetime import datetime

import pytz

from rich import print

import recurring_due_deferrals
import state_manager
import todoist_compat
from long_term_core import (
    get_long_term_project_id,
    find_task_by_index,
    is_task_recurring,
    is_task_due_today_or_earlier,
)
import long_term_recent
from long_term_recurring_validation import (
    build_validation_snapshot,
    format_validation_snapshot,
    get_due_key,
    should_log_due_not_advanced,
    verify_recurring_due_advanced,
)


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

        was_recurring = is_task_recurring(target_task)
        if was_recurring:
            london_tz = pytz.timezone("Europe/London")
            try:
                target_task, catch_up_count = recurring_due_deferrals.prepare_recurring_task_for_completion(
                    api,
                    target_task,
                    datetime.now(london_tz).date(),
                )
            except RuntimeError as error:
                print(f"[yellow]{error}[/yellow]")
                return None
            if catch_up_count > 0:
                print(f"[dim]Advanced {catch_up_count} deferred recurring occurrence(s) before completion.[/dim]")
        previous_due_key = get_due_key(target_task) if was_recurring else None
        print(f"[cyan]Completing long task: '{target_task.content}' (ID: {target_task.id})[/cyan]")
        success = todoist_compat.complete_task(api, target_task.id)
        if not success:
            print(f"[red]Todoist API indicated failure to close task ID: {target_task.id}.[/red]")
            return None

        if was_recurring:
            verified_task = verify_recurring_due_advanced(api, target_task.id, previous_due_key)
            if verified_task is not None:
                verified_due_key = get_due_key(verified_task)
                validation_snapshot = build_validation_snapshot(verified_task)
                if verified_due_key and verified_due_key != previous_due_key:
                    if not is_task_due_today_or_earlier(verified_task):
                        long_term_recent.suppress_task_id(str(getattr(verified_task, "id", target_task.id)))
                    print(f"[dim]Todoist next occurrence: {verified_due_key}[/dim]")
                elif previous_due_key:
                    print(
                        "[dim yellow]Note: Todoist has not reflected the next recurrence yet (it can lag briefly after completion).[/dim yellow]"
                    )
                    print(
                        "[dim yellow]Validation: Todoist still returns "
                        f"{format_validation_snapshot(validation_snapshot)}[/dim yellow]"
                    )
                    if should_log_due_not_advanced(target_task):
                        state_manager.add_recurring_anomaly_log(
                            {
                                "event": "recurrence_due_not_advanced",
                                "source": "done long",
                                "task_id": str(getattr(target_task, "id", "")),
                                "task_content": getattr(target_task, "content", None),
                                "due_string": getattr(getattr(target_task, "due", None), "string", None),
                                "previous_due_key": previous_due_key,
                                "verified_due_key": verified_due_key,
                                "validated_task_checked": validation_snapshot.get("checked"),
                                "validated_task_updated_at": validation_snapshot.get("updated_at"),
                                "validated_task_completed_at": validation_snapshot.get("completed_at"),
                                "validated_task_due_string": validation_snapshot.get("due_string"),
                            }
                        )
            elif previous_due_key:
                print("[dim yellow]Note: recurrence not yet reflected by API; it may briefly reappear.[/dim yellow]")

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
