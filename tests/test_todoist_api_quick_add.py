import unittest

from todoist_api import TodoistAPI


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = []
        self.headers = {}

    def request(self, method, url, params=None, json=None, timeout=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "timeout": timeout,
            }
        )
        if not self._payloads:
            raise AssertionError("No fake payload available for request")
        return _FakeResponse(self._payloads.pop(0))


class TestTodoistApiQuickAdd(unittest.TestCase):
    def test_add_task_quick_uses_tasks_quick_endpoint(self):
        api = TodoistAPI("token-1")
        fake_session = _FakeSession([{"id": "100", "content": "hello"}])
        api._session = fake_session

        task = api.add_task_quick("hello")

        self.assertEqual(task.id, "100")
        self.assertEqual(task.content, "hello")
        self.assertEqual(len(fake_session.calls), 1)
        call = fake_session.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertTrue(call["url"].endswith("/api/v1/tasks/quick"))
        self.assertEqual(call["json"]["text"], "hello")
        self.assertTrue(call["json"]["meta"])
        self.assertTrue(call["json"]["auto_reminder"])

    def test_add_task_quick_accepts_nested_task_payload(self):
        api = TodoistAPI("token-2")
        fake_session = _FakeSession([{"task": {"id": "101", "content": "nested"}}])
        api._session = fake_session

        task = api.add_task_quick("nested")

        self.assertEqual(task.id, "101")
        self.assertEqual(task.content, "nested")

    def test_add_task_quick_fetches_task_when_only_task_id_returned(self):
        api = TodoistAPI("token-3")
        fake_session = _FakeSession(
            [
                {"task_id": "102"},
                {"id": "102", "content": "resolved"},
            ]
        )
        api._session = fake_session

        task = api.add_task_quick("resolved")

        self.assertEqual(task.id, "102")
        self.assertEqual(task.content, "resolved")
        self.assertEqual(len(fake_session.calls), 2)
        self.assertEqual(fake_session.calls[1]["method"], "GET")
        self.assertTrue(fake_session.calls[1]["url"].endswith("/api/v1/tasks/102"))


if __name__ == "__main__":
    unittest.main()
