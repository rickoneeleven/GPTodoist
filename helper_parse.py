import re
import module_call_counter


def get_user_input():
    print("You: ", end="")
    user_input = ""
    while True:
        line = input()
        if line == "ignore":
            # Ignore everything above
            user_input = ""
        elif line == "!!":
            # Submit everything above and ignore "!!"
            break
        elif line.endswith("qq"):  # User input ended
            user_input += line[:-2]  # Add the current line without the trailing "qq"
            break
        else:
            user_input += line + "\n"  # Add the current line to user_input
    user_input = user_input.rstrip("\n")
    return user_input


def get_taskname_time_day_as_tuple(
    user_message,
):  # takes two messages before parse, i.e add task, move task
    parts = user_message.lower().split()
    task_name, task_time, task_day = [], None, None
    for part in parts[2:]:
        if re.match(r"\d{2}:\d{2}", part):  # Updated regex to match HH:MM format
            task_time = part
        elif part in ["today", "tomorrow"]:
            task_day = part
        else:
            task_name.append(part)
    return " ".join(task_name), task_time, task_day


module_call_counter.apply_call_counter_to_all(globals(), __name__)
