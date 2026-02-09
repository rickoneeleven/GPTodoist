from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


class PinescoreApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, error_code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


@dataclass(frozen=True)
class PinescoreState:
    etag: str
    state: dict[str, Any]
    server_time: str | None


def _parse_json_bytes(data: bytes) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise PinescoreApiError("Invalid JSON response from data hub") from exc


def _require_non_empty(value: str, *, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _validate_state_keys(keys: Sequence[str]) -> None:
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ValueError("State keys must be non-empty strings")
        if key.startswith("meta."):
            raise ValueError("Clients must not set or unset meta.* keys")


class PinescoreDataV1Client:
    def __init__(
        self,
        *,
        base_url: str = "https://data.pinescore.com",
        urlopen: Callable[..., Any] = urllib.request.urlopen,
        timeout_s: float = 10.0,
    ) -> None:
        _require_non_empty(base_url, name="base_url")
        self._base_url = base_url.rstrip("/")
        self._urlopen = urlopen
        self._timeout_s = float(timeout_s)

    def get_state(self, *, token: str) -> PinescoreState:
        _require_non_empty(token, name="token")

        req = urllib.request.Request(
            url=f"{self._base_url}/v1/state",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with self._urlopen(req, timeout=self._timeout_s) as resp:
                body = resp.read()
                etag = None
                headers = getattr(resp, "headers", None)
                if headers is not None:
                    etag = headers.get("ETag")
                if not etag:
                    raise PinescoreApiError("Missing ETag in data hub response")

                decoded = _parse_json_bytes(body)
                if not isinstance(decoded, Mapping) or decoded.get("ok") is not True:
                    raise PinescoreApiError("Unexpected response envelope from data hub")

                data = decoded.get("data") or {}
                state = (data.get("state") if isinstance(data, Mapping) else None) or {}
                if not isinstance(state, Mapping):
                    raise PinescoreApiError("Unexpected state type from data hub")

                meta = decoded.get("meta") if isinstance(decoded.get("meta"), Mapping) else {}
                server_time = meta.get("server_time") if isinstance(meta, Mapping) else None
                return PinescoreState(etag=str(etag), state=dict(state), server_time=server_time if isinstance(server_time, str) else None)
        except urllib.error.HTTPError as exc:
            raise self._http_error_to_exception(exc) from None
        except urllib.error.URLError as exc:
            raise PinescoreApiError("Network error talking to data hub") from exc

    def patch_state(
        self,
        *,
        token: str,
        etag: str,
        set_values: Mapping[str, Any] | None,
        unset_keys: Sequence[str] | None,
        updated_by: str,
    ) -> PinescoreState:
        _require_non_empty(token, name="token")
        _require_non_empty(etag, name="etag")
        _require_non_empty(updated_by, name="updated_by")

        set_values = dict(set_values or {})
        unset_keys = list(unset_keys or [])

        _validate_state_keys(list(set_values.keys()))
        _validate_state_keys(unset_keys)

        payload = {
            "updated_by": updated_by,
            "set": set_values,
            "unset": unset_keys,
        }

        req = urllib.request.Request(
            url=f"{self._base_url}/v1/state",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "If-Match": etag,
            },
            method="PATCH",
        )

        try:
            with self._urlopen(req, timeout=self._timeout_s) as resp:
                body = resp.read()
                new_etag = None
                headers = getattr(resp, "headers", None)
                if headers is not None:
                    new_etag = headers.get("ETag")
                if not new_etag:
                    raise PinescoreApiError("Missing ETag in data hub response")

                decoded = _parse_json_bytes(body)
                if not isinstance(decoded, Mapping) or decoded.get("ok") is not True:
                    raise PinescoreApiError("Unexpected response envelope from data hub")

                data = decoded.get("data") or {}
                state = (data.get("state") if isinstance(data, Mapping) else None) or {}
                if not isinstance(state, Mapping):
                    raise PinescoreApiError("Unexpected state type from data hub")

                meta = decoded.get("meta") if isinstance(decoded.get("meta"), Mapping) else {}
                server_time = meta.get("server_time") if isinstance(meta, Mapping) else None
                return PinescoreState(etag=str(new_etag), state=dict(state), server_time=server_time if isinstance(server_time, str) else None)
        except urllib.error.HTTPError as exc:
            raise self._http_error_to_exception(exc) from None
        except urllib.error.URLError as exc:
            raise PinescoreApiError("Network error talking to data hub") from exc

    def update_state(
        self,
        *,
        token: str,
        set_values: Mapping[str, Any] | None,
        unset_keys: Sequence[str] | None,
        updated_by: str,
        max_attempts: int = 2,
    ) -> PinescoreState:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        last_error: Exception | None = None
        for _ in range(max_attempts):
            try:
                current = self.get_state(token=token)
                return self.patch_state(
                    token=token,
                    etag=current.etag,
                    set_values=set_values,
                    unset_keys=unset_keys,
                    updated_by=updated_by,
                )
            except PinescoreApiError as exc:
                last_error = exc
                if exc.status_code == 409 or exc.error_code == "ETAG_MISMATCH":
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise PinescoreApiError("Failed to update data hub state for unknown reasons")

    def _http_error_to_exception(self, exc: urllib.error.HTTPError) -> PinescoreApiError:
        status = getattr(exc, "code", None)
        error_code = None
        message = f"HTTP {status} from data hub" if status else "HTTP error from data hub"

        try:
            body = exc.read()
            decoded = _parse_json_bytes(body)
            if isinstance(decoded, Mapping) and decoded.get("ok") is False:
                error = decoded.get("error") if isinstance(decoded.get("error"), Mapping) else {}
                if isinstance(error, Mapping):
                    code_val = error.get("code")
                    msg_val = error.get("message")
                    if isinstance(code_val, str):
                        error_code = code_val
                    if isinstance(msg_val, str) and msg_val.strip():
                        message = msg_val
        except Exception:
            pass

        return PinescoreApiError(message, status_code=status if isinstance(status, int) else None, error_code=error_code)

