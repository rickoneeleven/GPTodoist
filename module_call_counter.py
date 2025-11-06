import json
import os
import inspect
from functools import wraps
import time

json_file = "j_function_calls.json"

if not os.path.exists(json_file):
    call_counts = {}
    call_counts["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(json_file, "w") as f:
        json.dump(call_counts, f, indent=2)


def apply_call_counter_to_all(module_globals, target_module_name):
    """Decorate top-level functions only; never wrap classes or exceptions."""
    for name, obj in module_globals.copy().items():
        # Only wrap plain functions defined in the target module
        if (
            inspect.isfunction(obj)
            and not name.startswith("_")
            and getattr(obj, "__module__", None) == target_module_name
        ):
            module_globals[name] = call_counter_decorator(obj)


def call_counter_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with open(json_file, "r") as f:
            call_counts = json.load(f)

        key = f"{os.path.basename(inspect.getfile(func))}:{func.__name__}"
        call_counts[key] += 1

        timestamp = call_counts.pop("timestamp", None)  # Remove the timestamp

        sorted_call_counts = dict(
            sorted(
                [(k, v) for k, v in call_counts.items() if isinstance(v, int)],
                key=lambda item: item[1],
                reverse=True,
            )
        )

        if timestamp:  # Add the timestamp back
            sorted_call_counts = {"timestamp": timestamp, **sorted_call_counts}

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
