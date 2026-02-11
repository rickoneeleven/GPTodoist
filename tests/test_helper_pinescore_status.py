import unittest
from datetime import datetime
from threading import Event

import pytz

import helper_pinescore_status
import helper_todoist_part2


class _Due:
    def __init__(self, *, datetime_localized=None):
        self.datetime_localized = datetime_localized


class _Task:
    def __init__(self, *, due=None, has_time: bool = False):
        self.due = due
        self.has_time = has_time


class _FakeClient:
    def __init__(self, *, state=None):
        self.calls = []
        self.state = dict(state or {})

    def update_state(self, *, token, set_values, unset_keys, updated_by, max_attempts):
        self.calls.append(
            {
                "token": token,
                "set": dict(set_values),
                "unset": list(unset_keys),
                "updated_by": updated_by,
                "max_attempts": max_attempts,
            }
        )
        return type("Resp", (), {"etag": "\"etag\""})()

    def get_state(self, *, token):
        return type("Resp", (), {"etag": "\"etag\"", "state": dict(self.state), "server_time": None})()


class HelperPinescoreStatusTests(unittest.TestCase):
    def test_push_sets_boolean_and_metadata_keys(self):
        tz = pytz.timezone("Europe/London")
        now = tz.localize(datetime(2026, 2, 9, 12, 0, 0))
        future = tz.localize(datetime(2026, 2, 9, 13, 0, 0))
        regular_tasks = [_Task(due=_Due(datetime_localized=future), has_time=True)]

        fake = _FakeClient()
        original_client = helper_pinescore_status.PinescoreDataV1Client
        original_datetime = helper_pinescore_status.datetime

        class _FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return now if tz is not None else now.replace(tzinfo=None)

        try:
            helper_pinescore_status.PinescoreDataV1Client = lambda base_url, timeout_s: fake  # type: ignore[assignment]
            helper_pinescore_status.datetime = _FixedDatetime  # type: ignore[assignment]

            result = helper_pinescore_status.push_tasks_up_to_date_status(
                token="tok",
                regular_tasks=regular_tasks,
                long_tasks_showing_count=0,
                updated_by="gptodoist",
                base_url="https://data.pinescore.com",
                timeout_s=0.1,
            )
        finally:
            helper_pinescore_status.PinescoreDataV1Client = original_client  # type: ignore[assignment]
            helper_pinescore_status.datetime = original_datetime  # type: ignore[assignment]

        self.assertEqual(result.etag, "\"etag\"")
        self.assertEqual(len(fake.calls), 1)
        sent = fake.calls[0]["set"]
        self.assertIs(sent["todo.tasks_up_to_date"], True)
        self.assertEqual(sent["todo.tasks_last_updated_by"], "gptodoist")
        self.assertEqual(sent["todo.long_tasks_showing_count"], 0)

    def test_push_from_live_data_uses_fetched_tasks_and_long_count(self):
        fake_tasks = [_Task(due=_Due(datetime_localized=None), has_time=False)]
        captured = {}
        original_fetch = helper_todoist_part2.fetch_todoist_tasks
        original_count = helper_pinescore_status._count_due_long_tasks_for_status
        original_push = helper_pinescore_status.push_tasks_up_to_date_status

        def _fake_push(
            *,
            token,
            regular_tasks,
            long_tasks_showing_count,
            updated_by,
            base_url,
            timeout_s,
            background_owner_device_id=None,
            background_owner_device_label=None,
        ):
            captured["token"] = token
            captured["regular_tasks"] = regular_tasks
            captured["long_tasks_showing_count"] = long_tasks_showing_count
            captured["updated_by"] = updated_by
            captured["base_url"] = base_url
            captured["timeout_s"] = timeout_s
            captured["background_owner_device_id"] = background_owner_device_id
            captured["background_owner_device_label"] = background_owner_device_label
            status = helper_pinescore_status.compute_tasks_up_to_date_status(
                regular_tasks=regular_tasks,
                long_tasks_showing_count=long_tasks_showing_count,
            )
            return helper_pinescore_status.PinescorePushResult(status=status, etag="\"live\"")

        try:
            helper_todoist_part2.fetch_todoist_tasks = lambda _api: fake_tasks  # type: ignore[assignment]
            helper_pinescore_status._count_due_long_tasks_for_status = lambda *, api, max_count=2: 2  # type: ignore[assignment]
            helper_pinescore_status.push_tasks_up_to_date_status = _fake_push  # type: ignore[assignment]

            result = helper_pinescore_status.push_tasks_up_to_date_status_from_live_data(
                api=object(),
                token="tok",
                updated_by="gptodoist",
                base_url="https://data.pinescore.com",
                timeout_s=1.5,
            )
        finally:
            helper_todoist_part2.fetch_todoist_tasks = original_fetch  # type: ignore[assignment]
            helper_pinescore_status._count_due_long_tasks_for_status = original_count  # type: ignore[assignment]
            helper_pinescore_status.push_tasks_up_to_date_status = original_push  # type: ignore[assignment]

        self.assertEqual(result.etag, "\"live\"")
        self.assertEqual(captured["token"], "tok")
        self.assertEqual(captured["regular_tasks"], fake_tasks)
        self.assertEqual(captured["long_tasks_showing_count"], 2)
        self.assertEqual(captured["updated_by"], "gptodoist")
        self.assertEqual(captured["base_url"], "https://data.pinescore.com")
        self.assertEqual(captured["timeout_s"], 1.5)
        self.assertIsNone(captured["background_owner_device_id"])
        self.assertIsNone(captured["background_owner_device_label"])

    def test_push_from_live_data_raises_when_task_fetch_fails(self):
        original_fetch = helper_todoist_part2.fetch_todoist_tasks
        try:
            helper_todoist_part2.fetch_todoist_tasks = lambda _api: None  # type: ignore[assignment]
            with self.assertRaises(RuntimeError):
                helper_pinescore_status.push_tasks_up_to_date_status_from_live_data(
                    api=object(),
                    token="tok",
                    updated_by="gptodoist",
                )
        finally:
            helper_todoist_part2.fetch_todoist_tasks = original_fetch  # type: ignore[assignment]

    def test_claim_background_push_ownership_sets_expected_keys(self):
        fake = _FakeClient()
        original_client = helper_pinescore_status.PinescoreDataV1Client
        try:
            helper_pinescore_status.PinescoreDataV1Client = lambda base_url, timeout_s: fake  # type: ignore[assignment]
            claimed_id = helper_pinescore_status.claim_background_push_ownership(
                token="tok",
                updated_by="gptodoist",
                base_url="https://data.pinescore.com",
                timeout_s=0.1,
                device_id="dev-abc",
                device_label="work-laptop",
            )
        finally:
            helper_pinescore_status.PinescoreDataV1Client = original_client  # type: ignore[assignment]

        self.assertEqual(claimed_id, "dev-abc")
        self.assertEqual(len(fake.calls), 1)
        sent = fake.calls[0]["set"]
        self.assertEqual(sent[helper_pinescore_status.BACKGROUND_OWNER_DEVICE_ID_KEY], "dev-abc")
        self.assertEqual(sent[helper_pinescore_status.BACKGROUND_OWNER_DEVICE_LABEL_KEY], "work-laptop")
        self.assertIn(helper_pinescore_status.BACKGROUND_OWNER_CLAIMED_AT_KEY, sent)

    def test_get_background_push_gate_requires_owner_match(self):
        fake = _FakeClient(state={helper_pinescore_status.BACKGROUND_OWNER_DEVICE_ID_KEY: "dev-1"})
        original_client = helper_pinescore_status.PinescoreDataV1Client
        try:
            helper_pinescore_status.PinescoreDataV1Client = lambda base_url, timeout_s: fake  # type: ignore[assignment]
            allowed = helper_pinescore_status.get_background_push_gate(
                token="tok",
                local_device_id="dev-1",
                base_url="https://data.pinescore.com",
                timeout_s=0.1,
            )
            blocked = helper_pinescore_status.get_background_push_gate(
                token="tok",
                local_device_id="dev-2",
                base_url="https://data.pinescore.com",
                timeout_s=0.1,
            )
        finally:
            helper_pinescore_status.PinescoreDataV1Client = original_client  # type: ignore[assignment]

        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.reason, "owner_match")
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.reason, "owner_mismatch")
        self.assertEqual(blocked.owner_device_id, "dev-1")

    def test_background_loop_calls_success_and_stops(self):
        stop_event = Event()
        success = []
        original_push_live = helper_pinescore_status.push_tasks_up_to_date_status_from_live_data
        original_gate = helper_pinescore_status.get_background_push_gate

        def _fake_push_live(*, api, token, updated_by, base_url, timeout_s):
            status = helper_pinescore_status.compute_tasks_up_to_date_status(
                regular_tasks=[],
                long_tasks_showing_count=0,
            )
            stop_event.set()
            return helper_pinescore_status.PinescorePushResult(status=status, etag="\"bg\"")

        try:
            helper_pinescore_status.get_background_push_gate = lambda **_kwargs: helper_pinescore_status.BackgroundPushGateResult(  # type: ignore[assignment]
                allowed=True,
                reason="owner_match",
                owner_device_id="dev-1",
            )
            helper_pinescore_status.push_tasks_up_to_date_status_from_live_data = _fake_push_live  # type: ignore[assignment]
            helper_pinescore_status.background_status_push_loop(
                stop_event=stop_event,
                api=object(),
                token="tok",
                updated_by="gptodoist",
                local_device_id="dev-1",
                interval_s=9999.0,
                on_success=lambda pushed: success.append(pushed.etag),
            )
        finally:
            helper_pinescore_status.get_background_push_gate = original_gate  # type: ignore[assignment]
            helper_pinescore_status.push_tasks_up_to_date_status_from_live_data = original_push_live  # type: ignore[assignment]

        self.assertEqual(success, ["\"bg\""])

    def test_background_loop_skips_when_not_owner(self):
        stop_event = Event()
        skipped = []
        original_push_live = helper_pinescore_status.push_tasks_up_to_date_status_from_live_data
        original_gate = helper_pinescore_status.get_background_push_gate

        def _fake_push_live(*, api, token, updated_by, base_url, timeout_s):
            raise AssertionError("push should not run when gate denies ownership")

        try:
            helper_pinescore_status.get_background_push_gate = lambda **_kwargs: helper_pinescore_status.BackgroundPushGateResult(  # type: ignore[assignment]
                allowed=False,
                reason="owner_mismatch",
                owner_device_id="dev-remote",
            )
            helper_pinescore_status.push_tasks_up_to_date_status_from_live_data = _fake_push_live  # type: ignore[assignment]
            helper_pinescore_status.background_status_push_loop(
                stop_event=stop_event,
                api=object(),
                token="tok",
                updated_by="gptodoist",
                local_device_id="dev-local",
                interval_s=9999.0,
                on_skip=lambda gate: (skipped.append(gate.reason), stop_event.set()),
            )
        finally:
            helper_pinescore_status.get_background_push_gate = original_gate  # type: ignore[assignment]
            helper_pinescore_status.push_tasks_up_to_date_status_from_live_data = original_push_live  # type: ignore[assignment]

        self.assertEqual(skipped, ["owner_mismatch"])


if __name__ == "__main__":
    unittest.main()
