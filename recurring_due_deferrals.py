from datetime import date, datetime
from typing import Any

from dateutil.parser import parse

from helper_general import load_json, save_json
from long_term_recurring_validation import get_due_key, verify_recurring_due_advanced
import todoist_compat


RECURRING_DUE_DEFERRALS_FILENAME = "j_recurring_due_deferrals.json"


def _load_deferrals() -> dict[str, str]:
    data = load_json(RECURRING_DUE_DEFERRALS_FILENAME, default_value={})
    return data if isinstance(data, dict) else {}


def _save_deferrals(data: dict[str, str]) -> bool:
    return save_json(RECURRING_DUE_DEFERRALS_FILENAME, data)


def set_recurring_due_deferral(task_id: str, until_date: date) -> bool:
    if not isinstance(task_id, str) or not task_id.strip():
        return False
    if not isinstance(until_date, date):
        return False
    data = _load_deferrals()
    data[task_id] = until_date.isoformat()
    return _save_deferrals(data)


def clear_recurring_due_deferral(task_id: str) -> bool:
    if not isinstance(task_id, str) or not task_id.strip():
        return False
    data = _load_deferrals()
    if task_id in data:
        data.pop(task_id, None)
        return _save_deferrals(data)
    return True


def get_recurring_due_deferral(task_id: str) -> date | None:
    if not isinstance(task_id, str) or not task_id.strip():
        return None
    data = _load_deferrals()
    value = data.get(task_id)
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _extract_due_date(task: Any) -> date | None:
    due = getattr(task, "due", None)
    if due is None:
        return None
    due_value = getattr(due, "datetime", None) or getattr(due, "date", None)
    if due_value is None:
        return None
    if isinstance(due_value, date) and not isinstance(due_value, datetime):
        return due_value
    if isinstance(due_value, datetime):
        return due_value.date()
    if isinstance(due_value, str):
        try:
            return parse(due_value).date()
        except Exception:
            return None
    return None


def _apply_due_override(task: Any, until_date: date) -> None:
    due = getattr(task, "due", None)
    if due is None:
        return

    due_datetime = getattr(due, "datetime", None)
    due_date = getattr(due, "date", None)

    if isinstance(due_datetime, datetime):
        due.datetime = due_datetime.replace(year=until_date.year, month=until_date.month, day=until_date.day)
        return
    if isinstance(due_datetime, str) and "T" in due_datetime:
        parsed = parse(due_datetime)
        due.datetime = parsed.replace(year=until_date.year, month=until_date.month, day=until_date.day).isoformat()
        return
    if isinstance(due_date, datetime):
        due.date = due_date.replace(year=until_date.year, month=until_date.month, day=until_date.day)
        return
    if isinstance(due_date, str) and "T" in due_date:
        parsed = parse(due_date)
        due.date = parsed.replace(year=until_date.year, month=until_date.month, day=until_date.day).isoformat()
        return

    due.date = until_date.isoformat()


def apply_recurring_due_deferral(task: Any, today: date) -> bool:
    task_id = str(getattr(task, "id", "") or "")
    due = getattr(task, "due", None)
    if not task_id or due is None or not getattr(due, "is_recurring", False):
        return True

    deferred_until = get_recurring_due_deferral(task_id)
    if deferred_until is None:
        return True

    actual_due_date = _extract_due_date(task)
    if actual_due_date is None:
        return True

    if deferred_until <= actual_due_date:
        clear_recurring_due_deferral(task_id)
        return True

    if today < deferred_until:
        return False

    _apply_due_override(task, deferred_until)
    return True


def prepare_recurring_task_for_completion(api: Any, task: Any, today: date) -> tuple[Any, int]:
    task_id = str(getattr(task, "id", "") or "")
    if not task_id:
        return task, 0

    deferred_until = get_recurring_due_deferral(task_id)
    if deferred_until is None:
        return task, 0

    if today < deferred_until:
        raise RuntimeError(f"Task is deferred until {deferred_until.isoformat()}.")

    current_task = task
    catch_up_count = 0
    max_advances = 128

    while True:
        actual_due_date = _extract_due_date(current_task)
        if actual_due_date is None or actual_due_date >= deferred_until:
            clear_recurring_due_deferral(task_id)
            return current_task, catch_up_count

        if catch_up_count >= max_advances:
            raise RuntimeError(
                f"Recurring completion exceeded {max_advances} safe advances before reaching deferred date {deferred_until.isoformat()}."
            )

        previous_due_key = get_due_key(current_task)
        if not previous_due_key:
            raise RuntimeError("Recurring task is missing a due key and could not be advanced safely.")

        success = todoist_compat.complete_task(api, task_id)
        if not success:
            raise RuntimeError("Todoist did not confirm recurring task completion while resolving deferred due state.")

        advanced_task = verify_recurring_due_advanced(api, task_id, previous_due_key)
        if advanced_task is None:
            raise RuntimeError("Todoist did not return the next recurring occurrence while resolving deferred due state.")

        advanced_due_key = get_due_key(advanced_task)
        if advanced_due_key == previous_due_key:
            raise RuntimeError("Todoist did not advance the recurring task while resolving deferred due state.")

        current_task = advanced_task
        catch_up_count += 1
