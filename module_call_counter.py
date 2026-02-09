import json
import os
import inspect
from functools import wraps
import time
import threading

json_file = "j_function_calls.json"
_file_lock = threading.Lock()


def _default_counts() -> dict:
    return {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}


def _load_counts_unlocked() -> dict:
    if not os.path.exists(json_file):
        return _default_counts()

    try:
        with open(json_file, "r") as f:
            loaded = json.load(f)
            if isinstance(loaded, dict):
                return loaded
    except Exception:
        pass

    return _default_counts()


def _save_counts_unlocked(call_counts: dict) -> None:
    temp_path = f"{json_file}.tmp"
    with open(temp_path, "w") as f:
        json.dump(call_counts, f, indent=2)
    os.replace(temp_path, json_file)


with _file_lock:
    if not os.path.exists(json_file):
        _save_counts_unlocked(_default_counts())


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
        with _file_lock:
            call_counts = _load_counts_unlocked()

            key = f"{os.path.basename(inspect.getfile(func))}:{func.__name__}"
            call_counts[key] = int(call_counts.get(key, 0)) + 1

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

            _save_counts_unlocked(sorted_call_counts)

        return func(*args, **kwargs)

    key = f"{os.path.basename(inspect.getfile(func))}:{func.__name__}"
    with _file_lock:
        call_counts = _load_counts_unlocked()
        if key not in call_counts:
            call_counts[key] = 0
            _save_counts_unlocked(call_counts)

    return wrapper
