from rich import print


def update_recurrence_patterns(api):
    updated_count = 0
    error_count = 0
    try:
        import helper_todoist_long
        project_id = helper_todoist_long.get_long_term_project_id(api)
        if not project_id:
            return

        from todoist_compat import get_tasks_by_project
        tasks = get_tasks_by_project(api, project_id)
        if tasks is None:
            print("[yellow]Could not retrieve 'Long Term Tasks'.[/yellow]")
            return

        tasks_to_update = []
        for task in tasks:
            if task.due and hasattr(task.due, "string") and isinstance(task.due.string, str):
                due_string = task.due.string.lower()
                if task.due.is_recurring and "every " in due_string and "every!" not in due_string:
                    tasks_to_update.append(task)

        if not tasks_to_update:
            return

        print(f"[cyan]Found {len(tasks_to_update)} long tasks needing 'every ' -> 'every!'.[/cyan]")
        for task in tasks_to_update:
            try:
                current_due_string = task.due.string
                new_due_string = current_due_string.replace("every ", "every! ")
                if new_due_string == current_due_string:
                    continue

                print(f"  Updating: '{task.content}' ('{current_due_string}' -> '{new_due_string}')")
                update_success = api.update_task(task_id=task.id, due_string=new_due_string)
                if update_success:
                    updated_count += 1
                else:
                    print(f"  [red]API failed updating task ID {task.id}.[/red]")
                    error_count += 1
            except Exception as e:
                print(f"[red]Error updating task '{task.content}': {e}[/red]")
                error_count += 1

        if updated_count > 0 or error_count > 0:
            print(f"[cyan]Recurrence update finished. Updated: {updated_count}, Errors: {error_count}[/cyan]")

    except Exception as e:
        print(f"[red]Unexpected error during recurrence update: {e}[/red]")

