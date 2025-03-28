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
    graft,
    display_todoist_tasks,
    add_todoist_task,
    rename_todoist_task,
    change_active_task_priority,
)

# Import from other helper modules
import helper_tasks, helper_regex, helper_timesheets, helper_todoist_long, helper_task_factory

def ifelse_commands(api, user_message):
    command = user_message.lower()
    if command == "done":
        subprocess.call("reset")
        complete_active_todoist_task(api)
        return True
    elif command == "skip":
        subprocess.call("reset")
        complete_active_todoist_task(api, skip_logging=True)
        return True
    elif command == "diary":
        helper_diary.diary()
        return True
    elif command.startswith("diary "):
        new_objective = user_message[6:].strip()
        helper_diary.update_todays_objective(new_objective)
        return True
    elif command == "timesheet":
        helper_timesheets.timesheet()
        return True
    elif command.startswith("time long"):
        # Extract index and schedule from command
        parts = user_message.split(None, 3)  # Split into max 4 parts: "time", "long", "<index>", "<schedule>"
        if len(parts) < 4:
            print("[red]Invalid format. Usage: 'time long <index> <schedule>'[/red]")
            return True
            
        try:
            index = int(parts[2])
            schedule = parts[3]
            
            # Call the new function to reschedule the long task
            helper_todoist_long.reschedule_task(api, index, schedule)
        except ValueError:
            print("[red]Invalid index format. Usage: 'time long <index> <schedule>'[/red]")
        return True
    elif command.startswith("time"):
        check_and_update_task_due_date(api, user_message)
        return True
    elif command.startswith("xx"):
        helper_tasks.add_completed_task(user_message)
        return True
    elif command.startswith("postpone"):
        postpone_due_date(api, user_message)
        return True
    elif command.startswith("graft"):
        graft(api, user_message)
        return True
    elif command.startswith("~~~"):
        helper_regex.complete_todoist_task_by_title(user_message)
        display_todoist_tasks(api)
        return True
    elif command.startswith("|||"):
        helper_regex.search_todoist_tasks(user_message)
        return True
    elif command == "delete":
        delete_todoist_task(api)
        return True
    elif command == "all" or command == "show all":
        subprocess.call("reset")
        display_todoist_tasks(api)
        print("###################################################################################################")
        return True
    elif command == "completed" or command == "show complete":
        subprocess.call("reset")
        helper_tasks.display_completed_tasks()
        return True
    elif command == "clear":
        subprocess.call("reset")
        return True
    elif command == "flip":
        subprocess.call("reset")
        change_active_task()
        return True
    elif command.startswith("add long"):
        task_name = user_message[9:].strip()  # Extract task name after "add long"
        helper_todoist_long.add_task(api, task_name)
        # Removed reset call to allow feedback to be visible
        return True
    elif command.startswith("show long"):
        subprocess.call("reset")
        helper_todoist_long.display_tasks(api)
        return True
    elif command.startswith("rename long "):  # Add rename handler
        try:
            # Split the command into parts
            parts = user_message.split(None, 3)  # Split into max 4 parts
            if len(parts) < 4:
                print("[red]Invalid format. Usage: 'rename long <index> <new_name>'[/red]")
                return True
                
            index = int(parts[2])  # Get index from command
            new_name = parts[3]  # Get new name
            
            renamed_task = helper_todoist_long.rename_task(api, index, new_name)
            if renamed_task:
                subprocess.call("reset")
                # Similar removal of redundant display call here
        except ValueError:
            print("[red]Invalid index format. Usage: 'rename long <index> <new_name>'[/red]")
        return True
    elif command.startswith("rename "):
        subprocess.call("reset")
        rename_todoist_task(api, user_message)
        return True
    elif command.startswith("priority"):
        subprocess.call("reset")
        change_active_task_priority(api, user_message)
        return True
    elif command.startswith("delete long"):
        try:
            index = int(user_message.split()[-1])  # Get index from command
            deleted_task = helper_todoist_long.delete_task(api, index)
            if deleted_task:
                subprocess.call("reset")
                # Also removed redundant display call here
        except ValueError:
            print("[red]Invalid index format. Usage: 'delete long2 <index>'[/red]")
        return True
    elif command.startswith("touch long"):  # Add new handler here
        index = int(user_message.split()[-1])  # Extract index from command
        subprocess.call("reset")
        helper_todoist_long.touch_task(api, index)
        # Also removed redundant display call here
        return True
    elif command.startswith("add task"):
        add_todoist_task(api, user_message)
        return True

    return False

module_call_counter.apply_call_counter_to_all(globals(), __name__)