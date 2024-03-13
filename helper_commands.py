import subprocess
import helper_todoist, module_call_counter, helper_tasks, helper_parse
import helper_regex


def ifelse_commands(api, user_message):
    command = user_message.lower()
    if command == "done":
        subprocess.call("reset")
        helper_todoist.complete_active_todoist_task(api)
        return True
    elif command.startswith("time"):
        helper_todoist.update_task_due_date(api, user_message)
        return True
    elif command.startswith("graft"):
        helper_todoist.graft(api, user_message)
        return True
    elif command.startswith("~~~"):
        helper_regex.complete_todoist_task_by_title(user_message)
        helper_todoist.display_todoist_tasks(api)
        return True
    elif command == "delete":
        helper_todoist.delete_todoist_task(api)
        return True
    elif command == "all" or command == "show all":
        subprocess.call("reset")
        helper_todoist.display_todoist_tasks(api)
        return True
    elif command == "clear":
        subprocess.call("reset")
        return True
    elif command == "flip":
        subprocess.call("reset")
        helper_todoist.change_active_task()
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
    elif command.startswith("rename"):
        subprocess.call("reset")
        helper_todoist.rename_todoist_task(api, user_message)
        return True
    elif command.startswith("priority"):
        subprocess.call("reset")
        helper_todoist.change_active_task_priority(api, user_message)
        return True
    elif command.startswith("rename long"):
        helper_tasks.rename_long_task(user_message)
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
    elif command.startswith("add task"):
        task_data = helper_parse.get_taskname_time_day_as_tuple(user_message)
        if task_data[0] == "bad time format":
            print("Bad time format, task not added")
            return False  # Or handle it as needed
        elif task_data:
            task_name, task_time, task_day = task_data
            helper_todoist.add_todoist_task(api, task_name, task_time, task_day)
        return True

    return False


module_call_counter.apply_call_counter_to_all(globals(), __name__)
