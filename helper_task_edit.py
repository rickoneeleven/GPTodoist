from rich import print
import traceback
import state_manager
from helper_todoist_part1 import add_to_active_task_file


def rename_todoist_task(api, user_message):
    try:
        if not user_message.lower().startswith("rename "):
            print("[red]Invalid format. Use 'rename <new task name>'.[/red]")
            return False
        new_task_name = user_message[len("rename "):].strip()
        if not new_task_name:
            print("[yellow]No new task name provided.[/yellow]")
            return False

        active_task = state_manager.get_active_task()
        if not active_task:
            print("[red]Error: Active task file not found or invalid. Cannot rename.[/red]")
            return False
        task_id = active_task.get("task_id")
        if not task_id:
            print("[red]Error: 'task_id' missing in active task data.[/red]")
            return False

        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]Task ID {task_id} not found. Cannot rename.[/yellow]")
            state_manager.clear_active_task()
            return False

        print(f"[cyan]Renaming task '{task.content}' to '{new_task_name}'[/cyan]")
        update_success = api.update_task(task_id=task_id, content=new_task_name)

        if update_success:
            print(f"[green]Task successfully renamed to: '{new_task_name}'[/green]")
            add_to_active_task_file(new_task_name, task_id, active_task.get("task_due"))
            return True
        else:
            print(f"[red]Failed to rename task ID {task_id} via API.[/red]")
            return False

    except Exception as error:
        print(f"[red]An unexpected error occurred renaming task: {error}[/red]")
        traceback.print_exc()
        return False


def change_active_task_priority(api, user_message):
    try:
        parts = user_message.lower().split()
        if len(parts) < 2 or not parts[-1].isdigit():
            print("[red]Invalid format. Use 'priority <1|2|3|4>'.[/red]")
            return False
        level_str = parts[-1]
        if level_str not in ["1", "2", "3", "4"]:
            print("[red]Invalid priority level. Use 1-4.[/red]")
            return False
        priority_map = {"1": 4, "2": 3, "3": 2, "4": 1}
        todoist_priority = priority_map[level_str]

        active_task = state_manager.get_active_task()
        if not active_task:
            print("[red]Error: Active task not found. Cannot change priority.[/red]")
            return False
        task_id = active_task.get("task_id")
        if not task_id:
            print("[red]Error: 'task_id' missing in active task data.[/red]")
            return False

        task = api.get_task(task_id)
        if not task:
            print(f"[yellow]Task ID {task_id} not found.[/yellow]")
            state_manager.clear_active_task()
            return False

        print(f"[cyan]Changing priority of '{task.content}' to P{level_str}[/cyan]")
        update_success = api.update_task(task_id=task_id, priority=todoist_priority)

        if update_success:
            print(f"[green]Task priority updated to P{level_str}.[/green]")
            return True
        else:
            print(f"[red]Failed to update priority for task ID {task_id} via API.[/red]")
            return False

    except Exception as error:
        print(f"[red]An unexpected error occurred changing priority: {error}[/red]")
        traceback.print_exc()
        return False

