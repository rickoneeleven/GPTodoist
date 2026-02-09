import unittest
from datetime import datetime

import pytz

import helper_pinescore_status


class _Due:
    def __init__(self, *, datetime_localized=None):
        self.datetime_localized = datetime_localized


class _Task:
    def __init__(self, *, due=None, has_time: bool = False):
        self.due = due
        self.has_time = has_time


class _FakeClient:
    def __init__(self):
        self.calls = []

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


if __name__ == "__main__":
    unittest.main()

