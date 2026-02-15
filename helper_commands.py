import subprocess
import time
import module_call_counter
import helper_diary
import helper_tasks
import helper_regex
import helper_timesheets
import helper_todoist_long
import regular_due
import state_manager
import helper_hide
from rich import print
import traceback

from helper_todoist_part1 import (
    complete_active_todoist_task,
    check_and_update_task_due_date,
    postpone_due_date,
    delete_todoist_task,
    change_active_task,
)
from helper_display import display_todoist_tasks
from helper_todoist_part2 import add_todoist_task
from helper_task_edit import rename_todoist_task, change_active_task_priority

CMD_DONE = "done"
CMD_SKIP = "skip"
CMD_DELETE = "delete"
CMD_FLIP = "flip"
CMD_ALL = "all"
CMD_SHOW_ALL = "show all"
CMD_COMPLETED = "completed"
CMD_SHOW_COMPLETED = "show completed"
CMD_SHOW_LONG = "show long"
CMD_DIARY = "diary"
CMD_TIMESHEET = "timesheet"
CMD_CLEAR = "clear"
CMD_HIDE = "hide" # New command

PREFIX_FUZZY_COMPLETE = "~~~"
PREFIX_ADHOC_COMPLETE = "xx "
PREFIX_TIME = "time "
PREFIX_DUE = "due "
PREFIX_POSTPONE = "postpone "
PREFIX_RENAME = "rename "
PREFIX_PRIORITY = "priority "
PREFIX_ADD_TASK = "add task "
PREFIX_TIME_LONG = "time long "
PREFIX_DUE_LONG = "due long "
PREFIX_SKIP_LONG = "skip long "
PREFIX_TOUCH_LONG = "touch long "
PREFIX_HIDE_LONG = "hide long "
PREFIX_ADD_LONG = "add long "
PREFIX_RENAME_LONG = "rename long "
PREFIX_DELETE_LONG = "delete long "
PREFIX_PRIORITY_LONG = "priority long "
PREFIX_POSTPONE_LONG = "postpone long "
PREFIX_FUZZY_SEARCH = "|||"
PREFIX_DIARY_UPDATE = "diary "

def _parse_long_task_index(user_message: str, command_prefix: str) -> (int | None):
    try:
        parts = user_message.split()
        if len(parts) < 3:
            print(f"[red]Invalid format. Usage: '{command_prefix.strip()} <index>'[/red]")
            return None
        index = int(parts[-1]) # Takes the last part as index
        return index
    except (ValueError, IndexError):
        print("[red]Invalid or missing index. Index must be a number.[/red]")
        return None

def _parse_long_task_index_and_value(user_message: str, command_prefix: str, value_name: str) -> (tuple[int, str] | None):
    if len(user_message) <= len(command_prefix):
        print(f"[red]Invalid format. Usage: '{command_prefix.strip()} <index> <{value_name}>'[/red]")
        return None

    remainder = user_message[len(command_prefix):].strip()
    parts = remainder.split(None, 1) # Split into index and the rest

    if len(parts) < 2:
        print(f"[red]Invalid format. Missing index or {value_name}. Usage: '{command_prefix.strip()} <index> <{value_name}>'[/red]")
        return None

    index_str = parts[0]
    value = parts[1].strip()

    if not value:
         print(f"[red]Invalid format. The {value_name} part cannot be empty.[/red]")
         return None

    try:
        index = int(index_str)
        return index, value
    except ValueError:
        print(f"[red]Invalid index format '{index_str}'. Index must be a number.[/red]")
        return None


def _handle_done(api, user_message):
    subprocess.call("reset")
    complete_active_todoist_task(api)
    return True

def _handle_skip(api, user_message):
    subprocess.call("reset")
    complete_active_todoist_task(api, skip_logging=True)
    return True

def _handle_fuzzy_complete(api, user_message):
    helper_regex.complete_todoist_task_by_title(user_message)
    display_todoist_tasks(api) # Show updated tasks
    return True

def _handle_adhoc_complete(api, user_message):
    helper_tasks.add_completed_task(user_message)
    return True

def _handle_time(api, user_message):
    check_and_update_task_due_date(api, user_message)
    return True

def _handle_due(api, user_message):
    regular_due.due_active_task(api, user_message)
    return True

def _handle_postpone(api, user_message):
    postpone_due_date(api, user_message)
    return True

def _handle_rename(api, user_message):
    subprocess.call("reset")
    rename_todoist_task(api, user_message)
    return True

def _handle_priority(api, user_message):
    subprocess.call("reset")
    change_active_task_priority(api, user_message)
    return True

def _handle_delete(api, user_message):
    # Confirmation with countdown before deleting the active regular task
    from rich import print as rprint

    active_task = state_manager.get_active_task()
    task_name = active_task.get("task_name", "Unknown Task") if active_task else "Unknown Task"

    rprint(f"[bold red]You are about to delete the active task:[/bold red] [white]{task_name}[/white]")
    for remaining in range(5, 0, -1):
        rprint(f"[yellow]Deleting in {remaining} second(s)... Press Ctrl+C to abort.[/yellow]")
        time.sleep(1)

    choice = input("Delete this task? (y/N): ").strip().lower()
    if choice != "y":
        print("[cyan]Delete cancelled.[/cyan]")
        return True

    delete_todoist_task(api)
    return True

def _handle_flip(api, user_message):
    subprocess.call("reset")
    change_active_task()
    return True

def _handle_add_task(api, user_message):
    add_todoist_task(api, user_message)
    return True

def _handle_time_long(api, user_message):
    parsed = _parse_long_task_index_and_value(user_message, PREFIX_TIME_LONG, "schedule")
    if parsed is None:
        return True # Error message already printed by parser

    index, schedule = parsed
    try:
        helper_todoist_long.reschedule_task(api, index, schedule)
    except Exception as e:
         print(f"[red]Error rescheduling long task (Index: {index}, Schedule: '{schedule}'): {e}[/red]")
         traceback.print_exc()
    return True

def _handle_due_long(api, user_message):
    parsed = _parse_long_task_index_and_value(user_message, PREFIX_DUE_LONG, "due_text")
    if parsed is None:
        return True

    index, due_text = parsed
    try:
        helper_todoist_long.due_task(api, index, due_text)
    except Exception as e:
         print(f"[red]Error updating due date for long task (Index: {index}, Due: '{due_text}'): {e}[/red]")
         traceback.print_exc()
    return True

def _handle_skip_long(api, user_message):
    index = _parse_long_task_index(user_message, PREFIX_SKIP_LONG)
    if index is None:
        return True # Error handled by parser

    try:
        subprocess.call("reset")
        helper_todoist_long.touch_task(api, index, skip_logging=True)
    except Exception as e:
         print(f"[red]Error skipping long task (Index: {index}): {e}[/red]")
         traceback.print_exc()
    return True

def _handle_touch_long(api, user_message):
    index = _parse_long_task_index(user_message, PREFIX_TOUCH_LONG)
    if index is None:
        return True # Error handled by parser

    try:
        subprocess.call("reset")
        helper_todoist_long.touch_task(api, index, skip_logging=False)
    except Exception as e:
         print(f"[red]Error touching long task (Index: {index}): {e}[/red]")
         traceback.print_exc()
    return True

def _handle_add_long(api, user_message):
    task_name = user_message[len(PREFIX_ADD_LONG):].strip()
    if not task_name:
         print("[yellow]No task name provided for 'add long'.[/yellow]")
         return True # Handled (as invalid)
    try:
        helper_todoist_long.add_task(api, task_name)
    except Exception as e:
        print(f"[red]Error adding long task ('{task_name}'): {e}[/red]")
        traceback.print_exc()
    return True

def _handle_rename_long(api, user_message):
    parsed = _parse_long_task_index_and_value(user_message, PREFIX_RENAME_LONG, "new_name")
    if parsed is None:
        return True # Error handled by parser

    index, new_name = parsed
    try:
        renamed_task = helper_todoist_long.rename_task(api, index, new_name)
        if renamed_task:
            subprocess.call("reset")
    except Exception as e:
        print(f"[red]Error renaming long task (Index: {index}, New Name: '{new_name}'): {e}[/red]")
        traceback.print_exc()
    return True

def _handle_delete_long(api, user_message):
    index = _parse_long_task_index(user_message, PREFIX_DELETE_LONG)
    if index is None:
        return True # Error handled by parser

    try:
        deleted_task = helper_todoist_long.delete_task(api, index)
        if deleted_task:
            subprocess.call("reset")
    except Exception as e:
        print(f"[red]Error deleting long task (Index: {index}): {e}[/red]")
        traceback.print_exc()
    return True

def _handle_priority_long(api, user_message):
    parsed = _parse_long_task_index_and_value(user_message, PREFIX_PRIORITY_LONG, "priority")
    if parsed is None:
        return True # Error handled by parser

    index, priority_str = parsed
    
    # Validate priority level
    if not priority_str.isdigit() or priority_str not in ["1", "2", "3", "4"]:
        print("[red]Invalid priority level. Use 1-4 (1=P4 lowest, 4=P1 highest).[/red]")
        return True
    
    priority_level = int(priority_str)
    
    try:
        updated_task = helper_todoist_long.change_task_priority(api, index, priority_level)
        if updated_task:
            subprocess.call("reset")
    except Exception as e:
        print(f"[red]Error changing priority for long task (Index: {index}): {e}[/red]")
        traceback.print_exc()
    return True

def _handle_hide(api, user_message):
    subprocess.call("reset")
    active_task = state_manager.get_active_task()
    if active_task and "task_id" in active_task:
        task_id = active_task["task_id"]
        helper_hide.hide_task_for_today(task_id)
        print(f"[green]Regular task with ID {task_id} hidden for today.[/green]")
    else:
        print("[yellow]No active regular task to hide.[/yellow]")
    return True

def _handle_postpone_long(api, user_message):
    parsed = _parse_long_task_index_and_value(user_message, PREFIX_POSTPONE_LONG, "schedule")
    if parsed is None:
        return True # Error handled by parser

    index, schedule = parsed
    try:
        helper_todoist_long.postpone_task(api, index, schedule)
    except Exception as e:
         print(f"[red]Error postponing long task (Index: {index}, Schedule: '{schedule}'): {e}[/red]")
         traceback.print_exc()
    return True

def _handle_all(api, user_message):
    subprocess.call("reset")
    # Show standard tasks for the active filter
    display_todoist_tasks(api)
    # Then show due long-term tasks (recurring first, then one-shots)
    try:
        helper_todoist_long.display_tasks(api)
    except Exception as e:
        print(f"[red]Error displaying due long-term tasks: {e}[/red]")
    print("###################################################################################################")
    return True

def _handle_completed(api, user_message):
    subprocess.call("reset")
    helper_tasks.display_completed_tasks()
    return True

def _handle_show_long(api, user_message):
    subprocess.call("reset")
    helper_todoist_long.display_tasks(api) # Displays DUE long tasks
    return True

def _handle_hide_long(api, user_message):
    index = _parse_long_task_index(user_message, PREFIX_HIDE_LONG)
    if index is None:
        return True
    try:
        from helper_todoist_long import hide_task_for_today
        hide_task_for_today(index)
    except Exception as e:
        print(f"[red]Error hiding long task (Index: {index}): {e}[/red]")
        traceback.print_exc()
    return True

def _handle_fuzzy_search(api, user_message):
    helper_regex.search_todoist_tasks(user_message)
    return True

def _handle_diary(api, user_message):
    helper_diary.diary()
    return True

def _handle_diary_update(api, user_message):
    new_objective = user_message[len(PREFIX_DIARY_UPDATE):].strip()
    if not new_objective:
         print("[yellow]No objective provided for 'diary'.[/yellow]")
         return True # Handled (as invalid)
    try:
        helper_diary.update_todays_objective(new_objective)
    except Exception as e:
        print(f"[red]Error updating diary objective ('{new_objective}'): {e}[/red]")
        traceback.print_exc()
    return True

def _handle_timesheet(api, user_message):
    # Consider adding a check or prompt if timesheets are disabled/unused?
    helper_timesheets.timesheet()
    return True

def _handle_clear(api, user_message):
    subprocess.call("reset")
    return True


# --- Command Dispatch ---
COMMAND_DISPATCH = [
    (PREFIX_HIDE_LONG, _handle_hide_long, True),
    (PREFIX_TIME_LONG, _handle_time_long, True),
    (PREFIX_DUE_LONG, _handle_due_long, True),
    (PREFIX_SKIP_LONG, _handle_skip_long, True),
    (PREFIX_TOUCH_LONG, _handle_touch_long, True),
    (PREFIX_ADD_LONG, _handle_add_long, True),
    (PREFIX_RENAME_LONG, _handle_rename_long, True),
    (PREFIX_DELETE_LONG, _handle_delete_long, True),
    (PREFIX_PRIORITY_LONG, _handle_priority_long, True),
    (PREFIX_POSTPONE_LONG, _handle_postpone_long, True),
    (PREFIX_FUZZY_COMPLETE, _handle_fuzzy_complete, True),
    (PREFIX_ADHOC_COMPLETE, _handle_adhoc_complete, True),
    (PREFIX_TIME, _handle_time, True),
    (PREFIX_DUE, _handle_due, True),
    (PREFIX_POSTPONE, _handle_postpone, True),
    (PREFIX_RENAME, _handle_rename, True),
    (PREFIX_PRIORITY, _handle_priority, True),
    (PREFIX_ADD_TASK, _handle_add_task, True),
    (PREFIX_FUZZY_SEARCH, _handle_fuzzy_search, True),
    (PREFIX_DIARY_UPDATE, _handle_diary_update, True),
    (CMD_DONE, _handle_done, False),
    (CMD_SKIP, _handle_skip, False),
    (CMD_DELETE, _handle_delete, False),
    (CMD_FLIP, _handle_flip, False),
    (CMD_HIDE, _handle_hide, False), # New exact match command
    (CMD_ALL, _handle_all, False),
    (CMD_SHOW_ALL, _handle_all, False),
    (CMD_COMPLETED, _handle_completed, False),
    (CMD_SHOW_COMPLETED, _handle_completed, False), # Alias for "completed"
    (CMD_SHOW_LONG, _handle_show_long, False), # Shows DUE long tasks
    (CMD_DIARY, _handle_diary, False), # Checked AFTER "diary "
    (CMD_TIMESHEET, _handle_timesheet, False),
    (CMD_CLEAR, _handle_clear, False),
]

def process_command(api, user_message):
    """
    Processes the user command by finding the appropriate handler in the dispatch table.
    Returns True if a handler was found and executed, False otherwise.
    """
    command_lower = user_message.lower().strip()
    if not command_lower:
        return False # Ignore empty input

    for trigger, handler, is_prefix in COMMAND_DISPATCH:
        match = False
        if is_prefix:
            if command_lower.startswith(trigger):
                match = True
        else:
            if command_lower == trigger:
                match = True

        if match:
            try:
                # Execute the handler
                handler(api, user_message) # Pass the original user_message for parsing
                return True # Indicate command was handled
            except Exception as handler_error:
                # Catch unexpected errors within the handler itself (should be rare if handlers are robust)
                print(f"[bold red]Unexpected error during execution of handler '{handler.__name__}' for command '{command_lower}':[/bold red]")
                print(f"[red]{handler_error}[/red]")
                traceback.print_exc()
                return True # Still return True as the command was recognized, even if it failed

    # If no handler was found
    return False

def ifelse_commands(api, user_message):
    return process_command(api, user_message)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
