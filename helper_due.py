import calendar
import uuid
from datetime import date, datetime
import re
from typing import Optional

import pytz
from dateutil.parser import parse


LONDON_TZ = pytz.timezone("Europe/London")


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
        return None

    parsed_dt: Optional[datetime] = None
    if isinstance(due_value, datetime):
        parsed_dt = due_value
    elif isinstance(due_value, str):
        try:
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


def update_task_due_preserving_schedule(api, task, raw_due_input: str):
    if task is None or not getattr(task, "id", None):
        raise ValueError("Task is missing or invalid.")

    original_due = getattr(task, "due", None)
    original_is_recurring = bool(original_due and getattr(original_due, "is_recurring", False))
    original_due_string = getattr(original_due, "string", None) if original_due else None
    project_id = getattr(task, "project_id", None)

    target_date = resolve_due_input_to_date(api, raw_due_input, project_id=project_id)
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

    if original_is_recurring:
        verification_due = getattr(verification_task, "due", None)
        if not (verification_due and getattr(verification_due, "is_recurring", False)):
            if not original_due_string:
                raise RuntimeError("Recurring metadata changed and could not be recovered.")

            # Todoist recurrence strings can already contain a `starting YYYY-MM-DD` anchor.
            # If we append another one, Todoist often keeps the first anchor, defeating the move.
            # Normalize by removing any existing `starting <iso-date>` clauses, then add exactly one.
            cleaned_due_string = re.sub(
                r"\s+starting\s+\d{4}-\d{2}-\d{2}\b",
                "",
                original_due_string,
                flags=re.IGNORECASE,
            ).strip()
            fallback_due_string = f"{cleaned_due_string} starting {target_date.isoformat()}"
            api.update_task(task_id=task.id, due_string=fallback_due_string)
            verification_task = api.get_task(task.id)
            verification_due = getattr(verification_task, "due", None) if verification_task else None

            if not (verification_due and getattr(verification_due, "is_recurring", False)):
                raise RuntimeError("Recurring metadata changed and recovery failed.")

            recovered_date = _extract_date_from_due(verification_due)
            if recovered_date != target_date:
                raise RuntimeError(
                    f"Recovered recurrence but due date mismatch (expected {target_date.isoformat()}, got {recovered_date})."
                )

    return verification_task, target_date
