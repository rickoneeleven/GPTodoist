from datetime import date, datetime
import unittest

import pytz

import helper_due


class _Due:
    def __init__(self, *, date=None, datetime_value=None, is_recurring=False, string=None, timezone_name="Europe/London"):
        self.date = date
        self.datetime = datetime_value
        self.is_recurring = is_recurring
        self.string = string
        self.timezone = timezone_name


class _Task:
    def __init__(self, *, task_id="1", content="Task", project_id="proj", due=None):
        self.id = task_id
        self.content = content
        self.project_id = project_id
        self.due = due


class _FakeApi:
    def __init__(self, *, task, probe_due_map=None, drop_recurring_on_datetime_update=False):
        self._task = task
        self._probe_due_map = probe_due_map or {}
        self._drop_recurring_on_datetime_update = drop_recurring_on_datetime_update
        self.probe_created = 0
        self.probe_deleted = 0
        self.last_update_kwargs = None

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
        self.last_update_kwargs = kwargs
        if "due_datetime" in kwargs:
            dt_value = kwargs["due_datetime"]
            is_recurring = False if self._drop_recurring_on_datetime_update else bool(self._task.due.is_recurring)
            self._task.due = _Due(
                datetime_value=dt_value if isinstance(dt_value, str) else dt_value.isoformat(),
                is_recurring=is_recurring,
                string=self._task.due.string,
            )
            return True
        if "due_date" in kwargs:
            d_value = kwargs["due_date"]
            self._task.due = _Due(
                date=d_value if isinstance(d_value, str) else d_value.isoformat(),
                is_recurring=bool(self._task.due.is_recurring),
                string=self._task.due.string,
            )
            return True
        if "due_string" in kwargs:
            due_string = kwargs["due_string"]
            # Treat any 'every ...' update as recurrence restoration and keep the current due value.
            if "every" in str(due_string).lower():
                self._task.due = _Due(
                    date=self._task.due.date,
                    datetime_value=self._task.due.datetime,
                    is_recurring=True,
                    string=due_string,
                )
                return True
            raise ValueError("Bad due_string update")
        raise ValueError("Unsupported update payload")

    def get_task(self, task_id):
        return self._task


class TestHelperDue(unittest.TestCase):
    def test_normalize_due_input_day_of_month_rules(self):
        london_tz = pytz.timezone("Europe/London")
        now = london_tz.localize(datetime(2026, 2, 15, 12, 0, 0))
        self.assertEqual(helper_due.normalize_due_input("21", now), "2026-02-21")
        self.assertEqual(helper_due.normalize_due_input("14", now), "2026-03-14")

    def test_update_task_due_preserves_datetime_and_recurrence(self):
        due = _Due(
            datetime_value="2026-02-15T09:30:00+00:00",
            is_recurring=True,
            string="every day at 9:30",
        )
        task = _Task(task_id="A1", due=due)
        api = _FakeApi(task=task, probe_due_map={"sat": "2026-02-21"})

        updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "sat")

        self.assertEqual(target_date.isoformat(), "2026-02-21")
        self.assertEqual(effective_date, target_date)
        self.assertTrue(updated_task.due.is_recurring)
        self.assertEqual(api.probe_created, 1)
        self.assertEqual(api.probe_deleted, 1)
        self.assertIn("due_datetime", api.last_update_kwargs)
        self.assertIsInstance(api.last_update_kwargs["due_datetime"], datetime)
        self.assertEqual(api.last_update_kwargs["due_datetime"].date(), date(2026, 2, 21))

    def test_update_task_due_uses_datetime_when_due_date_is_datetime(self):
        due = _Due(
            date=datetime(2026, 2, 15, 9, 30, 0),
            is_recurring=False,
            string=None,
        )
        task = _Task(task_id="A1b", due=due)
        api = _FakeApi(task=task, probe_due_map={"sat": "2026-02-21"})

        _updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "sat")

        self.assertEqual(target_date.isoformat(), "2026-02-21")
        self.assertEqual(effective_date, target_date)
        self.assertIn("due_datetime", api.last_update_kwargs)
        self.assertNotIn("due_date", api.last_update_kwargs)
        dt_value = api.last_update_kwargs["due_datetime"]
        self.assertIsInstance(dt_value, datetime)
        self.assertEqual(dt_value.hour, 9)
        self.assertEqual(dt_value.minute, 30)

    def test_update_task_due_recovers_recurrence_if_lost(self):
        due = _Due(
            datetime_value="2026-02-15T09:30:00+00:00",
            is_recurring=True,
            string="every day at 9:30",
        )
        task = _Task(task_id="A2", due=due)
        api = _FakeApi(
            task=task,
            probe_due_map={"sat": "2026-02-21"},
            drop_recurring_on_datetime_update=True,
        )

        updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "sat")

        self.assertEqual(target_date.isoformat(), "2026-02-21")
        self.assertEqual(effective_date, target_date)
        self.assertTrue(updated_task.due.is_recurring)
        self.assertNotIn("starting", str(updated_task.due.string).lower())

    def test_update_task_due_recovery_strips_existing_starting_anchors(self):
        due = _Due(
            datetime_value="2026-02-21T12:00:00+00:00",
            is_recurring=True,
            string="every! 3 months 12:00 starting 2026-02-21 starting 2026-02-22 starting 2026-02-22",
        )
        task = _Task(task_id="A3", due=due)
        api = _FakeApi(
            task=task,
            probe_due_map={"tom": "2026-02-22"},
            drop_recurring_on_datetime_update=True,
        )

        updated_task, target_date, effective_date = helper_due.update_task_due_preserving_schedule(api, task, "tom")

        self.assertEqual(target_date.isoformat(), "2026-02-22")
        self.assertEqual(effective_date, target_date)
        self.assertTrue(updated_task.due.is_recurring)
        self.assertNotIn("starting", str(updated_task.due.string).lower())


if __name__ == "__main__":
    unittest.main()
