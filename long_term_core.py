import re
import pytz
import traceback
from datetime import datetime, date, timedelta, timezone
from dateutil.parser import parse
from rich import print
import todoist_compat


def get_long_term_project_id(api):
    """Get the ID of the 'Long Term Tasks' project, returns None if not found or error occurs."""
    project_name = "Long Term Tasks"
    try:
        projects = todoist_compat.get_all_projects(api)
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
        tasks = todoist_compat.get_tasks_by_project(api, project_id)
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
    if not task:
        return False
    if not getattr(task, "due", None):
        return True

    try:
        london_tz = pytz.timezone("Europe/London")
        now_london = datetime.now(london_tz)

        due_val = getattr(task.due, "datetime", None) or getattr(task.due, "date", None)
        if due_val is None:
            return True

        # String date or datetime from API
        if isinstance(due_val, str):
            try:
                if "T" in due_val:
                    dt = parse(due_val)
                    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                        try:
                            dt_london = london_tz.localize(dt, is_dst=None)
                        except pytz.exceptions.AmbiguousTimeError:
                            dt_london = london_tz.localize(dt, is_dst=True)
                        except pytz.exceptions.NonExistentTimeError:
                            dt_london = london_tz.localize(dt + timedelta(hours=1), is_dst=True)
                    else:
                        dt_london = dt.astimezone(london_tz)
                    return dt_london <= now_london
                else:
                    d = parse(due_val).date()
                    return d <= now_london.date()
            except Exception:
                return False

        # Datetime instance
        if isinstance(due_val, datetime):
            dt = due_val
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                try:
                    dt_london = london_tz.localize(dt, is_dst=None)
                except pytz.exceptions.AmbiguousTimeError:
                    dt_london = london_tz.localize(dt, is_dst=True)
                except pytz.exceptions.NonExistentTimeError:
                    dt_london = london_tz.localize(dt + timedelta(hours=1), is_dst=True)
            else:
                dt_london = dt.astimezone(london_tz)
            return dt_london <= now_london

        # Date instance (all-day tasks)
        if isinstance(due_val, date):
            return due_val <= now_london.date()

        # Fallback: unknown type -> not due
        return False

    except Exception as e:
        print(f"[red]Unexpected error checking due status for task '{getattr(task, 'content', 'N/A')}' (ID: {getattr(task, 'id', 'N/A')}): {e}[/red]")
        traceback.print_exc()
        return False
