from __future__ import annotations

from requests.exceptions import HTTPError


def describe_todoist_http_error(error: HTTPError) -> str:
    response = getattr(error, "response", None)
    if response is None:
        return f"Todoist API error: {error}"

    status = response.status_code
    url = getattr(response, "url", "")

    if status == 401:
        return "Todoist API error (401 Unauthorized). Check `TODOIST_API_KEY`."
    if status == 403:
        return "Todoist API error (403 Forbidden). Token lacks permission or is blocked."
    if status == 404:
        return "Todoist API error (404 Not Found). Resource no longer exists."
    if status == 410:
        if "/rest/v2/" in url:
            return "Todoist API error (410 Gone). `/rest/v2/*` has been deprecated. GPTodoist must use `/api/v1/*`."
        return "Todoist API error (410 Gone). Endpoint is deprecated."
    if status == 429:
        retry_after = response.headers.get("Retry-After")
        extra = f" Retry after {retry_after}s." if retry_after else ""
        return f"Todoist API rate-limited (429 Too Many Requests).{extra}"

    return f"Todoist API error (HTTP {status})."

