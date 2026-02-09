from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from threading import Event
from typing import Any

import pytz

from pinescore_data_v1 import PinescoreDataV1Client
from pinescore_tasks_status import TasksUpToDateStatus, compute_tasks_up_to_date_status


@dataclass(frozen=True)
class PinescorePushResult:
    status: TasksUpToDateStatus
    etag: str


def _count_due_long_tasks_for_status(*, api: Any, max_count: int = 2) -> int:
    from long_term_indexing import get_next_long_tasks

    tasks = get_next_long_tasks(api, count=max_count)
    if not isinstance(tasks, list):
        return 0
    return len(tasks)


def push_tasks_up_to_date_status(
    *,
    token: str,
    regular_tasks: list[Any],
    long_tasks_showing_count: int,
    updated_by: str,
    base_url: str = "https://data.pinescore.com",
    timeout_s: float = 3.0,
) -> PinescorePushResult:
    london_tz = pytz.timezone("Europe/London")
    now_london = datetime.now(london_tz)
    status = compute_tasks_up_to_date_status(
        regular_tasks=regular_tasks,
        long_tasks_showing_count=long_tasks_showing_count,
        now_london=now_london,
    )

    set_values = dict(status.as_state_patch())
    set_values["todo.tasks_last_updated_by"] = updated_by

    client = PinescoreDataV1Client(base_url=base_url, timeout_s=timeout_s)
    resp = client.update_state(token=token, set_values=set_values, unset_keys=[], updated_by=updated_by, max_attempts=2)
    return PinescorePushResult(status=status, etag=resp.etag)


def push_tasks_up_to_date_status_from_live_data(
    *,
    api: Any,
    token: str,
    updated_by: str,
    base_url: str = "https://data.pinescore.com",
    timeout_s: float = 3.0,
) -> PinescorePushResult:
    import helper_todoist_part2

    regular_tasks = helper_todoist_part2.fetch_todoist_tasks(api)
    if regular_tasks is None:
        raise RuntimeError("Unable to fetch regular tasks for pinescore status push")

    long_tasks_showing_count = _count_due_long_tasks_for_status(api=api, max_count=2)
    return push_tasks_up_to_date_status(
        token=token,
        regular_tasks=regular_tasks,
        long_tasks_showing_count=long_tasks_showing_count,
        updated_by=updated_by,
        base_url=base_url,
        timeout_s=timeout_s,
    )


def background_status_push_loop(
    *,
    stop_event: Event,
    api: Any,
    token: str,
    updated_by: str,
    base_url: str = "https://data.pinescore.com",
    interval_s: float = 300.0,
    timeout_s: float = 3.0,
    on_success: Callable[[PinescorePushResult], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
) -> None:
    safe_interval_s = max(1.0, float(interval_s))

    while not stop_event.is_set():
        try:
            pushed = push_tasks_up_to_date_status_from_live_data(
                api=api,
                token=token,
                updated_by=updated_by,
                base_url=base_url,
                timeout_s=timeout_s,
            )
            if on_success is not None:
                on_success(pushed)
        except Exception as exc:
            if on_error is not None:
                on_error(exc)

        if stop_event.wait(safe_interval_s):
            break
