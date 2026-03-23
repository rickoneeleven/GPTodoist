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


def _invalid_project_id_base32_error():
    error = HTTPError("400 Client Error")
    error.response = _FakeHttpResponse(
        {
            "error_tag": "INVALID_ARGUMENT_VALUE",
            "error_extra": {
                "argument": "project_id",
                "expected": "Value error, Non-base32 digit found",
            },
        }
    )
    return error


class _FakeApi:
    def __init__(self, *, quick_task, add_task_error_factory=_legacy_project_id_error):
        self.quick_task = quick_task
        self.add_task_error_factory = add_task_error_factory
        self.quick_add_calls = []
        self.update_calls = []

    def add_task(self, **kwargs):
        raise self.add_task_error_factory()

    def add_task_quick(self, text):
        self.quick_add_calls.append(text)
        return self.quick_task

    def update_task(self, *, task_id, **kwargs):
        self.update_calls.append((task_id, kwargs))
        return True


class TestHelperTaskFactory(unittest.TestCase):
    def test_create_task_sets_due_on_create_and_skips_post_update(self):
        created_tasks = []

        class _FakeApiNormal:
            def __init__(self):
                self.update_calls = []

            def add_task(self, **kwargs):
                created_tasks.append(kwargs)
                return SimpleNamespace(id="task-789")

            def update_task(self, *, task_id, **kwargs):
                self.update_calls.append((task_id, kwargs))
                return True

        api = _FakeApiNormal()

        task = helper_task_factory.create_task(
            api=api,
            task_content="Replace sensors p1 11:00 mon",
            task_type="normal",
            options={},
        )

        self.assertIsNotNone(task)
        self.assertEqual(getattr(task, "id", None), "task-789")
        self.assertEqual(len(created_tasks), 1)
        self.assertEqual(created_tasks[0].get("due_string"), "11:00 mon")
        self.assertEqual(created_tasks[0].get("priority"), 4)
        self.assertEqual(api.update_calls, [])

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
        self.assertEqual(api.quick_add_calls, ["Replace sensors p1 11:00 mon #RCP"])
        self.assertEqual(len(api.update_calls), 1)
        task_id, payload = api.update_calls[0]
        self.assertEqual(task_id, "task-456")
        self.assertEqual(payload.get("priority"), 4)
        self.assertNotIn("due_string", payload)

    def test_create_task_fallbacks_to_quick_add_for_invalid_base32_project_id(self):
        api = _FakeApi(
            quick_task=SimpleNamespace(id="task-987"),
            add_task_error_factory=_invalid_project_id_base32_error,
        )

        task = helper_task_factory.create_task(
            api=api,
            task_content="print out eyewear email 09:00 tom",
            task_type="normal",
            options={"project_id": "2294289600", "project_name": "RCP"},
        )

        self.assertIsNotNone(task)
        self.assertEqual(getattr(task, "id", None), "task-987")
        self.assertEqual(api.quick_add_calls, ["print out eyewear email 09:00 tom #RCP"])

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
