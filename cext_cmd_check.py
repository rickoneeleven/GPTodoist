import os
import helper_todoist, module_call_counter, helper_tasks, module_weather


def ifelse_commands(api, user_message):
    command = user_message.lower()
    if command == ".":
        helper_todoist.get_next_todoist_task(api)
        return True
    elif command == "done":
        os.system("clear")
        helper_todoist.complete_active_todoist_task(api)
        helper_todoist.get_next_todoist_task(api)
        return True
    elif command == "undo":
        helper_todoist.undo_active_todoist_task(api)
        return True
    elif command.startswith("time"):
        helper_todoist.update_task_due_date(api, user_message, False)
        helper_todoist.get_next_todoist_task(api)
        return True
    elif command == "delete":
        helper_todoist.delete_todoist_task(api)
        helper_todoist.get_next_todoist_task(api)
        return True
    elif command == "all":
        helper_todoist.display_todoist_tasks(api)
        return True
    elif command == "clear":
        os.system("clear")
        return True
    elif command == "weather":
        module_weather.today()
        return True
    elif command.startswith("add long"):
        helper_tasks.add_long_term_task(user_message)
        return True
    elif command.startswith("show long"):
        os.system("clear")
        helper_tasks.print_tasks()
        return True
    elif command.startswith("rename long"):
        helper_tasks.rename_long_task(user_message)
        return True
    elif command.startswith("delete long"):
        helper_tasks.delete_long_task(user_message)
        return True
    return False


module_call_counter.apply_call_counter_to_all(globals(), __name__)
