from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event
from typing import Any
import hashlib
import os
import platform
import uuid

import pytz

from pinescore_data_v1 import PinescoreDataV1Client
from pinescore_tasks_status import TasksUpToDateStatus, compute_tasks_up_to_date_status


@dataclass(frozen=True)
class PinescorePushResult:
    status: TasksUpToDateStatus
    etag: str


@dataclass(frozen=True)
class BackgroundPushGateResult:
    allowed: bool
    reason: str
    owner_device_id: str | None


BACKGROUND_OWNER_DEVICE_ID_KEY = "todo.tasks_background_owner_device_id"
BACKGROUND_OWNER_DEVICE_LABEL_KEY = "todo.tasks_background_owner_device_label"
BACKGROUND_OWNER_CLAIMED_AT_KEY = "todo.tasks_background_owner_claimed_at"


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_local_device_id() -> str:
    override = os.environ.get("PINESCOREDATA_DEVICE_ID")
    if isinstance(override, str) and override.strip():
        return override.strip()

    system_info = [
        platform.node(),
        platform.machine(),
        platform.processor(),
        platform.system(),
        str(uuid.getnode()),
    ]
    normalized = [part.strip() for part in system_info if isinstance(part, str) and part.strip()]
    if not normalized:
        return "unknown-device"
    return hashlib.sha256(":".join(normalized).encode("utf-8")).hexdigest()


def get_local_device_label() -> str:
    override = os.environ.get("PINESCOREDATA_DEVICE_LABEL")
    if isinstance(override, str) and override.strip():
        return override.strip()

    hostname = platform.node()
    if isinstance(hostname, str) and hostname.strip():
        return hostname.strip()
    return "unknown-host"


def _count_due_long_tasks_for_status(*, api: Any, max_count: int = 2) -> int:
    from long_term_indexing import get_next_long_tasks

    tasks = get_next_long_tasks(api, count=max_count)
    if not isinstance(tasks, list):
        return 0
    return len(tasks)


def claim_background_push_ownership(
    *,
    token: str,
    updated_by: str,
    base_url: str = "https://data.pinescore.com",
    timeout_s: float = 3.0,
    device_id: str | None = None,
    device_label: str | None = None,
) -> str:
    claimed_device_id = device_id.strip() if isinstance(device_id, str) and device_id.strip() else get_local_device_id()
    claimed_device_label = (
        device_label.strip() if isinstance(device_label, str) and device_label.strip() else get_local_device_label()
    )

    set_values = {
        BACKGROUND_OWNER_DEVICE_ID_KEY: claimed_device_id,
        BACKGROUND_OWNER_DEVICE_LABEL_KEY: claimed_device_label,
        BACKGROUND_OWNER_CLAIMED_AT_KEY: _iso_utc_now(),
    }

    client = PinescoreDataV1Client(base_url=base_url, timeout_s=timeout_s)
    client.update_state(
        token=token,
        set_values=set_values,
        unset_keys=[],
        updated_by=updated_by,
        max_attempts=2,
    )
    return claimed_device_id


def get_background_push_gate(
    *,
    token: str,
    local_device_id: str,
    base_url: str = "https://data.pinescore.com",
    timeout_s: float = 3.0,
) -> BackgroundPushGateResult:
    normalized_device_id = local_device_id.strip()
    if not normalized_device_id:
        raise ValueError("local_device_id must be a non-empty string")

    client = PinescoreDataV1Client(base_url=base_url, timeout_s=timeout_s)
    state = client.get_state(token=token).state
    owner_raw = state.get(BACKGROUND_OWNER_DEVICE_ID_KEY)
    owner_device_id = owner_raw.strip() if isinstance(owner_raw, str) and owner_raw.strip() else None
    if owner_device_id is None:
        return BackgroundPushGateResult(allowed=False, reason="owner_missing", owner_device_id=None)
    if owner_device_id != normalized_device_id:
        return BackgroundPushGateResult(allowed=False, reason="owner_mismatch", owner_device_id=owner_device_id)
    return BackgroundPushGateResult(allowed=True, reason="owner_match", owner_device_id=owner_device_id)


def push_tasks_up_to_date_status(
    *,
    token: str,
    regular_tasks: list[Any],
    long_tasks_showing_count: int,
    updated_by: str,
    base_url: str = "https://data.pinescore.com",
    timeout_s: float = 3.0,
    background_owner_device_id: str | None = None,
    background_owner_device_label: str | None = None,
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
    if isinstance(background_owner_device_id, str) and background_owner_device_id.strip():
        normalized_owner_id = background_owner_device_id.strip()
        set_values[BACKGROUND_OWNER_DEVICE_ID_KEY] = normalized_owner_id
        set_values[BACKGROUND_OWNER_CLAIMED_AT_KEY] = _iso_utc_now()
        if isinstance(background_owner_device_label, str) and background_owner_device_label.strip():
            set_values[BACKGROUND_OWNER_DEVICE_LABEL_KEY] = background_owner_device_label.strip()

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
    background_owner_device_id: str | None = None,
    background_owner_device_label: str | None = None,
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
        background_owner_device_id=background_owner_device_id,
        background_owner_device_label=background_owner_device_label,
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
    local_device_id: str | None = None,
    on_success: Callable[[PinescorePushResult], None] | None = None,
    on_skip: Callable[[BackgroundPushGateResult], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
) -> None:
    safe_interval_s = max(1.0, float(interval_s))
    resolved_device_id = local_device_id.strip() if isinstance(local_device_id, str) and local_device_id.strip() else get_local_device_id()

    while not stop_event.is_set():
        try:
            gate = get_background_push_gate(
                token=token,
                local_device_id=resolved_device_id,
                base_url=base_url,
                timeout_s=timeout_s,
            )
            if gate.allowed:
                pushed = push_tasks_up_to_date_status_from_live_data(
                    api=api,
                    token=token,
                    updated_by=updated_by,
                    base_url=base_url,
                    timeout_s=timeout_s,
                )
                if on_success is not None:
                    on_success(pushed)
            elif on_skip is not None:
                on_skip(gate)
        except Exception as exc:
            if on_error is not None:
                on_error(exc)

        if stop_event.wait(safe_interval_s):
            break
