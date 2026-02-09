import unittest
from datetime import datetime

import pytz

from pinescore_tasks_status import compute_tasks_up_to_date_status


class _Due:
    def __init__(self, *, date: str | None = None, datetime_localized=None):
        self.date = date
        self.datetime_localized = datetime_localized


class _Task:
    def __init__(self, *, due=None, has_time: bool = False):
        self.due = due
        self.has_time = has_time


class TasksUpToDateStatusTests(unittest.TestCase):
    def test_up_to_date_when_no_tasks_and_no_long_tasks(self):
        status = compute_tasks_up_to_date_status(regular_tasks=[], long_tasks_showing_count=0)
        self.assertTrue(status.up_to_date)
        self.assertEqual(status.reason, "no_regular_tasks")

    def test_not_up_to_date_when_long_tasks_showing(self):
        status = compute_tasks_up_to_date_status(regular_tasks=[], long_tasks_showing_count=1)
        self.assertFalse(status.up_to_date)
        self.assertEqual(status.reason, "long_tasks_due")

    def test_up_to_date_when_next_task_due_in_future_datetime(self):
        tz = pytz.timezone("Europe/London")
        now = tz.localize(datetime(2026, 2, 9, 12, 0, 0))
        future = tz.localize(datetime(2026, 2, 9, 13, 0, 0))
        tasks = [_Task(due=_Due(datetime_localized=future), has_time=True)]
        status = compute_tasks_up_to_date_status(regular_tasks=tasks, long_tasks_showing_count=0, now_london=now)
        self.assertTrue(status.up_to_date)
        self.assertEqual(status.reason, "next_regular_in_future")
        self.assertEqual(status.next_normal_due_kind, "datetime")
        self.assertIsNotNone(status.next_normal_due_at_utc)

    def test_up_to_date_when_next_task_due_in_future_date(self):
        tz = pytz.timezone("Europe/London")
        now = tz.localize(datetime(2026, 2, 9, 12, 0, 0))
        tasks = [_Task(due=_Due(date="2026-02-10", datetime_localized=None), has_time=False)]
        status = compute_tasks_up_to_date_status(regular_tasks=tasks, long_tasks_showing_count=0, now_london=now)
        self.assertTrue(status.up_to_date)
        self.assertEqual(status.next_normal_due_kind, "date")
        self.assertEqual(status.next_normal_due_date, "2026-02-10")

    def test_not_up_to_date_when_task_undated(self):
        tasks = [_Task(due=_Due(date=None, datetime_localized=None), has_time=False)]
        status = compute_tasks_up_to_date_status(regular_tasks=tasks, long_tasks_showing_count=0)
        self.assertFalse(status.up_to_date)
        self.assertEqual(status.reason, "regular_due_or_undated")


if __name__ == "__main__":
    unittest.main()

