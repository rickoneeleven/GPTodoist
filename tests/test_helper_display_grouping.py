import unittest
from datetime import date, datetime

import pytz

import helper_display


class _Due:
    def __init__(self, *, date_value=None, datetime_value=None, datetime_localized=None):
        self.date = date_value
        self.datetime = datetime_value
        self.datetime_localized = datetime_localized


class _Task:
    def __init__(
        self,
        *,
        content="Task",
        due=None,
        priority=1,
        is_recurring_flag=False,
        has_time=False,
        created_at_sortable=None,
        due_string_raw=None,
    ):
        self.content = content
        self.due = due
        self.priority = priority
        self.is_recurring_flag = is_recurring_flag
        self.has_time = has_time
        self.created_at_sortable = created_at_sortable or datetime(2026, 2, 1, 0, 0, 0, tzinfo=pytz.utc)
        self.due_string_raw = due_string_raw


class HelperDisplayGroupingTests(unittest.TestCase):
    def test_grouping_places_tasks_into_expected_buckets(self):
        tz = pytz.timezone("Europe/London")
        today = date(2026, 2, 16)

        overdue_rec = _Task(
            content="overdue recurring",
            is_recurring_flag=True,
            due=_Due(date_value="2026-02-15", datetime_localized=tz.localize(datetime(2026, 2, 15, 9, 0, 0))),
        )
        due_today_one = _Task(
            content="today one-shot",
            is_recurring_flag=False,
            due=_Due(date_value="2026-02-16", datetime_localized=tz.localize(datetime(2026, 2, 16, 9, 0, 0))),
        )
        no_due = _Task(content="no due", due=_Due(datetime_localized=tz.localize(datetime(2026, 2, 16, 9, 0, 0))))

        grouped = helper_display._group_tasks_for_objective([overdue_rec, due_today_one, no_due], today=today)

        self.assertEqual(grouped["Overdue"]["Recurring"], [overdue_rec])
        self.assertEqual(grouped["Due Today"]["One-shot"], [due_today_one])
        self.assertEqual(grouped["No Due Date"]["Tasks"], [no_due])

    def test_sorting_prefers_higher_priority_within_bucket(self):
        tz = pytz.timezone("Europe/London")
        today = date(2026, 2, 16)

        low = _Task(
            content="low",
            priority=1,
            due=_Due(date_value="2026-02-16", datetime_localized=tz.localize(datetime(2026, 2, 16, 9, 0, 0))),
        )
        high = _Task(
            content="high",
            priority=4,
            due=_Due(date_value="2026-02-16", datetime_localized=tz.localize(datetime(2026, 2, 16, 9, 0, 0))),
        )

        grouped = helper_display._group_tasks_for_objective([low, high], today=today)
        self.assertEqual(grouped["Due Today"]["One-shot"], [high, low])


if __name__ == "__main__":
    unittest.main()

