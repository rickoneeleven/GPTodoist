import re
import module_call_counter


def get_taskname_time_day_as_tuple(
    user_message,
):  # takes two messages before parse, i.e add task, move task
    parts = user_message.lower().split()
    task_name, task_time, task_day = [], None, None
    for part in parts[2:]:
        if re.match(r"\d{4}", part):
            task_time = part
        elif part in ["today", "tomorrow"]:
            task_day = part
        else:
            task_name.append(part)
    return " ".join(task_name), task_time, task_day


module_call_counter.apply_call_counter_to_all(globals(), __name__)
