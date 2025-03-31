import subprocess
import module_call_counter, helper_diary
from rich import print

# Import from helper_todoist_part1
from helper_todoist_part1 import (
    complete_active_todoist_task,
    check_and_update_task_due_date,
    postpone_due_date,
    delete_todoist_task,
    change_active_task,
)

# Import from helper_todoist_part2
from helper_todoist_part2 import (
    # graft, # Removed - Functionality removed
    display_todoist_tasks,
    add_todoist_task,
    rename_todoist_task,
    change_active_task_priority,
)

# Import from other helper modules
# Ensure all necessary imports are still present after removals
import helper_tasks, helper_regex, helper_timesheets, helper_todoist_long, helper_task_factory

def ifelse_commands(api, user_message):
    """Processes user commands using a large if/elif structure."""
    command = user_message.lower().strip() # Ensure consistent stripping

    # --- Task Completion ---
    if command == "done":
        subprocess.call("reset")
        complete_active_todoist_task(api)
        return True
    elif command == "skip":
        subprocess.call("reset")
        complete_active_todoist_task(api, skip_logging=True)
        return True
    elif command.startswith("~~~"): # Fuzzy complete by title
        helper_regex.complete_todoist_task_by_title(user_message) # Assumes user_message has prefix
        display_todoist_tasks(api) # Show updated tasks
        return True
    elif command.startswith("xx "): # Add ad-hoc completed task
        helper_tasks.add_completed_task(user_message) # Assumes user_message has prefix
        return True

    # --- Task Modification ---
    elif command.startswith("time "):
        # Handles regular task time updates
        check_and_update_task_due_date(api, user_message) # Assumes user_message has prefix
        return True
    elif command.startswith("postpone "):
        postpone_due_date(api, user_message) # Assumes user_message has prefix
        return True
    elif command.startswith("rename "):
        subprocess.call("reset")
        rename_todoist_task(api, user_message) # Assumes user_message has prefix
        return True
    elif command.startswith("priority "):
        subprocess.call("reset")
        change_active_task_priority(api, user_message) # Assumes user_message has prefix
        return True
    elif command == "delete": # Delete active task
        delete_todoist_task(api)
        # The delete function should handle showing next task prompt
        return True
    elif command == "flip": # Toggle active filter
        subprocess.call("reset")
        change_active_task()
        return True
    elif command.startswith("add task "):
        add_todoist_task(api, user_message) # Assumes user_message has prefix
        # Consider calling display_todoist_tasks(api) after adding?
        return True

    # --- Long Term Task Commands ---
    elif command.startswith("time long "):
        parts = user_message.split(None, 3)
        if len(parts) < 4:
            print("[red]Invalid format. Usage: 'time long <index> <schedule>'[/red]")
            return True # Handled command (invalidly)
        try:
            index = int(parts[2])
            schedule = parts[3]
            helper_todoist_long.reschedule_task(api, index, schedule)
        except ValueError:
            print("[red]Invalid index format. Index must be a number.[/red]")
        except Exception as e:
             print(f"[red]Error rescheduling long task: {e}[/red]")
        return True
    elif command.startswith("skip long "):
        try:
            parts = user_message.split()
            if len(parts) < 3:
                 print("[red]Invalid format. Usage: 'skip long <index>'[/red]")
                 return True
            index = int(parts[-1])
            subprocess.call("reset")
            helper_todoist_long.touch_task(api, index, skip_logging=True)
        except (ValueError, IndexError):
            print("[red]Invalid index format. Index must be a number.[/red]")
        except Exception as e:
             print(f"[red]Error skipping long task: {e}[/red]")
        return True
    elif command.startswith("touch long "):
         try:
            parts = user_message.split()
            if len(parts) < 3:
                 print("[red]Invalid format. Usage: 'touch long <index>'[/red]")
                 return True
            index = int(parts[-1])
            subprocess.call("reset")
            helper_todoist_long.touch_task(api, index, skip_logging=False) # Default, log completion
         except (ValueError, IndexError):
            print("[red]Invalid index format. Index must be a number.[/red]")
         except Exception as e:
             print(f"[red]Error touching long task: {e}[/red]")
         return True
    elif command.startswith("add long "):
        task_name = user_message[len("add long "):].strip()
        if not task_name:
             print("[yellow]No task name provided for 'add long'.[/yellow]")
             return True
        helper_todoist_long.add_task(api, task_name)
        # Consider calling helper_todoist_long.display_tasks(api) after adding?
        return True
    elif command.startswith("rename long "):
        try:
            parts = user_message.split(None, 3)
            if len(parts) < 4:
                print("[red]Invalid format. Usage: 'rename long <index> <new_name>'[/red]")
                return True
            index = int(parts[2])
            new_name = parts[3].strip()
            if not new_name:
                 print("[yellow]No new name provided for 'rename long'.[/yellow]")
                 return True
            renamed_task = helper_todoist_long.rename_task(api, index, new_name)
            if renamed_task:
                subprocess.call("reset")
                # Optionally display long tasks after rename:
                # helper_todoist_long.display_tasks(api)
        except ValueError:
            print("[red]Invalid index format. Index must be a number.[/red]")
        except Exception as e:
             print(f"[red]Error renaming long task: {e}[/red]")
        return True
    elif command.startswith("delete long "):
        try:
            parts = user_message.split()
            if len(parts) < 3:
                 print("[red]Invalid format. Usage: 'delete long <index>'[/red]")
                 return True
            index = int(parts[-1])
            deleted_task = helper_todoist_long.delete_task(api, index)
            if deleted_task:
                subprocess.call("reset")
                 # Optionally display long tasks after delete:
                 # helper_todoist_long.display_tasks(api)
        except (ValueError, IndexError):
            print("[red]Invalid index format. Index must be a number.[/red]")
        except Exception as e:
             print(f"[red]Error deleting long task: {e}[/red]")
        return True

    # --- Display and Info ---
    elif command == "all" or command == "show all": # Show current tasks
        subprocess.call("reset")
        display_todoist_tasks(api)
        print("###################################################################################################")
        return True
    elif command == "completed" or command == "show completed": # Show logged completed tasks
        subprocess.call("reset")
        helper_tasks.display_completed_tasks()
        return True
    elif command == "show long": # Show long term tasks
        subprocess.call("reset")
        helper_todoist_long.display_tasks(api)
        return True
    elif command.startswith("|||"): # Fuzzy search tasks
        helper_regex.search_todoist_tasks(user_message) # Assumes user_message has prefix
        return True

    # --- Diary and Timesheets ---
    elif command == "diary":
        helper_diary.diary()
        return True
    elif command.startswith("diary "):
        new_objective = user_message[len("diary "):].strip()
        if not new_objective:
             print("[yellow]No objective provided for 'diary'.[/yellow]")
             return True
        helper_diary.update_todays_objective(new_objective)
        return True
    elif command == "timesheet":
        # Consider adding a check or prompt if timesheets are disabled/unused?
        helper_timesheets.timesheet()
        return True

    # --- Utility ---
    elif command == "clear":
        subprocess.call("reset")
        return True

    # --- Graft Commands (Removed) ---
    # elif command.startswith("graft"):
    #    print("[yellow]Graft functionality has been removed.[/yellow]")
    #    return True # Command was recognized but is defunct

    # --- If command not recognized ---
    return False # Indicate command was not handled by this function

# Apply call counter decorator to all functions defined in this module
module_call_counter.apply_call_counter_to_all(globals(), __name__)