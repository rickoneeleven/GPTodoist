import json
import unittest
from io import BytesIO
from types import SimpleNamespace
from urllib.error import HTTPError

from pinescore_data_v1 import PinescoreApiError, PinescoreDataV1Client


class _FakeResponse:
    def __init__(self, *, body: dict, headers: dict[str, str]):
        self.headers = headers
        self._raw = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class PinescoreDataV1ClientTests(unittest.TestCase):
    def test_get_state_extracts_etag_and_state(self):
        def urlopen(req, timeout):
            self.assertEqual(req.get_method(), "GET")
            self.assertTrue(req.full_url.endswith("/v1/state"))
            headers = {k.lower(): v for k, v in req.header_items()}
            self.assertIn("authorization", headers)
            return _FakeResponse(
                body={"ok": True, "data": {"state": {"a": 1}}, "meta": {"etag": "\"x\"", "server_time": "2026-02-09T13:18:40Z"}},
                headers={"ETag": "\"x\""},
            )

        client = PinescoreDataV1Client(base_url="https://data.pinescore.com", urlopen=urlopen, timeout_s=1)
        resp = client.get_state(token="tok")
        self.assertEqual(resp.etag, "\"x\"")
        self.assertEqual(resp.state["a"], 1)

    def test_patch_state_sends_if_match_and_payload(self):
        captured = SimpleNamespace(req=None)

        def urlopen(req, timeout):
            captured.req = req
            return _FakeResponse(
                body={"ok": True, "data": {"state": {"todo.tasks_up_to_date": True}}, "meta": {"etag": "\"y\"", "server_time": "2026-02-09T13:18:40Z"}},
                headers={"ETag": "\"y\""},
            )

        client = PinescoreDataV1Client(base_url="https://data.pinescore.com", urlopen=urlopen, timeout_s=1)
        resp = client.patch_state(
            token="tok",
            etag="\"x\"",
            set_values={"todo.tasks_up_to_date": True},
            unset_keys=[],
            updated_by="gptodoist",
        )

        self.assertEqual(resp.etag, "\"y\"")
        req = captured.req
        self.assertEqual(req.get_method(), "PATCH")
        headers = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(headers.get("if-match"), "\"x\"")
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["updated_by"], "gptodoist")
        self.assertEqual(payload["set"]["todo.tasks_up_to_date"], True)

    def test_update_state_retries_on_etag_mismatch(self):
        calls = {"get": 0, "patch": 0}

        def urlopen(req, timeout):
            if req.get_method() == "GET":
                calls["get"] += 1
                return _FakeResponse(body={"ok": True, "data": {"state": {}}, "meta": {"etag": "\"x\""}}, headers={"ETag": "\"x\""})

            calls["patch"] += 1
            if calls["patch"] == 1:
                fp = BytesIO(b'{"ok": false, "error": {"code": "ETAG_MISMATCH", "message": "etag mismatch"}}')
                raise HTTPError(req.full_url, 409, "Conflict", hdrs={}, fp=fp)

            return _FakeResponse(body={"ok": True, "data": {"state": {"k": 1}}, "meta": {"etag": "\"z\""}}, headers={"ETag": "\"z\""})

        client = PinescoreDataV1Client(base_url="https://data.pinescore.com", urlopen=urlopen, timeout_s=1)
        resp = client.update_state(token="tok", set_values={"k": 1}, unset_keys=[], updated_by="gptodoist", max_attempts=2)
        self.assertEqual(resp.state["k"], 1)
        self.assertEqual(calls["patch"], 2)

    def test_rejects_meta_keys(self):
        client = PinescoreDataV1Client(base_url="https://data.pinescore.com", urlopen=lambda *_args, **_kw: None, timeout_s=1)
        with self.assertRaises(ValueError):
            client.patch_state(token="tok", etag="\"x\"", set_values={"meta.updated_by": "x"}, unset_keys=[], updated_by="gptodoist")

        with self.assertRaises(ValueError):
            client.patch_state(token="tok", etag="\"x\"", set_values={}, unset_keys=["meta.updated_at"], updated_by="gptodoist")


if __name__ == "__main__":
    unittest.main()
