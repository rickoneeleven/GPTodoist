from datetime import date, datetime, timedelta
import unittest

import pytz

import helper_due
import recurring_due_deferrals


class _Due:
    def __init__(self, *, date=None, datetime_value=None, is_recurring=False, string=None, timezone_name="Europe/London"):
        self.date = date
        self.datetime = datetime_value
        self.is_recurring = is_recurring
        self.string = string
        self.timezone = timezone_name


class _Task:
    def __init__(self, *, task_id="1", content="Task", project_id="proj", due=None, priority=1, description=""):
        self.id = task_id
        self.content = content
        self.project_id = project_id
        self.due = due
        self.priority = priority
        self.description = description
        self.checked = False
        self.updated_at = "2026-03-21T00:00:00Z"


class _FakeApi:
    def __init__(self, *, task, probe_due_map=None, due_string_result_map=None, close_sequence=None):
        self._task = task
        self._probe_due_map = probe_due_map or {}
        self._due_string_result_map = due_string_result_map or {}
        self._close_sequence = list(close_sequence or [])
        self.probe_created = 0
        self.probe_deleted = 0
        self.update_calls = []
        self.close_calls = 0

    def add_task(self, **kwargs):
        self.probe_created += 1
        due_text = kwargs.get("due_string")
        if due_text not in self._probe_due_map:
            raise ValueError("Unknown due text")
        resolved = self._probe_due_map[due_text]
        return _Task(task_id="probe", due=_Due(date=resolved))

    def delete_task(self, *, task_id):
        if task_id == "probe":
            self.probe_deleted += 1
        return True

    def update_task(self, *, task_id, **kwargs):
        self.update_calls.append(kwargs)
        if "due_string" in kwargs and ("due_date" in kwargs or "due_datetime" in kwargs):
            due_string = kwargs["due_string"]
            due_date_value = kwargs.get("due_datetime", kwargs.get("due_date"))
            if isinstance(due_date_value, datetime):
                due_value = due_date_value.isoformat()
            elif isinstance(due_date_value, date):
                due_value = due_date_value.isoformat()
            else:
                due_value = due_date_value
            self._task.due = _Due(
                date=due_value,
                is_recurring=True,
                string=due_string,
            )
            return True
        if "due_datetime" in kwargs:
            dt_value = kwargs["due_datetime"]
            self._task.due = _Due(
                datetime_value=dt_value if isinstance(dt_value, str) else dt_value.isoformat(),
                is_recurring=False,
                string=self._task.due.string,
            )
            return True
        if "due_date" in kwargs:
            d_value = kwargs["due_date"]
            self._task.due = _Due(
                date=d_value if isinstance(d_value, str) else d_value.isoformat(),
                is_recurring=False,
                string=self._task.due.string,
            )
            return True
        if "due_string" in kwargs:
            due_string = kwargs["due_string"]
            due_override = self._due_string_result_map.get(due_string)
            if due_override is None:
                raise ValueError("Bad due_string update")

            due_date = due_override
            if isinstance(due_override, tuple):
                due_date, is_recurring = due_override
            else:
                is_recurring = True
            self._task.due = _Due(
                date=due_date,
                is_recurring=is_recurring,
                string=due_string,
            )
            return True
        raise ValueError("Unsupported update payload")

    def get_task(self, task_id):
        return self._task

    def close_task(self, *, task_id):
        self.close_calls += 1
        if not self._close_sequence:
            raise ValueError("No close sequence available")

        next_due_date, next_due_string = self._close_sequence.pop(0)
        self._task.due = _Due(
            date=next_due_date,
            is_recurring=True,
            string=next_due_string,
        )
        return True


class TestHelperDue(unittest.TestCase):
    def tearDown(self):
        for task_id in ("R1", "R2", "R3", "R4", "R5"):
            recurring_due_deferrals.clear_recurring_due_deferral(task_id)

    def test_normalize_due_input_day_of_month_rules(self):
        london_tz = pytz.timezone("Europe/London")
        now = london_tz.localize(datetime(2026, 2, 15, 12, 0, 0))
        self.assertEqual(helper_due.normalize_due_input("21", now), "2026-02-21")
        self.assertEqual(helper_due.normalize_due_input("14", now), "2026-03-14")

    def test_update_task_due_uses_datetime_for_non_recurring_datetime_tasks(self):
        due = _Due(
            datetime_value="2026-02-15T09:30:00+00:00",
            is_recurring=False,
            string=None,
        )
        task = _Task(task_id="A1", due=due)
        api = _FakeApi(task=task, probe_due_map={"sat": "2026-02-21"})

        updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "sat")

        self.assertEqual(target_date.isoformat(), "2026-02-21")
        self.assertEqual(effective_date, target_date)
        self.assertEqual(api.probe_created, 1)
        self.assertEqual(api.probe_deleted, 1)
        self.assertIn("due_datetime", api.update_calls[0])
        self.assertIsInstance(api.update_calls[0]["due_datetime"], datetime)
        self.assertEqual(api.update_calls[0]["due_datetime"].date(), date(2026, 2, 21))
        self.assertEqual(helper_due.extract_due_date(updated_task), date(2026, 2, 21))

    def test_update_task_due_advances_recurring_to_first_valid_occurrence_on_or_after_target(self):
        due = _Due(
            date="2026-03-21",
            is_recurring=True,
            string="every! mon,wed,sat",
        )
        task = _Task(task_id="R1", due=due)
        api = _FakeApi(
            task=task,
            probe_due_map={"next week": "2026-03-23"},
            close_sequence=[("2026-03-23", "every! mon,wed,sat")],
        )

        updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "next week")

        self.assertEqual(target_date.isoformat(), "2026-03-23")
        self.assertEqual(effective_date.isoformat(), "2026-03-23")
        self.assertEqual(api.close_calls, 1)
        self.assertTrue(updated_task.due.is_recurring)
        self.assertEqual(updated_task.due.string, "every! mon,wed,sat")
        self.assertEqual(updated_task.due.date, "2026-03-23")

    def test_update_task_due_pulls_recurring_occurrence_earlier_in_place(self):
        due = _Due(
            datetime_value="2026-03-22T07:30:00",
            is_recurring=True,
            string="every day at 07:30",
        )
        task = _Task(task_id="R2", due=due)
        api = _FakeApi(task=task, probe_due_map={"yesterday": "2026-03-20"})

        updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "yesterday")

        self.assertEqual(target_date.isoformat(), "2026-03-20")
        self.assertEqual(effective_date.isoformat(), "2026-03-20")
        self.assertEqual(api.close_calls, 0)
        self.assertEqual(helper_due.extract_due_date(updated_task), date(2026, 3, 20))
        self.assertEqual(updated_task.due.string, "every day at 07:30")
        self.assertEqual(api.update_calls[0]["due_string"], "every day at 07:30")
        self.assertIn("due_datetime", api.update_calls[0])

    def test_update_task_due_normalizes_anchored_recurring_rules_before_advancing(self):
        due = _Due(
            date="2026-03-20",
            is_recurring=True,
            string="every! 8 weeks starting 2026-03-20",
        )
        task = _Task(task_id="R3", due=due)
        api = _FakeApi(
            task=task,
            probe_due_map={"tomorrow": "2026-03-22"},
            due_string_result_map={"every! 8 weeks": "2026-03-21"},
            close_sequence=[("2026-05-16", "every! 8 weeks")],
        )

        updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "tomorrow")

        self.assertEqual(target_date.isoformat(), "2026-03-22")
        self.assertEqual(effective_date.isoformat(), "2026-05-16")
        self.assertEqual(api.update_calls[0], {"due_string": "every! 8 weeks"})
        self.assertEqual(api.close_calls, 1)
        self.assertNotIn("starting", updated_task.due.string.lower())
        self.assertEqual(updated_task.due.date, "2026-05-16")

    def test_update_task_due_uses_first_safe_occurrence_for_sparse_interval_rules(self):
        due = _Due(
            date="2026-03-21",
            is_recurring=True,
            string="every! 8 weeks",
        )
        task = _Task(task_id="R4", due=due)
        api = _FakeApi(
            task=task,
            probe_due_map={"tomorrow": "2026-03-22"},
            close_sequence=[("2026-05-16", "every! 8 weeks")],
        )

        updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "tomorrow")

        self.assertEqual(target_date.isoformat(), "2026-03-22")
        self.assertEqual(effective_date.isoformat(), "2026-05-16")
        self.assertEqual(api.close_calls, 1)
        self.assertEqual(updated_task.due.string, "every! 8 weeks")

    def test_update_task_due_defers_future_recurring_occurrence_locally_when_todoist_cannot_advance_it_safely(self):
        original_datetime = helper_due.datetime

        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                base = datetime(2026, 3, 21, 12, 0, 0)
                return tz.localize(base) if tz is not None else base

        helper_due.datetime = _FixedDateTime
        try:
            due = _Due(
                date="2026-03-23",
                is_recurring=True,
                string="every! mon,wed,sat",
            )
            task = _Task(task_id="R5", due=due)
            api = _FakeApi(task=task, probe_due_map={"next sat": "2026-03-28"})

            updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "next sat")
        finally:
            helper_due.datetime = original_datetime

        self.assertEqual(target_date.isoformat(), "2026-03-28")
        self.assertEqual(effective_date.isoformat(), "2026-03-23")
        self.assertEqual(api.close_calls, 0)
        self.assertEqual(getattr(updated_task, "deferred_until_date").isoformat(), "2026-03-28")
        self.assertEqual(recurring_due_deferrals.get_recurring_due_deferral("R5").isoformat(), "2026-03-28")

    def test_update_task_due_pulls_sparse_future_recurrence_earlier_in_place(self):
        due = _Due(
            date="2026-05-16",
            is_recurring=True,
            string="every! 8 weeks",
        )
        task = _Task(task_id="R4", due=due)
        api = _FakeApi(
            task=task,
            probe_due_map={"today": "2026-03-21"},
        )

        updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "today")

        self.assertEqual(target_date.isoformat(), "2026-03-21")
        self.assertEqual(effective_date.isoformat(), "2026-03-21")
        self.assertEqual(api.close_calls, 0)
        self.assertEqual(updated_task.due.string, "every! 8 weeks")
        self.assertEqual(helper_due.extract_due_date(updated_task), date(2026, 3, 21))
        self.assertEqual(api.update_calls[0]["due_string"], "every! 8 weeks")
        self.assertEqual(api.update_calls[0]["due_date"], date(2026, 3, 21))

    def test_update_task_due_advances_current_occurrence_once_then_defers_remaining_future_gap(self):
        original_datetime = helper_due.datetime

        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                base = datetime(2026, 3, 21, 12, 0, 0)
                return tz.localize(base) if tz is not None else base

        helper_due.datetime = _FixedDateTime
        try:
            due = _Due(
                date="2026-03-21",
                is_recurring=True,
                string="every! mon,wed,sat",
            )
            task = _Task(task_id="R1", due=due)
            api = _FakeApi(
                task=task,
                probe_due_map={"next sat": "2026-03-28"},
                close_sequence=[("2026-03-23", "every! mon,wed,sat")],
            )

            updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "next sat")
        finally:
            helper_due.datetime = original_datetime

        self.assertEqual(target_date.isoformat(), "2026-03-28")
        self.assertEqual(effective_date.isoformat(), "2026-03-23")
        self.assertEqual(api.close_calls, 1)
        self.assertEqual(getattr(updated_task, "deferred_until_date").isoformat(), "2026-03-28")
        self.assertEqual(recurring_due_deferrals.get_recurring_due_deferral("R1").isoformat(), "2026-03-28")

    def test_prepare_recurring_task_for_completion_catches_up_to_deferred_boundary(self):
        recurring_due_deferrals.set_recurring_due_deferral("R5", date(2026, 3, 28))
        due = _Due(
            date="2026-03-23",
            is_recurring=True,
            string="every! mon,wed,sat",
        )
        task = _Task(task_id="R5", due=due)
        api = _FakeApi(
            task=task,
            close_sequence=[
                ("2026-03-25", "every! mon,wed,sat"),
                ("2026-03-28", "every! mon,wed,sat"),
            ],
        )

        updated_task, catch_up_count = recurring_due_deferrals.prepare_recurring_task_for_completion(
            api,
            task,
            date(2026, 3, 28),
        )

        self.assertEqual(catch_up_count, 2)
        self.assertEqual(updated_task.due.date, "2026-03-28")
        self.assertIsNone(recurring_due_deferrals.get_recurring_due_deferral("R5"))

    def test_prepare_recurring_task_for_completion_blocks_before_deferred_date(self):
        recurring_due_deferrals.set_recurring_due_deferral("R5", date(2026, 3, 28))
        due = _Due(
            date="2026-03-23",
            is_recurring=True,
            string="every! mon,wed,sat",
        )
        task = _Task(task_id="R5", due=due)
        api = _FakeApi(task=task)

        with self.assertRaisesRegex(RuntimeError, "deferred until 2026-03-28"):
            recurring_due_deferrals.prepare_recurring_task_for_completion(
                api,
                task,
                date(2026, 3, 27),
            )

    def test_update_task_due_falls_back_to_local_deferral_after_max_safe_advances(self):
        original_datetime = helper_due.datetime

        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                base = datetime(2026, 3, 21, 12, 0, 0)
                return tz.localize(base) if tz is not None else base

        helper_due.datetime = _FixedDateTime
        try:
            due = _Due(
                date="2026-01-01",
                is_recurring=True,
                string="every day",
            )
            task = _Task(task_id="R4", due=due)
            close_sequence = [
                ((date(2026, 1, 1) + timedelta(days=offset)).isoformat(), "every day")
                for offset in range(1, 65)
            ]
            api = _FakeApi(
                task=task,
                probe_due_map={"next sat": "2026-03-28"},
                close_sequence=close_sequence,
            )

            updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "next sat")
        finally:
            helper_due.datetime = original_datetime

        self.assertEqual(target_date.isoformat(), "2026-03-28")
        self.assertEqual(effective_date.isoformat(), "2026-03-06")
        self.assertEqual(api.close_calls, 64)
        self.assertEqual(getattr(updated_task, "deferred_until_date").isoformat(), "2026-03-28")
        self.assertEqual(recurring_due_deferrals.get_recurring_due_deferral("R4").isoformat(), "2026-03-28")


if __name__ == "__main__":
    unittest.main()
