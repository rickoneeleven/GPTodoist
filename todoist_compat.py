from typing import Iterable, List, Any


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


def get_tasks_by_filter(api, filter_query: str) -> List[Any]:
    if hasattr(api, "filter_tasks"):
        return _flatten_pages(api.filter_tasks(query=filter_query))
    return _flatten_pages(api.get_tasks(filter=filter_query))


def get_tasks_by_project(api, project_id: str) -> List[Any]:
    return _flatten_pages(api.get_tasks(project_id=project_id))


def get_all_projects(api) -> List[Any]:
    return _flatten_pages(api.get_projects())


def complete_task(api, task_id: str) -> bool:
    if hasattr(api, "close_task"):
        return api.close_task(task_id=task_id)
    return api.complete_task(task_id=task_id)

