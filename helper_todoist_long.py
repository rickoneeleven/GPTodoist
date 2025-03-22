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
        
def touch_task(api, task_index):
    """Update the timestamp of a task by setting its due date to today.
    
    Args:
        api: Todoist API instance
        task_index: Index of task to touch
        
    Returns:
        Updated task object or None if failed
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
            
        # Extract task content without index to check if it's a y_ task
        content_without_index = re.sub(r'^\[\d+\]\s*', '', target_task.content)
        
        # Check if this is a y_ task that's already been touched today
        if content_without_index.startswith('y_'):
            if target_task.due and target_task.due.date:
                due_date = datetime.fromisoformat(target_task.due.date)
                if due_date.date() > datetime.now().date():
                    print(f"[yellow]Task {task_index} has already been touched today[/yellow]")
                    return None
            
        # Update the task's due date to tomorrow (so it won't show up in today's list)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        updated_task = api.update_task(
            task_id=target_task.id,
            due_string=tomorrow
        )
        
        print(f"[green]Updated task: {target_task.content}[/green]")
        return updated_task
        
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
    project_id = get_long_term_project_id(api)
    if not project_id:
        return None
        
    try:
        # Get existing tasks to determine next index
        tasks = api.get_tasks(project_id=project_id)
        
        # Extract existing indices
        indices = []
        for task in tasks:
            match = re.match(r'\[(\d+)\]', task.content)
            if match:
                indices.append(int(match.group(1)))
                
        # Find lowest available index
        next_index = 0
        while next_index in indices:
            next_index += 1
            
        # Format task content with index prefix
        task_content = f"[{next_index}] {task_name}"
        
        # For y_ tasks, set due date to yesterday so they show up immediately
        due_string = None
        if task_name.startswith('y_'):
            yesterday = datetime.now() - timedelta(days=1)
            due_string = yesterday.strftime("%Y-%m-%d")
        
        # Add task to project
        task = api.add_task(
            content=task_content,
            project_id=project_id,
            due_string=due_string
        )
        
        print(f"[green]Added task: {task_content}[/green]")
        return task
        
    except Exception as error:
        print(f"[red]Error adding task: {error}[/red]")
        return None

def fetch_tasks(api, prefix=None):
    """Fetch and display tasks from Long Term Tasks project.
    
    Args:
        api: Todoist API instance
        prefix: Optional filter for x_ or y_ tasks, or "untagged" for tasks without x_ or y_
        
    Returns:
        List of tasks matching criteria
    """
    project_id = get_long_term_project_id(api)
    if not project_id:
        return []
        
    try:
        # Get all tasks in project
        tasks = api.get_tasks(project_id=project_id)
        
        # Filter by prefix if specified
        if prefix:
            filtered_tasks = []
            today = datetime.now().date()
            
            if prefix == "untagged":
                # Get tasks that don't start with x_ or y_ (after removing index)
                for task in tasks:
                    # Remove index from content
                    content_without_index = re.sub(r'^\[\d+\]\s*', '', task.content)
                    # Check if it starts with x_ or y_
                    if not (content_without_index.startswith('x_') or content_without_index.startswith('y_')):
                        filtered_tasks.append(task)
            else:
                # Regular prefix filtering
                for task in tasks:
                    # Remove index from content
                    content_without_index = re.sub(r'^\[\d+\]\s*', '', task.content)
                    # Check if it starts with the prefix
                    if content_without_index.startswith(prefix):
                        # For y_ tasks, only show if due today or overdue
                        if prefix == 'y_':
                            if not task.due:
                                # For y_ tasks without due date, treat as oldest
                                filtered_tasks.append(task)
                            else:
                                due_date = datetime.fromisoformat(task.due.date)
                                if due_date.date() <= today:
                                    filtered_tasks.append(task)
                        else:
                            filtered_tasks.append(task)
            tasks = filtered_tasks
            
        # Sort by due date (oldest first), then by index for tasks with same date
        def sort_key(task):
            # If no due date (only possible for non-y_ tasks), treat as oldest
            if not task.due:
                return (datetime.min.date(), get_index(task))
            due_date = datetime.fromisoformat(task.due.date).date()
            return (due_date, get_index(task))
            
        def get_index(task):
            match = re.match(r'\[(\d+)\]', task.content)
            return int(match.group(1)) if match else float('inf')
            
        tasks.sort(key=sort_key)
        
        return tasks
        
    except Exception as error:
        print(f"[red]Error fetching tasks: {error}[/red]")
        return []

def identify_task_type(task_content):
    """Identify if a task is x_ or y_ type.
    
    Args:
        task_content: Task content string
        
    Returns:
        'x', 'y' or None
    """
    if 'x_' in task_content:
        return 'x'
    elif 'y_' in task_content:
        return 'y'
    return None

def display_tasks(api, task_type=None):
    """Display tasks in format matching current implementation.
    
    Args:
        api: Todoist API instance
        task_type: Optional 'x' or 'y' to filter tasks
    """
    prefix = None
    if task_type == 'x':
        prefix = 'x_'
    elif task_type == 'y':
        prefix = 'y_'
        
    tasks = fetch_tasks(api, prefix)
    
    for task in tasks:
        # Extract index from [n] prefix
        index = re.match(r'\[(\d+)\]', task.content).group(1)
        
        # Get task date
        task_date = datetime.fromisoformat(task.created_at[:19])
        date_str = task_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # Format matching current implementation
        print(f"[{index}] {task.content} {date_str}")
        
def rename_task(api, index, new_name):
    """Rename a task in the Long Term Tasks project while preserving its index.
    
    Args:
        api: Todoist API instance
        index: Index of task to rename
        new_name: New name for the task (complete new name including x_/y_ prefix)
        
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