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
        original_add_anomaly = long_term_operations.state_manager.add_recurring_anomaly_log
        original_suppress = long_term_operations.long_term_recent.suppress_task_id
        original_print = long_term_operations.print
        try:
            long_term_operations.state_manager.add_completed_task_log = (  # type: ignore[assignment]
                lambda entry: calls["log"].append(entry) or True
            )
            long_term_operations.state_manager.add_recurring_anomaly_log = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: True
            )
            long_term_operations.long_term_recent.suppress_task_id = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: None
            )
            long_term_operations.print = lambda *_args, **_kwargs: None  # type: ignore[assignment]

            task = SimpleNamespace(id="123", content="[22] Test recurring")
            result = long_term_operations.handle_recurring_task(FakeApi(), task, skip_logging=False)
        finally:
            long_term_operations.state_manager.add_completed_task_log = original_add_completed_task_log  # type: ignore[assignment]
            long_term_operations.state_manager.add_recurring_anomaly_log = original_add_anomaly  # type: ignore[assignment]
            long_term_operations.long_term_recent.suppress_task_id = original_suppress  # type: ignore[assignment]
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
        original_add_anomaly = long_term_operations.state_manager.add_recurring_anomaly_log
        original_suppress = long_term_operations.long_term_recent.suppress_task_id
        original_print = long_term_operations.print
        try:
            long_term_operations.state_manager.add_completed_task_log = (  # type: ignore[assignment]
                lambda entry: calls["log"].append(entry) or True
            )
            long_term_operations.state_manager.add_recurring_anomaly_log = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: True
            )
            long_term_operations.long_term_recent.suppress_task_id = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: None
            )
            long_term_operations.print = lambda *_args, **_kwargs: None  # type: ignore[assignment]

            task = SimpleNamespace(id="123", content="[22] Test recurring")
            result = long_term_operations.handle_recurring_task(FakeApi(), task, skip_logging=True)
        finally:
            long_term_operations.state_manager.add_completed_task_log = original_add_completed_task_log  # type: ignore[assignment]
            long_term_operations.state_manager.add_recurring_anomaly_log = original_add_anomaly  # type: ignore[assignment]
            long_term_operations.long_term_recent.suppress_task_id = original_suppress  # type: ignore[assignment]
            long_term_operations.print = original_print  # type: ignore[assignment]

        self.assertTrue(result)
        self.assertEqual(calls["log"], [])

    def test_handle_recurring_task_suppresses_when_due_advances(self):
        calls = {"close": [], "suppress": []}

        class FakeApi:
            def close_task(self, task_id: str) -> bool:
                calls["close"].append(task_id)
                return True

            def get_task(self, task_id: str):
                return SimpleNamespace(
                    id=task_id,
                    content="[22] Test recurring",
                    due=SimpleNamespace(
                        datetime="2099-01-01T09:00:00Z",
                        date=None,
                        string="09:00 every! month starting 2000-01-01",
                        is_recurring=True,
                    ),
                )

        original_add_completed_task_log = long_term_operations.state_manager.add_completed_task_log
        original_add_anomaly = long_term_operations.state_manager.add_recurring_anomaly_log
        original_suppress = long_term_operations.long_term_recent.suppress_task_id
        original_print = long_term_operations.print
        try:
            long_term_operations.state_manager.add_completed_task_log = lambda *_args, **_kwargs: True  # type: ignore[assignment]
            long_term_operations.state_manager.add_recurring_anomaly_log = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: True
            )
            long_term_operations.long_term_recent.suppress_task_id = (  # type: ignore[assignment]
                lambda task_id, *_args, **_kwargs: calls["suppress"].append(task_id)
            )
            long_term_operations.print = lambda *_args, **_kwargs: None  # type: ignore[assignment]

            task = SimpleNamespace(
                id="123",
                content="[22] Test recurring",
                due=SimpleNamespace(
                    datetime="2000-01-01T09:00:00Z",
                    date=None,
                    string="09:00 every! month starting 2000-01-01",
                    is_recurring=True,
                ),
            )
            result = long_term_operations.handle_recurring_task(FakeApi(), task, skip_logging=True)
        finally:
            long_term_operations.state_manager.add_completed_task_log = original_add_completed_task_log  # type: ignore[assignment]
            long_term_operations.state_manager.add_recurring_anomaly_log = original_add_anomaly  # type: ignore[assignment]
            long_term_operations.long_term_recent.suppress_task_id = original_suppress  # type: ignore[assignment]
            long_term_operations.print = original_print  # type: ignore[assignment]

        self.assertTrue(result)
        self.assertEqual(calls["close"], ["123"])
        self.assertEqual(calls["suppress"], ["123"])

    def test_handle_recurring_task_logs_validation_evidence_when_due_does_not_advance(self):
        calls = {"anomaly": [], "printed": []}

        class FakeApi:
            def close_task(self, task_id: str) -> bool:
                return True

            def get_task(self, task_id: str):
                return SimpleNamespace(
                    id=task_id,
                    content="[70] hair cuts",
                    checked=False,
                    updated_at="2026-03-16T08:54:25.295283Z",
                    completed_at=None,
                    due=SimpleNamespace(
                        datetime=None,
                        date="2026-03-20",
                        string="every! 8 weeks starting 2026-03-20",
                        is_recurring=True,
                    ),
                )

        original_add_completed_task_log = long_term_operations.state_manager.add_completed_task_log
        original_add_anomaly = long_term_operations.state_manager.add_recurring_anomaly_log
        original_suppress = long_term_operations.long_term_recent.suppress_task_id
        original_print = long_term_operations.print
        try:
            long_term_operations.state_manager.add_completed_task_log = lambda *_args, **_kwargs: True  # type: ignore[assignment]
            long_term_operations.state_manager.add_recurring_anomaly_log = (  # type: ignore[assignment]
                lambda entry: calls["anomaly"].append(entry) or True
            )
            long_term_operations.long_term_recent.suppress_task_id = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: None
            )
            long_term_operations.print = lambda *args, **_kwargs: calls["printed"].append(args[0] if args else "")  # type: ignore[assignment]

            task = SimpleNamespace(
                id="6fm8Qgvx9Wf5RC78",
                content="[70] hair cuts",
                due=SimpleNamespace(
                    datetime=None,
                    date="2026-03-20",
                    string="every! 8 weeks starting 2026-03-20",
                    is_recurring=True,
                ),
            )
            result = long_term_operations.handle_recurring_task(FakeApi(), task, skip_logging=True, source="touch long")
        finally:
            long_term_operations.state_manager.add_completed_task_log = original_add_completed_task_log  # type: ignore[assignment]
            long_term_operations.state_manager.add_recurring_anomaly_log = original_add_anomaly  # type: ignore[assignment]
            long_term_operations.long_term_recent.suppress_task_id = original_suppress  # type: ignore[assignment]
            long_term_operations.print = original_print  # type: ignore[assignment]

        self.assertTrue(result)
        self.assertEqual(len(calls["anomaly"]), 1)
        self.assertEqual(calls["anomaly"][0]["validated_task_checked"], False)
        self.assertEqual(calls["anomaly"][0]["validated_task_updated_at"], "2026-03-16T08:54:25.295283Z")
        self.assertEqual(calls["anomaly"][0]["validated_task_due_string"], "every! 8 weeks starting 2026-03-20")
        self.assertTrue(any("Validation: Todoist still returns" in str(line) for line in calls["printed"]))


if __name__ == "__main__":
    unittest.main()
