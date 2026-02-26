from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

import os
import requests


@dataclass
class Due:
    date: Optional[str] = None
    datetime: Optional[str] = None
    timezone: Optional[str] = None
    string: Optional[str] = None
    lang: Optional[str] = None
    is_recurring: bool = False


@dataclass
class Task:
    id: str
    content: str
    description: Optional[str] = None
    project_id: Optional[str] = None
    section_id: Optional[str] = None
    parent_id: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    priority: int = 1
    due: Optional[Due] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    checked: Optional[bool] = None


@dataclass
class Project:
    id: str
    name: str


def _coerce_due(due: Any) -> Optional[Due]:
    if due is None:
        return None
    if isinstance(due, Due):
        return due
    if isinstance(due, dict):
        return Due(
            date=due.get("date"),
            datetime=due.get("datetime"),
            timezone=due.get("timezone"),
            string=due.get("string"),
            lang=due.get("lang"),
            is_recurring=bool(due.get("is_recurring", False)),
        )
    return None


def _coerce_task(payload: Dict[str, Any]) -> Task:
    due = _coerce_due(payload.get("due"))
    return Task(
        id=str(payload.get("id")),
        content=payload.get("content") or "",
        description=payload.get("description"),
        project_id=payload.get("project_id"),
        section_id=payload.get("section_id"),
        parent_id=payload.get("parent_id"),
        labels=list(payload.get("labels") or []),
        priority=int(payload.get("priority") or 1),
        due=due,
        created_at=payload.get("added_at") or payload.get("created_at"),
        updated_at=payload.get("updated_at"),
        checked=payload.get("checked"),
    )


def _coerce_project(payload: Dict[str, Any]) -> Project:
    return Project(id=str(payload.get("id")), name=payload.get("name") or "")


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


class TodoistAPI:
    """
    Minimal Todoist API client for GPTodoist.

    Note: Todoist deprecated the old REST v2 base path. This client uses the
    currently-supported `/api/v1/*` endpoints.
    """

    def __init__(
        self,
        token: str,
        *,
        timeout_seconds: float = 15.0,
        filter_lang: str | None = None,
    ) -> None:
        self._token = token
        self._timeout_seconds = timeout_seconds
        self._filter_lang = (filter_lang or os.environ.get("TODOIST_FILTER_LANG") or "en").strip() or "en"
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "GPTodoist",
            }
        )
        self._base_url = "https://api.todoist.com/api/v1"

    def _request(self, method: str, path: str, *, params: Dict[str, Any] | None = None, json: Any = None) -> requests.Response:
        url = f"{self._base_url}{path}"
        response = self._session.request(
            method,
            url,
            params=params,
            json=json,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        return response

    def _paginate(self, path: str, *, params: Dict[str, Any] | None = None) -> Iterable[Dict[str, Any]]:
        cursor: Optional[str] = None
        while True:
            page_params = dict(params or {})
            page_params.setdefault("limit", 200)
            if cursor:
                page_params["cursor"] = cursor
            response = self._request("GET", path, params=page_params)
            data = response.json()
            results = data.get("results")
            if not isinstance(results, list):
                raise ValueError(f"Unexpected Todoist response shape for {path}: {type(results)}")
            for item in results:
                if isinstance(item, dict):
                    yield item
            cursor = data.get("next_cursor")
            if not cursor:
                return

    def get_tasks(self, **kwargs: Any) -> List[Task]:
        if "filter" in kwargs:
            query = kwargs.pop("filter")
            if query is None:
                return []
            return self.filter_tasks(query=str(query), **kwargs)

        params = {k: _jsonable(v) for k, v in kwargs.items() if v is not None}
        return [_coerce_task(item) for item in self._paginate("/tasks", params=params)]

    def filter_tasks(self, *, query: str, lang: str | None = None, **kwargs: Any) -> List[Task]:
        params = {k: _jsonable(v) for k, v in kwargs.items() if v is not None}
        params["query"] = query
        params.setdefault("lang", (lang or self._filter_lang))
        return [_coerce_task(item) for item in self._paginate("/tasks/filter", params=params)]

    def get_task(self, task_id: str) -> Task:
        response = self._request("GET", f"/tasks/{task_id}")
        return _coerce_task(response.json())

    def add_task(self, **kwargs: Any) -> Task:
        payload = {k: _jsonable(v) for k, v in kwargs.items() if v is not None}
        response = self._request("POST", "/tasks", json=payload)
        return _coerce_task(response.json())

    def update_task(self, *, task_id: str, **kwargs: Any) -> Task:
        payload = {k: _jsonable(v) for k, v in kwargs.items() if v is not None}
        response = self._request("POST", f"/tasks/{task_id}", json=payload)
        return _coerce_task(response.json())

    def delete_task(self, *, task_id: str) -> bool:
        self._request("DELETE", f"/tasks/{task_id}")
        return True

    def close_task(self, *, task_id: str) -> bool:
        self._request("POST", f"/tasks/{task_id}/close")
        return True

    def get_projects(self) -> List[Project]:
        return [_coerce_project(item) for item in self._paginate("/projects")]
