import pytz
import traceback
import time as time_module
from datetime import datetime, timedelta
from rich import print
from long_term_core import get_long_term_project_id, find_task_by_index, is_task_recurring


def delete_task(api, index):
    """Deletes a task with the given index from the Long Term Tasks project."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None

    try:
        target_task = find_task_by_index(api, project_id, index)

        if not target_task:
            print(f"[yellow]No task found with index [{index}] to delete.[/yellow]")
            return None

        task_content_for_log = target_task.content

        print(f"[cyan]Attempting to delete task: {task_content_for_log} (ID: {target_task.id})[/cyan]")
        success = api.delete_task(task_id=target_task.id)

        if success:
            print(f"[green]Successfully deleted task: {task_content_for_log}[/green]")
            return task_content_for_log
        else:
            print(f"[red]API indicated failure deleting task ID {target_task.id}. Please check Todoist.[/red]")
            return None

    except Exception as error:
        print(f"[red]An unexpected error occurred deleting task with index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None


def reschedule_task(api, index, schedule):
    """Reschedules a long-term task to the specified schedule string."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None

    if not schedule or not isinstance(schedule, str):
        print("[red]Invalid schedule provided for rescheduling.[/red]")
        return None
    if schedule.isdigit() and len(schedule) == 4:
        print("[red]Invalid time format for reschedule. Use formats like 'tomorrow 9am', 'next monday', etc.[/red]")
        return None

    try:
        target_task = find_task_by_index(api, project_id, index)

        if not target_task:
            print(f"[yellow]No task found with index [{index}] to reschedule.[/yellow]")
            return None

        is_recurring = is_task_recurring(target_task)
        if is_recurring:
            response = input(f"Task '{target_task.content}' is recurring. Rescheduling might break recurrence. Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled by user.")
                return None

        print(f"[cyan]Attempting to reschedule task '{target_task.content}' to '{schedule}'[/cyan]")

        updated_task = api.update_task(
            task_id=target_task.id,
            due_string=schedule
        )

        if not updated_task:
            print(f"[red]API call to update task did not return updated task details. Reschedule might have failed.[/red]")
            return None

        print("[cyan]Verifying reschedule...[/cyan]")
        time_module.sleep(1)
        verification_task = api.get_task(target_task.id)

        if verification_task and verification_task.due and verification_task.due.string:
            print(f"[green]Task reschedule successful. Verified due: '{verification_task.due.string}'[/green]")
            return updated_task
        else:
            if is_recurring:
                print(f"[yellow]Recurring task reschedule initiated. Verification inconclusive, please check Todoist manually.[/yellow]")
                return updated_task
            else:
                print(f"[red]Failed to verify task reschedule. Please check Todoist.[/red]")
                return None

    except Exception as error:
        print(f"[red]An unexpected error occurred rescheduling task index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None


def handle_recurring_task(api, task, skip_logging=False):
    """Completes a recurring task using the standard completion function."""
    if not task:
        print("[red]Error: No task provided to handle_recurring_task.[/red]")
        return False

    print(f"[cyan]Completing recurring task: '{task.content}' (ID: {task.id})[/cyan]")
    try:
        from helper_todoist_part1 import complete_todoist_task_by_id

        success = complete_todoist_task_by_id(api, task.id, skip_logging=skip_logging)

        if not success:
            print(f"[red]Failed to complete recurring task '{task.content}'.[/red]")
            return False
        return True

    except ImportError:
        print("[red]Error: Could not import 'complete_todoist_task_by_id'. Cannot complete recurring task.[/red]")
        return False
    except Exception as e:
        print(f"[red]Unexpected error handling recurring task '{task.content}': {e}[/red]")
        traceback.print_exc()
        return False


def handle_non_recurring_task(api, task, skip_logging=False):
    """
    Handles a non-recurring long-term task 'touch'.
    Logs completion (if not skipped) and sets due date to tomorrow.
    """
    if not task:
        print("[red]Error: No task provided to handle_non_recurring_task.[/red]")
        return None

    print(f"[cyan]Touching non-recurring task: '{task.content}' (ID: {task.id})[/cyan]")
    try:
        if not skip_logging:
            try:
                import state_manager
                completed_task_log_entry = {
                    'task_name': f"(Touched Long Task) {task.content}"
                }
                if state_manager.add_completed_task_log(completed_task_log_entry):
                    print(f"  [green]Logged task touch to completed tasks.[/green]")
                else:
                    print(f"  [red]Failed to log non-recurring task touch via state_manager.[/red]")
            except (NameError, ImportError):
                print("[red]Error: state_manager not available. Cannot log task touch.[/red]")
            except Exception as log_error:
                print(f"[red]Error logging non-recurring task touch: {log_error}[/red]")

        london_tz = pytz.timezone("Europe/London")
        tomorrow_london = (datetime.now(london_tz) + timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"  Setting due date to tomorrow: {tomorrow_london}")

        updated_task = api.update_task(
            task_id=task.id,
            due_string=tomorrow_london
        )

        if updated_task:
            print(f"  [green]Successfully updated task due date.[/green]")
            return updated_task
        else:
            print(f"  [red]API failed to update task due date.[/red]")
            return None

    except Exception as error:
        print(f"[red]An unexpected error occurred handling non-recurring task '{task.content}': {error}[/red]")
        traceback.print_exc()
        return None


def touch_task(api, task_index, skip_logging=False):
    """
    'Touches' a long-term task: Completes recurring ones, pushes non-recurring to tomorrow.
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None

    try:
        target_task = find_task_by_index(api, project_id, task_index)

        if not target_task:
            print(f"[yellow]No task found with index [{task_index}] to touch.[/yellow]")
            return None

        if is_task_recurring(target_task):
            success = handle_recurring_task(api, target_task, skip_logging=skip_logging)
            return target_task if success else None
        else:
            updated_task = handle_non_recurring_task(api, target_task, skip_logging=skip_logging)
            return updated_task

    except Exception as error:
        print(f"[red]An unexpected error occurred touching task index [{task_index}]: {error}[/red]")
        traceback.print_exc()
        return None


def add_task(api, task_name):
    """Adds a new task to the Long Term Tasks project using the task factory."""
    if not task_name or not isinstance(task_name, str):
        print("[red]Invalid task name provided for adding long-term task.[/red]")
        return None

    try:
        import helper_task_factory

        print(f"[cyan]Adding long-term task: '{task_name}'[/cyan]")

        task = helper_task_factory.create_task(
            api=api,
            task_content=task_name,
            task_type="long",
            options={"api": api}
        )

        if task:
            return task
        else:
            return None

    except ImportError:
        print("[red]Error: Could not import helper_task_factory. Long-term task creation failed.[/red]")
        return None
    except Exception as error:
        print(f"[red]An unexpected error occurred adding long-term task: {error}[/red]")
        traceback.print_exc()
        return None


def rename_task(api, index, new_name):
    """Renames a long-term task, preserving its index prefix."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None

    if not new_name or not isinstance(new_name, str):
        print("[red]Invalid new name provided for renaming.[/red]")
        return None

    try:
        target_task = find_task_by_index(api, project_id, index)

        if not target_task:
            print(f"[yellow]No task found with index [{index}] to rename.[/yellow]")
            return None

        if not hasattr(target_task, 'content'):
            print(f"[red]Error: Task object for index [{index}] is invalid (missing content). Cannot rename.[/red]")
            return None

        import re
        match = re.match(r'\s*\[(\d+)\]', target_task.content)
        if not match:
            print(f"[red]Error: Could not extract original index from task '{target_task.content}'. Cannot rename.[/red]")
            return None
        original_index = match.group(1)

        new_content = f"[{original_index}] {new_name.strip()}"

        print(f"[cyan]Renaming task index [{original_index}] from '{target_task.content}' to '{new_content}'[/cyan]")

        updated_task = api.update_task(
            task_id=target_task.id,
            content=new_content
        )

        if updated_task:
            print(f"[green]Task successfully renamed.[/green]")
            return updated_task
        else:
            print(f"[red]API failed to rename task ID {target_task.id}.[/red]")
            return None

    except Exception as error:
        print(f"[red]An unexpected error occurred renaming task index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None


def change_task_priority(api, index, priority_level):
    """Changes the priority of a long-term task."""
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None

    if priority_level not in [1, 2, 3, 4]:
        print("[red]Invalid priority level. Use 1-4 (1=P4 lowest, 4=P1 highest).[/red]")
        return None

    try:
        target_task = find_task_by_index(api, project_id, index)

        if not target_task:
            print(f"[yellow]No task found with index [{index}] to change priority.[/yellow]")
            return None

        # Map user input to Todoist priority values
        priority_map = {1: 4, 2: 3, 3: 2, 4: 1}
        todoist_priority = priority_map[priority_level]

        print(f"[cyan]Changing priority of '{target_task.content}' to P{priority_level}[/cyan]")

        updated_task = api.update_task(
            task_id=target_task.id,
            priority=todoist_priority
        )

        if updated_task:
            print(f"[green]Task priority successfully updated to P{priority_level}.[/green]")
            return updated_task
        else:
            print(f"[red]API failed to update priority for task ID {target_task.id}.[/red]")
            return None

    except Exception as error:
        print(f"[red]An unexpected error occurred changing priority for task index [{index}]: {error}[/red]")
        traceback.print_exc()
        return None