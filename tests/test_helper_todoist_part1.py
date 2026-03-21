import unittest
from types import SimpleNamespace

import helper_todoist_part1
import recurring_due_deferrals
import state_manager
import todoist_compat


class HelperTodoistPart1CompletionTests(unittest.TestCase):
    def test_complete_by_id_disarms_alarm_before_recurring_catch_up(self):
        alarm_calls = []

        class FakeApi:
            def get_task(self, task_id):
                return SimpleNamespace(
                    id=task_id,
                    content="Recurring task",
                    due=SimpleNamespace(
                        date="2026-03-23",
                        datetime=None,
                        string="every! mon,wed,sat",
                        is_recurring=True,
                    ),
                )

        original_signal = helper_todoist_part1.signal.signal
        original_alarm = helper_todoist_part1.signal.alarm
        original_prepare = recurring_due_deferrals.prepare_recurring_task_for_completion
        original_complete = todoist_compat.complete_task
        original_print = helper_todoist_part1.print
        try:
            helper_todoist_part1.signal.signal = lambda *_args, **_kwargs: None  # type: ignore[assignment]
            helper_todoist_part1.signal.alarm = lambda seconds: alarm_calls.append(seconds)  # type: ignore[assignment]

            def _prepare(_api, task, _today):
                self.assertEqual(alarm_calls[-1], 30)
                return task, 2

            recurring_due_deferrals.prepare_recurring_task_for_completion = _prepare  # type: ignore[assignment]
            todoist_compat.complete_task = lambda _api, _task_id: True  # type: ignore[assignment]
            helper_todoist_part1.print = lambda *_args, **_kwargs: None  # type: ignore[assignment]

            result = helper_todoist_part1.complete_todoist_task_by_id(FakeApi(), "abc", skip_logging=True)
        finally:
            helper_todoist_part1.signal.signal = original_signal  # type: ignore[assignment]
            helper_todoist_part1.signal.alarm = original_alarm  # type: ignore[assignment]
            recurring_due_deferrals.prepare_recurring_task_for_completion = original_prepare  # type: ignore[assignment]
            todoist_compat.complete_task = original_complete  # type: ignore[assignment]
            helper_todoist_part1.print = original_print  # type: ignore[assignment]

        self.assertTrue(result)
        self.assertEqual(alarm_calls[:6], [30, 5, 0, 30, 0, 30])
        self.assertEqual(alarm_calls[-1], 0)

    def test_complete_active_disarms_alarm_before_recurring_catch_up(self):
        alarm_calls = []

        class FakeApi:
            def get_task(self, task_id):
                return SimpleNamespace(
                    id=task_id,
                    content="Recurring active task",
                    due=SimpleNamespace(
                        date="2026-03-23",
                        datetime=None,
                        string="every! mon,wed,sat",
                        is_recurring=True,
                    ),
                )

        original_signal = helper_todoist_part1.signal.signal
        original_alarm = helper_todoist_part1.signal.alarm
        original_prepare = recurring_due_deferrals.prepare_recurring_task_for_completion
        original_complete = todoist_compat.complete_task
        original_get_active = state_manager.get_active_task
        original_clear_active = state_manager.clear_active_task
        original_print = helper_todoist_part1.print
        try:
            helper_todoist_part1.signal.signal = lambda *_args, **_kwargs: None  # type: ignore[assignment]
            helper_todoist_part1.signal.alarm = lambda seconds: alarm_calls.append(seconds)  # type: ignore[assignment]

            def _prepare(_api, task, _today):
                self.assertEqual(alarm_calls[-1], 30)
                return task, 1

            recurring_due_deferrals.prepare_recurring_task_for_completion = _prepare  # type: ignore[assignment]
            todoist_compat.complete_task = lambda _api, _task_id: True  # type: ignore[assignment]
            state_manager.get_active_task = lambda: {"task_id": "abc", "task_name": "Recurring active task"}  # type: ignore[assignment]
            state_manager.clear_active_task = lambda: True  # type: ignore[assignment]
            helper_todoist_part1.print = lambda *_args, **_kwargs: None  # type: ignore[assignment]

            result = helper_todoist_part1.complete_active_todoist_task(FakeApi(), skip_logging=True)
        finally:
            helper_todoist_part1.signal.signal = original_signal  # type: ignore[assignment]
            helper_todoist_part1.signal.alarm = original_alarm  # type: ignore[assignment]
            recurring_due_deferrals.prepare_recurring_task_for_completion = original_prepare  # type: ignore[assignment]
            todoist_compat.complete_task = original_complete  # type: ignore[assignment]
            state_manager.get_active_task = original_get_active  # type: ignore[assignment]
            state_manager.clear_active_task = original_clear_active  # type: ignore[assignment]
            helper_todoist_part1.print = original_print  # type: ignore[assignment]

        self.assertTrue(result)
        self.assertEqual(alarm_calls[:5], [5, 0, 30, 0, 5])
        self.assertEqual(alarm_calls[-1], 0)


if __name__ == "__main__":
    unittest.main()
