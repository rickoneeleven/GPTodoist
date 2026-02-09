import unittest

import helper_hide
import helper_todoist_part2
import state_manager
import todoist_compat


class FetchTodoistTasksSignalTests(unittest.TestCase):
    def test_fetch_skips_signal_timeout_off_main_thread(self):
        original_get_active_filter_details = state_manager.get_active_filter_details
        original_get_tasks_by_filter = todoist_compat.get_tasks_by_filter
        original_get_hidden_task_ids_for_today = helper_hide.get_hidden_task_ids_for_today
        original_signal_signal = helper_todoist_part2.signal.signal
        original_current_thread = helper_todoist_part2.threading.current_thread
        original_main_thread = helper_todoist_part2.threading.main_thread

        class _ThreadA:
            pass

        class _ThreadB:
            pass

        try:
            state_manager.get_active_filter_details = lambda: ("today", None)  # type: ignore[assignment]
            todoist_compat.get_tasks_by_filter = lambda api, q: []  # type: ignore[assignment]
            helper_hide.get_hidden_task_ids_for_today = lambda: set()  # type: ignore[assignment]
            helper_todoist_part2.threading.current_thread = lambda: _ThreadA()  # type: ignore[assignment]
            helper_todoist_part2.threading.main_thread = lambda: _ThreadB()  # type: ignore[assignment]

            def _fail_if_called(*_args, **_kwargs):
                raise AssertionError("signal.signal must not be called off main thread")

            helper_todoist_part2.signal.signal = _fail_if_called  # type: ignore[assignment]

            result = helper_todoist_part2.fetch_todoist_tasks(api=object())
        finally:
            state_manager.get_active_filter_details = original_get_active_filter_details  # type: ignore[assignment]
            todoist_compat.get_tasks_by_filter = original_get_tasks_by_filter  # type: ignore[assignment]
            helper_hide.get_hidden_task_ids_for_today = original_get_hidden_task_ids_for_today  # type: ignore[assignment]
            helper_todoist_part2.signal.signal = original_signal_signal  # type: ignore[assignment]
            helper_todoist_part2.threading.current_thread = original_current_thread  # type: ignore[assignment]
            helper_todoist_part2.threading.main_thread = original_main_thread  # type: ignore[assignment]

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
