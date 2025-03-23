import module_call_counter
from rich import print
from datetime import datetime, timedelta
import re

def get_long_term_project_id(api):
    """Get the ID of the Long Term Tasks project, or None if it doesn't exist."""
    try:
        projects = api.get_projects()
        for project in projects:
            if project.name == "Long Term Tasks":
                return project.id
        print("[yellow]Long Term Tasks functionality unavailable - please create a project named 'Long Term Tasks'[/yellow]")
        return None
    except Exception as error:
        print(f"[red]Error accessing Todoist projects: {error}[/red]")
        return None
        
def delete_task(api, index):
    """Delete a task with the given index from the Long Term Tasks project.
    
    Args:
        api: Todoist API instance
        index: Index number to delete
        
    Returns:
        Deleted task content or None if failed
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None
        
    try:
        # Get all tasks to find the one with matching index
        tasks = api.get_tasks(project_id=project_id)
        target_task = None
        
        # Find task with matching index
        for task in tasks:
            match = re.match(r'\[(\d+)\]', task.content)
            if match and int(match.group(1)) == index:
                target_task = task
                break
                
        if not target_task:
            print(f"[yellow]No task found with index [{index}][/yellow]")
            return None
            
        # Store task content before deletion
        task_content = target_task.content
        
        # Delete the task
        api.delete_task(task_id=target_task.id)
        
        print(f"[green]Deleted task: {task_content}[/green]")
        return task_content
        
    except Exception as error:
        print(f"[red]Error deleting task: {error}[/red]")
        return None

def reschedule_task(api, index, schedule):
    """Reschedule a task from the Long Term Tasks project with the specified schedule.
    
    Args:
        api: Todoist API instance
        index: Index of the task to reschedule
        schedule: Due date string (in Todoist format)
        
    Returns:
        Updated task object or None if operation failed
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None
        
    try:
        # Get all tasks to find the one with matching index
        tasks = api.get_tasks(project_id=project_id)
        target_task = None
        
        # Find task with matching index
        for task in tasks:
            match = re.match(r'\[(\d+)\]', task.content)
            if match and int(match.group(1)) == index:
                target_task = task
                break
                
        if not target_task:
            print(f"[yellow]No task found with index [{index}][/yellow]")
            return None
            
        # Check if this is a recurring task
        is_recurring = is_task_recurring(target_task)
        if is_recurring:
            response = input("You are trying to change the time of a recurring task, are you sure? y to continue: ")
            if response.lower() != 'y':
                print("User aborted...")
                return None
                
        # Validate the schedule format
        if schedule.isdigit() and len(schedule) == 4:
            print("[red]Bad time format. Please use a format like '09:00', '09:00 tomorrow', etc.[/red]")
            return None
            
        # Update the task with the new due date and preserve description
        updated_task = api.update_task(
            task_id=target_task.id,
            due_string=schedule,
            description=target_task.description
        )
        
        # Verify the update with a small delay for API consistency
        # For recurring tasks, this check isn't as reliable
        if not is_recurring:
            verification_task = api.get_task(target_task.id)
            if verification_task and verification_task.due and verification_task.due.string:
                print(f"[green]Task due date successfully updated to '{schedule}'.[/green]")
            else:
                print(f"[yellow]Task update initiated but couldn't verify immediately. Please check manually.[/yellow]")
        else:
            print(f"[green]Recurring task update initiated. Please verify the change manually.[/green]")
        
        return updated_task
        
    except Exception as error:
        print(f"[red]Error rescheduling task: {error}[/red]")
        return None

def is_task_recurring(task):
    """Check if a task has recurring information.
    
    Args:
        task: Todoist task object
        
    Returns:
        bool: True if the task is recurring, False otherwise
    """
    if task.due and hasattr(task.due, 'is_recurring'):
        return task.due.is_recurring
    elif task.due and hasattr(task.due, 'string'):
        recurrence_patterns = ['every', 'daily', 'weekly', 'monthly', 'yearly']
        return any(pattern in task.due.string.lower() for pattern in recurrence_patterns)
    return False

def is_task_due_today_or_earlier(task):
    """Check if a task is due today or earlier.
    
    Args:
        task: Todoist task object
        
    Returns:
        bool: True if the task is due today or earlier, False otherwise
    """
    # Tasks with no due date should be included (implicitly due now)
    if not task.due or not hasattr(task.due, 'date'):
        return True
    
    try:
        # Get task's due date
        task_due_date = datetime.fromisoformat(task.due.date).date()
        today = datetime.now().date()
        
        # Include if due today or earlier
        return task_due_date <= today
    except (ValueError, AttributeError, TypeError) as e:
        # If there's any error parsing the date, include the task by default
        print(f"[yellow]Warning: Error checking due date for task: {e}[/yellow]")
        return True

def handle_recurring_task(api, task):
    """Complete a recurring task.
    
    Args:
        api: Todoist API instance
        task: Todoist task object
        
    Returns:
        Completed task object or None if failed
    """
    try:
        completed_task = api.close_task(task_id=task.id)
        print(f"[green]Completed recurring task: {task.content}[/green]")
        return completed_task
    except Exception as error:
        print(f"[red]Error completing recurring task: {error}[/red]")
        return None

def handle_non_recurring_task(api, task):
    """Update a non-recurring task's due date to tomorrow.
    
    Args:
        api: Todoist API instance
        task: Todoist task object
        
    Returns:
        Updated task object or None if failed
    """
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        updated_task = api.update_task(
            task_id=task.id,
            due_string=tomorrow
        )
        print(f"[green]Updated task: {task.content}[/green]")
        return updated_task
    except Exception as error:
        print(f"[red]Error updating task due date: {error}[/red]")
        return None
        
def touch_task(api, task_index):
    """Update the timestamp of a task by setting its due date to tomorrow or completing it if recurring.
    
    Args:
        api: Todoist API instance
        task_index: Index of task to touch
        
    Returns:
        Updated or completed task object or None if failed
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None
        
    try:
        # Get all tasks in project
        tasks = api.get_tasks(project_id=project_id)
        
        # Find task with matching index
        target_task = None
        for task in tasks:
            match = re.match(r'\[(\d+)\]', task.content)
            if match and int(match.group(1)) == task_index:
                target_task = task
                break
                
        if not target_task:
            print(f"[yellow]No task found with index {task_index}[/yellow]")
            return None
            
        # Check if task is recurring and handle appropriately
        if is_task_recurring(target_task):
            return handle_recurring_task(api, target_task)
        else:
            return handle_non_recurring_task(api, target_task)
        
    except Exception as error:
        print(f"[red]Error touching task: {error}[/red]")
        return None

def add_task(api, task_name):
    """Add a task to the Long Term Tasks project with proper [index] prefix.
    
    Args:
        api: Todoist API instance
        task_name: Name of task to add
        
    Returns:
        Created task object or None if failed
    """
    # Import here to avoid circular imports
    import helper_task_factory
    
    task = helper_task_factory.create_task(
        api=api,
        task_content=task_name,
        task_type="long",
        options={"api": api}
    )
    
    if task:
        print(f"[green]Added task: {task.content}[/green]")
    
    return task

def get_categorized_tasks(api):
    """Fetch tasks from Long Term Tasks project, automatically fix unindexed tasks, and categorize them.
    
    Args:
        api: Todoist API instance
        
    Returns:
        Tuple of (one_shot_tasks, recurring_tasks)
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return [], []
        
    try:
        # Get all tasks in project
        tasks = api.get_tasks(project_id=project_id)
        
        # Extract existing indices and identify unindexed tasks
        indices = []
        unindexed_tasks = []
        
        for task in tasks:
            match = re.match(r'\[(\d+)\]', task.content)
            if match:
                indices.append(int(match.group(1)))
            else:
                unindexed_tasks.append(task)
        
        # Fix unindexed tasks
        if unindexed_tasks:
            print(f"[yellow]Found {len(unindexed_tasks)} tasks without indices. Auto-fixing...[/yellow]")
            
            # Assign indices to unindexed tasks
            for task in unindexed_tasks:
                # Find next available index
                next_index = 0
                while next_index in indices:
                    next_index += 1
                
                # Update task with index
                new_content = f"[{next_index}] {task.content}"
                api.update_task(
                    task_id=task.id,
                    content=new_content
                )
                
                # Update the local task object for correct categorization
                task.content = new_content
                indices.append(next_index)
            
            print(f"[green]Successfully indexed {len(unindexed_tasks)} tasks.[/green]")
            
        # Filter tasks that are due today or earlier
        filtered_tasks = [task for task in tasks if is_task_due_today_or_earlier(task)]
            
        # Categorize tasks
        one_shot_tasks = []
        recurring_tasks = []
        
        for task in filtered_tasks:
            if is_task_recurring(task):
                recurring_tasks.append(task)
            else:
                one_shot_tasks.append(task)
        
        # Sort both lists
        def sort_key(task):
            if not task.due:
                return (datetime.min.date(), get_index(task))
            due_date = datetime.fromisoformat(task.due.date).date()
            return (due_date, get_index(task))
            
        def get_index(task):
            match = re.match(r'\[(\d+)\]', task.content)
            return int(match.group(1)) if match else float('inf')
            
        one_shot_tasks.sort(key=sort_key)
        recurring_tasks.sort(key=sort_key)
        
        return one_shot_tasks, recurring_tasks
        
    except Exception as error:
        print(f"[red]Error fetching and categorizing tasks: {error}[/red]")
        return [], []

def fetch_tasks(api, prefix=None):
    """Fetch tasks from Long Term Tasks project.
    
    Args:
        api: Todoist API instance
        prefix: Not used anymore, kept for backward compatibility
        
    Returns:
        List of tasks
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return []
        
    try:
        # Get all tasks in project
        tasks = api.get_tasks(project_id=project_id)
            
        # Filter tasks that are due today or earlier
        filtered_tasks = [task for task in tasks if is_task_due_today_or_earlier(task)]
            
        # Sort by due date (oldest first), then by index for tasks with same date
        def sort_key(task):
            # If no due date, treat as oldest
            if not task.due:
                return (datetime.min.date(), get_index(task))
            due_date = datetime.fromisoformat(task.due.date).date()
            return (due_date, get_index(task))
            
        def get_index(task):
            match = re.match(r'\[(\d+)\]', task.content)
            return int(match.group(1)) if match else float('inf')
            
        filtered_tasks.sort(key=sort_key)
        
        return filtered_tasks
        
    except Exception as error:
        print(f"[red]Error fetching tasks: {error}[/red]")
        return []

def format_task_for_display(task):
    """Format a task for display with recurring and priority information.
    
    Args:
        task: Todoist task object
        
    Returns:
        str: Formatted task string ready for display
    """
    try:
        # Extract task index
        match = re.match(r'\[(\d+)\]', task.content)
        if not match:
            return task.content  # Fallback if no index found
            
        task_index = match.group(1)
        
        # Check if the task is recurring
        is_recurring = False
        recurrence_string = ""
        
        if task.due:
            # First check is_recurring property
            if hasattr(task.due, 'is_recurring') and task.due.is_recurring:
                is_recurring = True
                if hasattr(task.due, 'string'):
                    recurrence_string = task.due.string
            # Second check the due string for recurring patterns
            elif hasattr(task.due, 'string') and task.due.string:
                recurrence_patterns = ['every', 'daily', 'weekly', 'monthly', 'yearly']
                if any(pattern in task.due.string.lower() for pattern in recurrence_patterns):
                    is_recurring = True
                    recurrence_string = task.due.string
        
        # Build display string with proper prefixes
        display_text = f"[{task_index}] "
        
        # Add recurring info if applicable
        if is_recurring:
            display_text += "(r) "
            if recurrence_string:
                display_text += f"{recurrence_string} | "
        
        # Add priority if available
        if hasattr(task, 'priority') and task.priority < 4:
            display_text += f"(p{5 - task.priority}) "
        
        # Add the task content without the index
        content_without_index = re.sub(r'^\[\d+\]\s*', '', task.content)
        display_text += content_without_index
        
        return display_text
        
    except Exception as error:
        # Fallback to original content if any error occurs
        return task.content

def display_tasks(api, task_type=None):
    """Display tasks based on their recurrence status.
    
    Args:
        api: Todoist API instance
        task_type: Optional filter (kept for backward compatibility)
    """
    one_shot_tasks, recurring_tasks = get_categorized_tasks(api)
    
    print("\nOne Shots:")
    if one_shot_tasks:
        for task in one_shot_tasks:
            formatted_task = format_task_for_display(task)
            print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
    else:
        print("[dim]No tasks[/dim]")
        
    print("\nRecurring:")
    if recurring_tasks:
        for task in recurring_tasks:
            formatted_task = format_task_for_display(task)
            print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
    else:
        print("[dim]No tasks[/dim]")
    
def rename_task(api, index, new_name):
    """Rename a task in the Long Term Tasks project while preserving its index.
    
    Args:
        api: Todoist API instance
        index: Index of task to rename
        new_name: New name for the task
        
    Returns:
        Updated task object or None if failed
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None
        
    try:
        # Get all tasks to find the one with matching index
        tasks = api.get_tasks(project_id=project_id)
        target_task = None
        
        # Find task with matching index
        for task in tasks:
            match = re.match(r'\[(\d+)\]', task.content)
            if match and int(match.group(1)) == index:
                target_task = task
                break
                
        if not target_task:
            print(f"[yellow]No task found with index [{index}][/yellow]")
            return None
            
        # Construct new task content, just preserving the index
        new_content = f"[{index}] {new_name}"
        
        # Update the task
        updated_task = api.update_task(
            task_id=target_task.id,
            content=new_content
        )
        
        print(f"[green]Renamed task to: {new_content}[/green]")
        return updated_task
        
    except Exception as error:
        print(f"[red]Error renaming task: {error}[/red]")
        return None

module_call_counter.apply_call_counter_to_all(globals(), __name__)