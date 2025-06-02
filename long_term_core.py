import re
import pytz
import traceback
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
from rich import print


def get_long_term_project_id(api):
    """Get the ID of the 'Long Term Tasks' project, returns None if not found or error occurs."""
    project_name = "Long Term Tasks"
    try:
        projects = api.get_projects()
        if projects is None:
            print(f"[red]Error: Failed to retrieve projects from Todoist API.[/red]")
            return None

        for project in projects:
            if not hasattr(project, 'name'):
                print(f"[yellow]Warning: Skipping unexpected item in project list (type: {type(project)}): {project}[/yellow]")
                continue

            if project.name == project_name:
                return project.id

        print(f"[yellow]Warning: Project named '{project_name}' not found in Todoist.[/yellow]")
        print(f"[yellow]Long Term Task functionality will be unavailable until the project is created.[/yellow]")
        return None
    except Exception as error:
        print(f"[red]Error accessing or processing Todoist projects: {error}[/red]")
        traceback.print_exc()
        return None


def find_task_by_index(api, project_id, index):
    """Find a task by its index '[index]' in a project."""
    try:
        tasks = api.get_tasks(project_id=project_id)
        if tasks is None:
            print(f"[red]Error retrieving tasks for project ID {project_id}.[/red]")
            return None

        for task in tasks:
            match = re.match(r'\s*\[(\d+)\]', task.content)
            if match:
                try:
                    task_index = int(match.group(1))
                    if task_index == index:
                        return task
                except ValueError:
                    print(f"[yellow]Warning: Found non-integer index in task '{task.content}'. Skipping.[/yellow]")
                    continue

        return None
    except Exception as error:
        print(f"[red]Error searching for task with index [{index}] in project {project_id}: {error}[/red]")
        traceback.print_exc()
        return None


def is_task_recurring(task):
    """Checks if a Todoist task object represents a recurring task."""
    if not task or not task.due:
        return False

    try:
        if hasattr(task.due, 'is_recurring') and task.due.is_recurring:
            return True

        if hasattr(task.due, 'string') and isinstance(task.due.string, str):
            due_string_lower = task.due.string.lower()
            recurrence_patterns = ['every ', 'every!', 'daily', 'weekly', 'monthly', 'yearly']
            if any(pattern in due_string_lower for pattern in recurrence_patterns):
                if 'every day until' in due_string_lower:
                    return False
                return True

        return False
    except Exception as e:
        print(f"[yellow]Warning: Error checking recurrence for task {task.id}: {e}[/yellow]")
        return False


def is_task_due_today_or_earlier(task):
    """
    Checks if a task is due today or earlier, handling timezones and specific times.
    Returns True if due, False otherwise.
    Note: Tasks with no due date are considered "due" to ensure they appear in the list.
    """
    if not task:
        return False

    if not task.due:
        return True

    try:
        london_tz = pytz.timezone("Europe/London")
        now_london = datetime.now(london_tz)

        if task.due.datetime:
            task_due_datetime_london = None
            try:
                raw_dt_str = task.due.datetime
                parsed_dt = parse(raw_dt_str)

                if parsed_dt.tzinfo is None or parsed_dt.tzinfo.utcoffset(parsed_dt) is None:
                    try:
                        task_due_datetime_london = london_tz.localize(parsed_dt, is_dst=None)
                    except (pytz.exceptions.AmbiguousTimeError, pytz.exceptions.NonExistentTimeError) as dst_err:
                        print(f"[yellow]Warning: DST ambiguity/non-existence for task '{task.content}' (ID: {task.id}) due '{raw_dt_str}': {dst_err}. Treating as not due.[/yellow]")
                        return False
                else:
                    task_due_datetime_london = parsed_dt.astimezone(london_tz)

                if task_due_datetime_london:
                    return task_due_datetime_london <= now_london
                else:
                    print(f"[yellow]Warning: Failed to determine valid London due time for task '{task.content}' (ID: {task.id}). Treating as not due.[/yellow]")
                    return False

            except (ValueError, TypeError) as parse_err:
                print(f"[yellow]Warning: Error parsing due datetime '{task.due.datetime}' for task '{task.content}' (ID: {task.id}): {parse_err}. Treating as not due.[/yellow]")
                return False

        elif task.due.date:
            try:
                task_due_date = parse(task.due.date).date()
                return task_due_date <= now_london.date()
            except (ValueError, TypeError) as parse_err:
                print(f"[yellow]Warning: Error parsing due date '{task.due.date}' for task '{task.content}' (ID: {task.id}): {parse_err}. Treating as not due.[/yellow]")
                return False
        else:
            return True

    except Exception as e:
        print(f"[red]Unexpected error checking due status for task '{task.content}' (ID: {task.id}): {e}[/red]")
        traceback.print_exc()
        return False