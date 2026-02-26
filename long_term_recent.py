import time
from typing import Dict

_suppressed_task_ids: Dict[str, float] = {}


def suppress_task_id(task_id: str, ttl_seconds: float = 20.0) -> None:
    """Temporarily suppress a task ID from due-long-task views.

    Todoist recurring task completion can be briefly eventually consistent; this avoids showing a
    just-completed recurring task as still-due for a short window.
    """
    if not isinstance(task_id, str) or not task_id.strip():
        return
    try:
        ttl = float(ttl_seconds)
    except (TypeError, ValueError):
        ttl = 20.0
    if ttl <= 0:
        return
    _suppressed_task_ids[task_id] = time.monotonic() + ttl


def is_suppressed(task_id: str) -> bool:
    if not isinstance(task_id, str) or not task_id.strip():
        return False
    expiry = _suppressed_task_ids.get(task_id)
    if expiry is None:
        return False
    if expiry <= time.monotonic():
        _suppressed_task_ids.pop(task_id, None)
        return False
    return True


def prune_expired() -> None:
    now = time.monotonic()
    for task_id, expiry in list(_suppressed_task_ids.items()):
        if expiry <= now:
            _suppressed_task_ids.pop(task_id, None)
