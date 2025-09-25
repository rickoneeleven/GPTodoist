import time
from typing import Any, Callable, List

from requests.exceptions import HTTPError


_MAX_ATTEMPTS = 3
_BACKOFF = 0.5
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _flatten_pages(pages: Any) -> List[Any]:
    if pages is None:
        return []
    if isinstance(pages, list):
        return pages
    items: List[Any] = []
    try:
        for page in pages:
            if isinstance(page, list):
                items.extend(page)
            else:
                items.append(page)
        return items
    except TypeError:
        return [pages]


def _should_retry(error: HTTPError) -> bool:
    response = getattr(error, "response", None)
    if response is None:
        return False
    return response.status_code in _RETRYABLE_STATUS


def _retry_delay(error: HTTPError, attempt: int) -> float:
    delay = _BACKOFF * (2 ** (attempt - 1))
    response = getattr(error, "response", None)
    if response is None:
        return delay
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            delay = max(delay, float(retry_after))
        except ValueError:
            pass
    return delay


def _collect_with_retries(fetch_pages: Callable[[], Any]) -> List[Any]:
    attempt = 0
    while True:
        try:
            return _flatten_pages(fetch_pages())
        except HTTPError as error:
            attempt += 1
            if not _should_retry(error) or attempt >= _MAX_ATTEMPTS:
                raise
            time.sleep(_retry_delay(error, attempt))


def get_tasks_by_filter(api, filter_query: str) -> List[Any]:
    if hasattr(api, "filter_tasks"):
        return _collect_with_retries(lambda: api.filter_tasks(query=filter_query))
    return _collect_with_retries(lambda: api.get_tasks(filter=filter_query))


def get_tasks_by_project(api, project_id: str) -> List[Any]:
    return _collect_with_retries(lambda: api.get_tasks(project_id=project_id))


def get_all_projects(api) -> List[Any]:
    return _collect_with_retries(api.get_projects)


def complete_task(api, task_id: str) -> bool:
    if hasattr(api, "close_task"):
        return api.close_task(task_id=task_id)
    return api.complete_task(task_id=task_id)
