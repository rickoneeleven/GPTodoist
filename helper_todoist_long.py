import module_call_counter
from rich import print
from datetime import datetime
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
        
        # Add task to project
        task = api.add_task(
            content=task_content,
            project_id=project_id
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
        prefix: Optional filter for x_ or y_ tasks
        
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
            tasks = [t for t in tasks if prefix in t.content]
            
        # Sort by index
        tasks.sort(key=lambda t: int(re.match(r'\[(\d+)\]', t.content).group(1)))
        
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

module_call_counter.apply_call_counter_to_all(globals(), __name__)