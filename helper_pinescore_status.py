from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytz

from pinescore_data_v1 import PinescoreDataV1Client
from pinescore_tasks_status import TasksUpToDateStatus, compute_tasks_up_to_date_status


@dataclass(frozen=True)
class PinescorePushResult:
    status: TasksUpToDateStatus
    etag: str


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

