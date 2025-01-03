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
import helper_tasks, helper_regex, helper_timesheets

def ifelse_commands(api, user_message):
    command = user_message.lower()
    if command == "done":
        subprocess.call("reset")
        complete_active_todoist_task(api)
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
        helper_tasks.print_tasks()
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
        helper_tasks.add_long_term_task(user_message)
        subprocess.call("reset")
        helper_tasks.print_tasks()
        return True
    elif command.startswith("show long"):
        subprocess.call("reset")
        helper_tasks.print_tasks()
        return True
    elif command.startswith("rename long"):
        helper_tasks.rename_long_task(user_message)
        return True
    elif command.startswith("rename"):
        subprocess.call("reset")
        rename_todoist_task(api, user_message)
        return True
    elif command.startswith("priority"):
        subprocess.call("reset")
        change_active_task_priority(api, user_message)
        return True
    elif command.startswith("delete long"):
        helper_tasks.delete_long_task(user_message)
        subprocess.call("reset")
        helper_tasks.print_tasks()
        return True
    elif command.startswith("touch long"):
        helper_tasks.touch_long_date(user_message)
        subprocess.call("reset")
        helper_tasks.print_tasks()
        return True
    elif command.startswith("untouch long"):
        helper_tasks.untouch_long_date(user_message)
        subprocess.call("reset")
        helper_tasks.print_tasks()
        return True
    elif command.startswith("add task"):
        add_todoist_task(api, user_message)
        return True

    return False

module_call_counter.apply_call_counter_to_all(globals(), __name__)