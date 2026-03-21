import re
import time as time_module
from typing import Any


_STARTING_ANCHOR_RE = re.compile(r"\bstarting\s+\d{4}-\d{2}-\d{2}\b", flags=re.IGNORECASE)


def get_due_key(task: Any) -> str | None:
    due = getattr(task, "due", None)
    if due is None:
        return None
    key = getattr(due, "datetime", None) or getattr(due, "date", None)
    if key is None:
        return None
    return str(key)


def should_log_due_not_advanced(task: Any) -> bool:
    due_string = getattr(getattr(task, "due", None), "string", None)
    if not isinstance(due_string, str) or not due_string.strip():
        return False
    return bool(_STARTING_ANCHOR_RE.search(due_string))


def has_starting_anchor_due_string(due_string: str | None) -> bool:
    if not isinstance(due_string, str) or not due_string.strip():
        return False
    return bool(_STARTING_ANCHOR_RE.search(due_string))


def build_validation_snapshot(task: Any) -> dict[str, Any]:
    if task is None:
        return {}

    due = getattr(task, "due", None)
    return {
        "task_id": str(getattr(task, "id", "")) or None,
        "checked": getattr(task, "checked", None),
        "updated_at": getattr(task, "updated_at", None),
        "completed_at": getattr(task, "completed_at", None),
        "due_key": get_due_key(task),
        "due_string": getattr(due, "string", None) if due is not None else None,
        "is_recurring": getattr(due, "is_recurring", None) if due is not None else None,
    }


def format_validation_snapshot(snapshot: dict[str, Any]) -> str:
    if not snapshot:
        return "no validation snapshot available"

    parts: list[str] = []
    for key in ("due_key", "checked", "updated_at", "completed_at", "due_string"):
        value = snapshot.get(key)
        if value is None:
            continue
        parts.append(f"{key}={value}")
    return ", ".join(parts) if parts else "no validation fields available"


def verify_recurring_due_advanced(api: Any, task_id: str, previous_due_key: str | None) -> object | None:
    if not previous_due_key:
        return None
    if not hasattr(api, "get_task"):
        return None

    max_wait_s = 8.0
    delay_s = 0.35
    deadline = time_module.monotonic() + max_wait_s
    last_task = None
    while True:
        try:
            last_task = api.get_task(task_id)
        except Exception:
            last_task = None
        else:
            new_key = get_due_key(last_task)
            if new_key and new_key != previous_due_key:
                return last_task

        now = time_module.monotonic()
        if now >= deadline:
            return last_task
        time_module.sleep(min(delay_s, max(0.0, deadline - now)))
        delay_s = min(delay_s * 1.7, 2.0)
