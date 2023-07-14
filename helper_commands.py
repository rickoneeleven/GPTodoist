import time, subprocess
import helper_todoist, module_call_counter, helper_tasks, module_weather, helper_code, helper_parse, helper_general
import helper_messages, module_bell_ring


def ifelse_commands(api, user_message):
    command = user_message.lower()
    if command == "done":
        subprocess.call('reset')
        helper_todoist.complete_active_todoist_task(api)
        return True
    elif command == "replay":
        subprocess.call('reset')
        helper_messages.print_conversation_history()
        return True
    elif command.startswith("time"):
        helper_todoist.update_task_due_date(api, user_message, False)
        return True
    elif command == "delete":
        helper_todoist.delete_todoist_task(api)
        return True
    elif command == "ring":
        module_bell_ring.ring()
        return True
    elif command == "all" or command == "show all":
        helper_todoist.display_todoist_tasks(api)
        return True
    elif command == "clear":
        subprocess.call('reset')
        return True
    elif command == "flip":
        helper_todoist.change_active_task()
        return True
    elif command == "weather":
        # module_weather.today_old()
        module_weather.pretty_print_weather_data()
        return True
    elif command.startswith("add long"):
        helper_tasks.add_long_term_task(user_message)
        subprocess.call('reset')
        helper_tasks.print_tasks()
        return True
    elif command.startswith("show long"):
        subprocess.call('reset')
        helper_tasks.print_tasks()
        return True
    elif command.startswith("rename long"):
        helper_tasks.rename_long_task(user_message)
        return True
    elif command.startswith("delete long"):
        helper_tasks.delete_long_task(user_message)
        subprocess.call('reset')
        helper_tasks.print_tasks()
        return True
    elif command.startswith("delete conv"):
        helper_messages.delete_conversation(user_message)
        print("clearning console....")
        time.sleep(3)
        subprocess.call('reset')
        helper_messages.show_saved_conversations()
        return True
    elif command.startswith("load conv"):
        helper_messages.load_conversation(user_message)
        return True
    elif command.startswith("add file"):
        helper_code.add_file(user_message)
        return True
    elif command == "reset":
        subprocess.call('reset')
        helper_code.reset_all()
        return True
    elif command == "fresh":
        subprocess.call('reset')
        helper_code.fresh_session()
        return True
    elif command == "commands":
        helper_general.print_commands()
        return True
    elif command.startswith("save"):
        helper_messages.save_conversation(user_message)
        print("clearning console....")
        time.sleep(3)
        subprocess.call('reset')
        helper_code.reset_all()
        return True
    elif command == "show conv":
        helper_messages.show_saved_conversations()
        return True

    elif command.startswith("add task"):
        task_data = helper_parse.get_taskname_time_day_as_tuple(user_message)
        if task_data:
            task_name, task_time, task_day = task_data
            task = helper_todoist.add_todoist_task(api, task_name, task_time, task_day)
            if task:
                print(f"Task '{task.content}' successfully added.")
            else:
                print("Failed to add task.")
        return True

    return False


module_call_counter.apply_call_counter_to_all(globals(), __name__)
