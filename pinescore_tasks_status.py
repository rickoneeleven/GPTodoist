from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from dateutil.parser import parse
import pytz


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class TasksUpToDateStatus:
    up_to_date: bool
    computed_at_utc: datetime
    long_tasks_showing_count: int
    regular_tasks_count: int
    next_normal_due_kind: str
    next_normal_due_at_utc: str | None
    next_normal_due_date: str | None
    reason: str
    version: int = 1

    def as_state_patch(self) -> Mapping[str, Any]:
        return {
            "todo.tasks_up_to_date": self.up_to_date,
            "todo.tasks_last_checked_at": _iso_utc(self.computed_at_utc),
            "todo.tasks_up_to_date_reason": self.reason,
            "todo.tasks_status_version": self.version,
            "todo.long_tasks_showing_count": int(self.long_tasks_showing_count),
            "todo.regular_tasks_count": int(self.regular_tasks_count),
            "todo.next_normal_due_kind": self.next_normal_due_kind,
            "todo.next_normal_due_at": self.next_normal_due_at_utc,
            "todo.next_normal_due_date": self.next_normal_due_date,
        }


def compute_tasks_up_to_date_status(
    *,
    regular_tasks: list[Any],
    long_tasks_showing_count: int,
    now_london: datetime | None = None,
) -> TasksUpToDateStatus:
    london_tz = pytz.timezone("Europe/London")
    if now_london is None:
        now_london = datetime.now(london_tz)

    long_ok = int(long_tasks_showing_count) == 0
    regular_count = len(regular_tasks)

    next_due_kind = "none"
    next_due_at_utc: str | None = None
    next_due_date: str | None = None
    normal_ok = False

    if regular_count == 0:
        normal_ok = True
    else:
        task = regular_tasks[0]
        due_obj = getattr(task, "due", None)
        has_time = bool(getattr(task, "has_time", False))

        if due_obj is None:
            next_due_kind = "none"
            normal_ok = False
        elif has_time:
            due_dt = getattr(due_obj, "datetime_localized", None)
            if isinstance(due_dt, datetime) and due_dt.tzinfo is not None and due_dt.tzinfo.utcoffset(due_dt) is not None:
                next_due_kind = "datetime"
                next_due_at_utc = _iso_utc(due_dt)
                normal_ok = due_dt > now_london
            else:
                next_due_kind = "datetime"
                normal_ok = False
        else:
            due_date_raw = getattr(due_obj, "date", None)
            if isinstance(due_date_raw, str) and due_date_raw.strip():
                next_due_kind = "date"
                try:
                    due_d = parse(due_date_raw).date()
                    next_due_date = due_d.isoformat()
                    normal_ok = due_d > now_london.date()
                except Exception:
                    next_due_date = None
                    normal_ok = False
            else:
                next_due_kind = "none"
                normal_ok = False

    up_to_date = bool(long_ok and normal_ok)
    if not long_ok:
        reason = "long_tasks_due"
    elif regular_count == 0:
        reason = "no_regular_tasks"
    elif normal_ok:
        reason = "next_regular_in_future"
    else:
        reason = "regular_due_or_undated"

    return TasksUpToDateStatus(
        up_to_date=up_to_date,
        computed_at_utc=datetime.now(timezone.utc),
        long_tasks_showing_count=int(long_tasks_showing_count),
        regular_tasks_count=int(regular_count),
        next_normal_due_kind=next_due_kind,
        next_normal_due_at_utc=next_due_at_utc,
        next_normal_due_date=next_due_date,
        reason=reason,
    )

