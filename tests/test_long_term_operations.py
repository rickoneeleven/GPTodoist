import unittest
from types import SimpleNamespace

import long_term_operations


class LongTermOperationsTests(unittest.TestCase):
    def test_handle_recurring_task_logs_touched_prefix(self):
        calls = {"close": [], "log": []}

        class FakeApi:
            def close_task(self, task_id: str) -> bool:
                calls["close"].append(task_id)
                return True

        original_add_completed_task_log = long_term_operations.state_manager.add_completed_task_log
        original_print = long_term_operations.print
        try:
            long_term_operations.state_manager.add_completed_task_log = (  # type: ignore[assignment]
                lambda entry: calls["log"].append(entry) or True
            )
            long_term_operations.print = lambda *_args, **_kwargs: None  # type: ignore[assignment]

            task = SimpleNamespace(id="123", content="[22] Test recurring")
            result = long_term_operations.handle_recurring_task(FakeApi(), task, skip_logging=False)
        finally:
            long_term_operations.state_manager.add_completed_task_log = original_add_completed_task_log  # type: ignore[assignment]
            long_term_operations.print = original_print  # type: ignore[assignment]

        self.assertTrue(result)
        self.assertEqual(calls["close"], ["123"])
        self.assertEqual(len(calls["log"]), 1)
        self.assertIn("(Touched Long Task)", calls["log"][0]["task_name"])

    def test_handle_recurring_task_skip_logging_does_not_log(self):
        calls = {"log": []}

        class FakeApi:
            def close_task(self, task_id: str) -> bool:
                return True

        original_add_completed_task_log = long_term_operations.state_manager.add_completed_task_log
        original_print = long_term_operations.print
        try:
            long_term_operations.state_manager.add_completed_task_log = (  # type: ignore[assignment]
                lambda entry: calls["log"].append(entry) or True
            )
            long_term_operations.print = lambda *_args, **_kwargs: None  # type: ignore[assignment]

            task = SimpleNamespace(id="123", content="[22] Test recurring")
            result = long_term_operations.handle_recurring_task(FakeApi(), task, skip_logging=True)
        finally:
            long_term_operations.state_manager.add_completed_task_log = original_add_completed_task_log  # type: ignore[assignment]
            long_term_operations.print = original_print  # type: ignore[assignment]

        self.assertTrue(result)
        self.assertEqual(calls["log"], [])


if __name__ == "__main__":
    unittest.main()
