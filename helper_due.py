import calendar
import uuid
from datetime import date, datetime
import re
from typing import Optional

import pytz
from dateutil.parser import parse
import recurring_due_deferrals
import todoist_compat
from long_term_recurring_validation import get_due_key, has_starting_anchor_due_string, verify_recurring_due_advanced


LONDON_TZ = pytz.timezone("Europe/London")

_STARTING_ANCHOR_RE = re.compile(r"\s+starting\s+\d{4}-\d{2}-\d{2}\b", flags=re.IGNORECASE)


def _extract_date_from_due(due_obj) -> Optional[date]:
    if due_obj is None:
        return None

    due_value = getattr(due_obj, "datetime", None) or getattr(due_obj, "date", None)
    if due_value is None:
        return None

    if isinstance(due_value, datetime):
        return due_value.date()
    if isinstance(due_value, date):
        return due_value
    if isinstance(due_value, str):
        try:
            if "T" in due_value:
                return parse(due_value).date()
            return parse(due_value).date()
        except Exception:
            return None

    return None


def _timezone_or_london(tz_name: Optional[str]):
    if not tz_name:
        return LONDON_TZ
    try:
        return pytz.timezone(tz_name)
    except Exception:
        return LONDON_TZ


def _parse_due_datetime(due_obj) -> Optional[datetime]:
    if due_obj is None:
        return None

    due_value = getattr(due_obj, "datetime", None)
    if due_value is None:
        due_value = getattr(due_obj, "date", None)
    if due_value is None:
        return None

    parsed_dt: Optional[datetime] = None
    if isinstance(due_value, datetime):
        parsed_dt = due_value
    elif isinstance(due_value, str):
        try:
            if "T" not in due_value:
                return None
            parsed_dt = parse(due_value)
        except Exception:
            return None
    else:
        return None

    if parsed_dt.tzinfo is not None and parsed_dt.tzinfo.utcoffset(parsed_dt) is not None:
        return parsed_dt

    tz = _timezone_or_london(getattr(due_obj, "timezone", None))
    return tz.localize(parsed_dt)


def _next_valid_date_for_day(day_num: int, current_date: date) -> date:
    year = current_date.year
    month = current_date.month
    if day_num < current_date.day:
        month += 1
        if month > 12:
            month = 1
            year += 1

    for _ in range(24):
        max_day = calendar.monthrange(year, month)[1]
        if day_num <= max_day:
            return date(year, month, day_num)
        month += 1
        if month > 12:
            month = 1
            year += 1

    raise ValueError(f"Could not resolve a valid future date for day '{day_num}'.")


def normalize_due_input(raw_due_input: str, now_london: Optional[datetime] = None) -> str:
    due_input = (raw_due_input or "").strip()
    if not due_input:
        raise ValueError("No due text provided.")

    if due_input.isdigit():
        day_num = int(due_input)
        if 1 <= day_num <= 31:
            now_dt = now_london or datetime.now(LONDON_TZ)
            target_date = _next_valid_date_for_day(day_num, now_dt.date())
            return target_date.isoformat()

    return due_input


def resolve_due_input_to_date(api, raw_due_input: str, project_id: Optional[str] = None) -> date:
    normalized_due_input = normalize_due_input(raw_due_input)

    try:
        return date.fromisoformat(normalized_due_input)
    except ValueError:
        pass

    probe_task = None
    probe_content = f"__due_probe__{uuid.uuid4().hex[:12]}"
    add_kwargs = {"content": probe_content, "due_string": normalized_due_input}
    if project_id:
        add_kwargs["project_id"] = project_id

    try:
        probe_task = api.add_task(**add_kwargs)
        resolved_date = _extract_date_from_due(getattr(probe_task, "due", None))
        if resolved_date is None:
            raise ValueError(f"Todoist could not resolve due text '{normalized_due_input}'.")
        return resolved_date
    except Exception as exc:
        raise ValueError(f"Invalid or unsupported due text '{raw_due_input}': {exc}") from exc
    finally:
        if probe_task is not None and getattr(probe_task, "id", None):
            try:
                api.delete_task(task_id=probe_task.id)
            except Exception:
                pass


def _build_due_update_payload(task, target_date: date) -> dict:
    due_obj = getattr(task, "due", None)
    parsed_dt = _parse_due_datetime(due_obj)
    if parsed_dt is None:
        return {"due_date": target_date}

    tz = _timezone_or_london(getattr(due_obj, "timezone", None))
    local_dt = parsed_dt.astimezone(tz)
    naive_target = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        local_dt.hour,
        local_dt.minute,
        local_dt.second,
        local_dt.microsecond,
    )
    try:
        target_local_dt = tz.localize(naive_target, is_dst=None)
    except Exception:
        target_local_dt = tz.localize(naive_target)
    return {"due_datetime": target_local_dt}

def _strip_starting_anchors(due_string: str) -> str:
    if not isinstance(due_string, str):
        return ""
    return _STARTING_ANCHOR_RE.sub("", due_string).strip()


def _build_recovery_due_candidates(original_due_string: str) -> list[str]:
    cleaned_due_string = _strip_starting_anchors(original_due_string)
    if not cleaned_due_string:
        return []
    return [cleaned_due_string]


def extract_due_date(task) -> Optional[date]:
    if task is None:
        return None
    return _extract_date_from_due(getattr(task, "due", None))


def _normalize_recurring_rule_if_needed(api, task, original_due_string: str | None):
    if task is None or not getattr(task, "id", None):
        return task
    if not has_starting_anchor_due_string(original_due_string):
        return task

    cleaned_due_string = _strip_starting_anchors(original_due_string or "")
    if not cleaned_due_string:
        raise RuntimeError("Recurring task has an invalid anchored rule and could not be normalized.")

    api.update_task(task_id=task.id, due_string=cleaned_due_string)
    normalized_task = api.get_task(task.id)
    if normalized_task is None:
        raise RuntimeError("Todoist did not return task data after recurrence normalization.")
    normalized_due = getattr(normalized_task, "due", None)
    if not (normalized_due and getattr(normalized_due, "is_recurring", False)):
        raise RuntimeError("Recurring task lost recurrence during normalization.")
    return normalized_task


def _pull_recurring_task_earlier_in_place(api, task, target_date: date):
    due = getattr(task, "due", None)
    due_string = getattr(due, "string", None) if due is not None else None
    if not isinstance(due_string, str) or not due_string.strip():
        raise RuntimeError("Recurring task is missing its recurrence rule and could not be moved earlier safely.")

    update_payload = _build_due_update_payload(task, target_date)
    api.update_task(task_id=task.id, due_string=due_string, **update_payload)
    refreshed_task = api.get_task(task.id)
    if refreshed_task is None:
        raise RuntimeError("Todoist did not return task data after recurring due update.")

    refreshed_due = getattr(refreshed_task, "due", None)
    if not (refreshed_due and getattr(refreshed_due, "is_recurring", False)):
        raise RuntimeError("Recurring task lost recurrence during due update.")

    refreshed_date = extract_due_date(refreshed_task)
    if refreshed_date != target_date:
        raise RuntimeError(
            f"Recurring due update mismatch after update (expected {target_date.isoformat()}, got {refreshed_date})."
        )

    recurring_due_deferrals.clear_recurring_due_deferral(str(refreshed_task.id))
    return refreshed_task, refreshed_date


def _advance_recurring_task_until_future_boundary(api, task, target_date: date, today_london: date):
    current_task = task
    current_date = extract_due_date(current_task)
    if current_date is None:
        raise RuntimeError("Recurring task is missing a resolvable due date.")
    if current_date >= target_date:
        return current_task, current_date

    max_advances = 64
    advance_count = 0
    while current_date < target_date and current_date <= today_london:
        if advance_count >= max_advances:
            return current_task, current_date

        previous_due_key = get_due_key(current_task)
        if not previous_due_key:
            raise RuntimeError("Recurring task is missing a due key and could not be advanced safely.")

        success = todoist_compat.complete_task(api, current_task.id)
        if not success:
            raise RuntimeError("Todoist did not confirm recurring task completion while advancing due date.")

        advanced_task = verify_recurring_due_advanced(api, current_task.id, previous_due_key)
        if advanced_task is None:
            raise RuntimeError("Todoist did not return the next recurring occurrence after completion.")

        advanced_due_key = get_due_key(advanced_task)
        if advanced_due_key == previous_due_key:
            raise RuntimeError(
                "Todoist did not advance the recurring task while applying the due change."
            )

        current_task = advanced_task
        current_date = extract_due_date(current_task)
        if current_date is None:
            raise RuntimeError("Recurring task advanced but the new due date could not be resolved.")
        advance_count += 1

    return current_task, current_date


def update_task_due_preserving_schedule(api, task, raw_due_input: str):
    if task is None or not getattr(task, "id", None):
        raise ValueError("Task is missing or invalid.")

    original_due = getattr(task, "due", None)
    original_is_recurring = bool(original_due and getattr(original_due, "is_recurring", False))
    original_due_string = getattr(original_due, "string", None) if original_due else None
    project_id = getattr(task, "project_id", None)

    target_date = resolve_due_input_to_date(api, raw_due_input, project_id=project_id)

    if original_is_recurring:
        normalized_task = _normalize_recurring_rule_if_needed(api, task, original_due_string)
        effective_date = extract_due_date(normalized_task)
        if effective_date is None:
            raise RuntimeError("Recurring task is missing a resolvable due date.")
        today_london = datetime.now(LONDON_TZ).date()
        if target_date == effective_date:
            recurring_due_deferrals.clear_recurring_due_deferral(str(normalized_task.id))
            return normalized_task, target_date, effective_date
        if target_date < effective_date:
            pulled_task, pulled_date = _pull_recurring_task_earlier_in_place(api, normalized_task, target_date)
            return pulled_task, target_date, pulled_date
        advanced_task, effective_date = _advance_recurring_task_until_future_boundary(
            api,
            normalized_task,
            target_date,
            today_london,
        )
        if effective_date >= target_date:
            recurring_due_deferrals.clear_recurring_due_deferral(str(advanced_task.id))
            return advanced_task, target_date, effective_date
        recurring_due_deferrals.set_recurring_due_deferral(str(advanced_task.id), target_date)
        setattr(advanced_task, "deferred_until_date", target_date)
        return advanced_task, target_date, effective_date

    update_payload = _build_due_update_payload(task, target_date)
    api.update_task(task_id=task.id, **update_payload)
    verification_task = api.get_task(task.id)
    if verification_task is None:
        raise RuntimeError("Todoist update returned no task data.")

    verified_date = _extract_date_from_due(getattr(verification_task, "due", None))
    if verified_date != target_date:
        raise RuntimeError(
            f"Due date mismatch after update (expected {target_date.isoformat()}, got {verified_date})."
        )

    return verification_task, target_date, verified_date
