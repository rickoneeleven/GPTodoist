import re, datetime, os
import module_call_counter
from rich import print
from datetime import timedelta

def create_task(api, task_content, task_type="normal", options=None):
    """Unified task creation function with smart parsing.
    
    Args:
        api: Todoist API instance
        task_content: Raw task text content
        task_type: "normal" or "long" to determine destination
        options: Additional options dictionary (project_id, etc.)
    
    Returns:
        Created task object or None if failed
    """
    if options is None:
        options = {}
    
    try:
        # Parse task content for scheduling and priority
        parsed_data = parse_task_content(task_content)
        content = parsed_data["content"]
        
        # Create task parameters based on type
        task_params = create_task_parameters(content, parsed_data, task_type, options)
        
        # Create the task
        task = api.add_task(**task_params)
        
        if not task:
            print("[red]Failed to add task.[/red]")
            return None
            
        # Handle post-creation tasks (like setting due dates)
        if parsed_data["due_string"]:
            api.update_task(task_id=task.id, due_string=parsed_data["due_string"])
            print(f"Task due date set to '{parsed_data['due_string']}'.")
        
        return task
        
    except Exception as error:
        print(f"[red]Error creating task: {error}[/red]")
        return None

def parse_task_content(task_content):
    """Extract scheduling and priority information from task content.
    
    Handles both single-line and multi-line inputs. If scheduling markers
    (time like "12:00" or markers like "(every!) day") appear on the last
    line of a multi-line input, they are extracted into `due_string` and
    removed from the task content.
    
    Args:
        task_content: Raw task content string
        
    Returns:
        Dictionary with parsed data (content, priority, due_string)
    """
    # Initialize result
    result = {
        "content": task_content,
        "priority": None,
        "due_string": None
    }

    # Work with the last non-empty line for scheduling cues
    lines = task_content.splitlines() or [task_content]
    last_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            last_idx = i
            break

    if last_idx is None:
        # Empty content; nothing to parse
        return result

    last_line = lines[last_idx].strip()

    # Patterns: time (supports HH:MM or 9am/9pm), and (every)/(every!) marker
    time_pattern = re.compile(r"\b(\d{1,2}:\d{2}|\d{1,2}(?:am|pm))\b", re.IGNORECASE)
    every_marker_pattern = re.compile(r"\((every!?)\)", re.IGNORECASE)

    time_match = time_pattern.search(last_line)
    every_match = every_marker_pattern.search(last_line)

    if every_match:
        # Example: "... 10:00 (every!) day" or "... (every) monday 9am"
        every_type = every_match.group(1).lower()  # 'every' or 'every!'

        # Prefer schedule words after the marker
        post = last_line[every_match.end():].strip()

        # If a time exists, remove it from schedule words to avoid duplicate
        time_str = time_match.group(1) if time_match else None
        schedule_words = post
        if time_str and schedule_words:
            schedule_words = re.sub(rf"\b{re.escape(time_str)}\b", "", schedule_words, flags=re.IGNORECASE).strip()

        # Build due_string in the order Todoist understands (e.g., "every! monday 9am")
        due_parts = [every_type]
        if schedule_words:
            due_parts.append(schedule_words)
        if time_str:
            due_parts.append(time_str)

        result["due_string"] = " ".join(due_parts).strip()

        # Clean last line content: drop from first of (time or every) to end
        cut_positions = []
        if time_match:
            cut_positions.append(time_match.start())
        cut_positions.append(every_match.start())
        cut_at = min(cut_positions)
        cleaned_last = last_line[:cut_at].rstrip()
        lines[last_idx] = cleaned_last
        result["content"] = "\n".join(lines).rstrip()

    else:
        # No (every) marker; try time-only parsing on the last line
        if time_match:
            time_str = time_match.group(1)
            post = last_line[time_match.end():].strip()
            # Due string: include any words after the time on the same line
            result["due_string"] = f"{time_str} {post}".strip()
            # Remove time and trailing words from content (keep everything before time)
            cleaned_last = last_line[:time_match.start()].rstrip()
            lines[last_idx] = cleaned_last
            result["content"] = "\n".join(lines).rstrip()

    # Extract priority from remaining content
    for i, priority_flag in enumerate(["p1", "p2", "p3"]):
        if priority_flag in result["content"].lower():
            # Todoist uses 4 for p1, 3 for p2, etc.
            result["priority"] = 4 - i
            # We don't remove the priority tag from content as it might be part of text
    
    return result

def create_task_parameters(content, parsed_data, task_type, options):
    """Create appropriate task parameters based on type and parsed data.
    
    Args:
        content: Parsed task content
        parsed_data: Dictionary with parsed task data
        task_type: "normal" or "long"
        options: Additional options
        
    Returns:
        Dictionary of parameters for task creation
    """
    task_params = {"content": content}
    
    # Add priority if specified
    if parsed_data["priority"]:
        task_params["priority"] = parsed_data["priority"]
    
    # Handle project ID based on task type
    if task_type == "normal":
        # For normal tasks, use project_id from options (comes from active filter)
        if "project_id" in options and options["project_id"]:
            task_params["project_id"] = options["project_id"]
    
    elif task_type == "long":
        # For long tasks, get the Long Term Tasks project ID
        project_id = get_long_term_project_id(api=options.get("api"))
        if project_id:
            task_params["project_id"] = project_id
            
            # Get the next available index for long tasks
            next_index = get_next_long_task_index(options.get("api"), project_id)
            
            # Format task content with index prefix
            task_params["content"] = f"[{next_index}] {content}"
    
    return task_params

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

def get_next_long_task_index(api, project_id):
    """Find the next available index for a long task.
    
    Args:
        api: Todoist API instance
        project_id: Long Term Tasks project ID
        
    Returns:
        Next available index (integer)
    """
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
            
        return next_index
        
    except Exception as error:
        print(f"[red]Error determining next task index: {error}[/red]")
        return 0  # Fallback to index 0 in case of error

module_call_counter.apply_call_counter_to_all(globals(), __name__)
