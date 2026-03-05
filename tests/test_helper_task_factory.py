import unittest
from types import SimpleNamespace

from requests.exceptions import HTTPError

import helper_task_factory


class _FakeHttpResponse:
    def __init__(self, payload, status_code=400):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


def _legacy_project_id_error():
    error = HTTPError("400 Client Error")
    error.response = _FakeHttpResponse({"error_tag": "V1_ID_CANNOT_BE_USED"})
    return error


class _FakeApi:
    def __init__(self, *, quick_task):
        self.quick_task = quick_task
        self.quick_add_calls = []
        self.update_calls = []

    def add_task(self, **kwargs):
        raise _legacy_project_id_error()

    def add_task_quick(self, text):
        self.quick_add_calls.append(text)
        return self.quick_task

    def update_task(self, *, task_id, **kwargs):
        self.update_calls.append((task_id, kwargs))
        return True


class TestHelperTaskFactory(unittest.TestCase):
    def test_create_task_fallbacks_to_quick_add_for_legacy_project_id(self):
        api = _FakeApi(quick_task=SimpleNamespace(id="task-123"))

        task = helper_task_factory.create_task(
            api=api,
            task_content="create BMS VLAN",
            task_type="normal",
            options={"project_id": "2294289600", "project_name": "RCP"},
        )

        self.assertIsNotNone(task)
        self.assertEqual(getattr(task, "id", None), "task-123")
        self.assertEqual(api.quick_add_calls, ["create BMS VLAN #RCP"])
        self.assertEqual(api.update_calls, [])

    def test_create_task_quick_add_fallback_runs_post_create_updates(self):
        api = _FakeApi(quick_task=SimpleNamespace(id="task-456"))

        task = helper_task_factory.create_task(
            api=api,
            task_content="Replace sensors p1 11:00 mon",
            task_type="normal",
            options={"project_id": "2294289600", "project_name": "RCP"},
        )

        self.assertIsNotNone(task)
        self.assertEqual(api.quick_add_calls, ["Replace sensors p1 #RCP"])
        self.assertEqual(len(api.update_calls), 1)
        task_id, payload = api.update_calls[0]
        self.assertEqual(task_id, "task-456")
        self.assertEqual(payload.get("priority"), 4)
        self.assertEqual(payload.get("due_string"), "11:00 mon")

    def test_create_task_quick_add_missing_id_returns_none(self):
        api = _FakeApi(quick_task=SimpleNamespace())

        task = helper_task_factory.create_task(
            api=api,
            task_content="Missing id fallback",
            task_type="normal",
            options={"project_id": "2294289600", "project_name": "RCP"},
        )

        self.assertIsNone(task)
        self.assertEqual(api.quick_add_calls, ["Missing id fallback #RCP"])


if __name__ == "__main__":
    unittest.main()
