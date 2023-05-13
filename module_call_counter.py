import json
import os
import inspect
from functools import wraps

json_file = "j_function_calls.json"


def apply_call_counter_to_all(module_globals, target_module_name):
    for name, obj in module_globals.copy().items():
        if (
            callable(obj)
            and not name.startswith("_")
            and getattr(obj, "__module__", None) == target_module_name
        ):
            module_globals[name] = call_counter_decorator(obj)


if not os.path.exists(json_file):
    with open(json_file, "w") as f:
        json.dump({}, f, indent=2)


def call_counter_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with open(json_file, "r") as f:
            call_counts = json.load(f)

        key = f"{os.path.basename(inspect.getfile(func))}:{func.__name__}"
        call_counts[key] += 1

        sorted_call_counts = dict(
            sorted(call_counts.items(), key=lambda item: item[1], reverse=True)
        )

        with open(json_file, "w") as f:
            json.dump(sorted_call_counts, f, indent=2)

        return func(*args, **kwargs)

    with open(json_file, "r") as f:
        call_counts = json.load(f)

    key = f"{os.path.basename(inspect.getfile(func))}:{func.__name__}"
    if key not in call_counts:
        call_counts[key] = 0
        with open(json_file, "w") as f:
            json.dump(call_counts, f, indent=2)

    return wrapper
