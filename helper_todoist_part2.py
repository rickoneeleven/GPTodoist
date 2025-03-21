import re, json, pytz, datetime, time, os, signal, subprocess
import module_call_counter, helper_todoist_long
from dateutil.parser import parse
from rich import print

# Import necessary functions from part1
from helper_todoist_part1 import (
    get_active_filter,
    read_long_term_tasks,
    complete_todoist_task_by_id,
    format_due_time,
    print_beast_mode_complete,
    add_to_active_task_file,
)

def add_todoist_task(api, task_name):
    try:
        # Import here to avoid circular imports
        import helper_task_factory
        
        active_filter, project_id = get_active_filter()
        if not active_filter:
            print("No active filters configured. Update j_todoist_filters.json.")
            return None
            
        # Remove the "add task " prefix
        task_name = task_name.replace("add task ", "").strip()
        
        # Use the factory to create the task
        task = helper_task_factory.create_task(
            api=api,
            task_content=task_name,
            task_type="normal",
            options={"project_id": project_id}
        )
        
        if task:
            print(f"[purple]Task '{task.content}' successfully added.[/purple]")
        
        return task
    except Exception as error:
        print(f"[red]Error adding task: {error}[/red]")
        return None

def fetch_todoist_tasks(api):
    def handler(signum, frame):
        raise Exception("end of time")
    signal.signal(signal.SIGALRM, handler)
    active_filter, project_id = get_active_filter()
    if not active_filter:
        print("No active filters configured. Update j_todoist_filters.json.")
        return
    retries = 0
    while retries < 99:
        try:
            signal.alarm(5)
            tasks = api.get_tasks(filter=active_filter)
            london_tz = pytz.timezone("Europe/London")
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            now_london = now_utc.astimezone(london_tz)

            for task in tasks:
                if task.due:
                    if task.due.datetime:
                        utc_dt = parse(task.due.datetime)
                        london_dt = utc_dt.astimezone(london_tz)
                        task.due.datetime = london_dt.isoformat()
                        task.has_time = True
                    elif task.due.date:
                        due_date = parse(task.due.date).date()
                        task.due.datetime = now_london.replace(year=due_date.year, month=due_date.month, day=due_date.day).isoformat()
                        task.has_time = False
                    else:
                        task.due.datetime = now_london.isoformat()
                        task.has_time = False
                else:
                    task.due = type("Due", (object,), {"datetime": now_london.isoformat()})()
                    task.has_time = False

            sorted_final_tasks = sorted(
                tasks,
                key=lambda t: (
                    -t.priority,
                    t.due.datetime if t.due and hasattr(t.due, "datetime") else now_london.isoformat(),
                    not t.has_time,
                    t.created if hasattr(t, "created") else "",
                ),
            )
            
            signal.alarm(0)
            return sorted_final_tasks
        except Exception as e:
            retries += 1
            print(f"Attempt {retries}: Failed to fetch tasks. Error: {e}")
            if retries == 99:
                print("[red]Failed to fetch tasks after 99 retries. Exiting with 'end of time'[/red]")
                return None
            time.sleep(1)

def get_next_todoist_task(api):
    try:
        tasks = fetch_todoist_tasks(api)
        if tasks is None:  # Handle case where fetch_todoist_tasks failed
            print("[yellow]Unable to fetch tasks at this time. Please try again later.[/yellow]")
            print()
            return
            
        if tasks:
            try:
                next_task = tasks[0]
                original_task_name = next_task.content
                task_id = next_task.id
                task_due = next_task.due.datetime if next_task.due and next_task.due.datetime else None
                
                # Always store the next task, regardless of due time
                try:
                    add_to_active_task_file(original_task_name, task_id, task_due)
                except Exception as e:
                    print(f"[yellow]Warning: Could not save active task file: {str(e)}[/yellow]")
                
                # Check if task is due in the future
                if task_due:
                    try:
                        current_time = datetime.datetime.now(datetime.timezone.utc)
                        due_time = parse(task_due)
                        if due_time > current_time:
                            print(f"                   [orange1]next task due at {due_time.strftime('%H:%M')}...[/orange1]")
                            print()
                        else:
                            try:
                                task = api.get_task(task_id)
                                if task:
                                    display_info = get_task_display_info(task)
                                    print(f"                   [green]{display_info}{original_task_name}[/green]")
                                    if task.description:
                                        print(f"                   [italic blue]{task.description}[/italic blue]")
                                    print()
                            except Exception as e:
                                print(f"[yellow]Warning: Could not fetch full task details: {str(e)}[/yellow]")
                                # Fall back to displaying basic task info
                                print(f"                   [green]{original_task_name}[/green]")
                                print()
                    except (ValueError, TypeError) as e:
                        print(f"[yellow]Warning: Error processing task due date: {str(e)}[/yellow]")
                        print(f"                   [green]{original_task_name}[/green]")
                        print()
                else:
                    try:
                        task = api.get_task(task_id)
                        if task:
                            display_info = get_task_display_info(task)
                            print(f"                   [green]{display_info}{original_task_name}[/green]")
                            if task.description:
                                print(f"                   [italic blue]{task.description}[/italic blue]")
                            print()
                    except Exception as e:
                        print(f"[yellow]Warning: Could not fetch full task details: {str(e)}[/yellow]")
                        print(f"                   [green]{original_task_name}[/green]")
                        print()
            except Exception as e:
                print(f"[yellow]Warning: Error processing next task: {str(e)}[/yellow]")
                print()
        else:
            print("\u2705")
            print()
            
        # Display long-term tasks
        print("[cyan]Long Term Tasks:[/cyan]")
        try:
            # Get categorized tasks
            one_shot_tasks, recurring_tasks = helper_todoist_long.get_categorized_tasks(api)
            
            # Display one-shot tasks
            print("\nOne Shots:")
            if one_shot_tasks:
                for task in one_shot_tasks:
                    formatted_task = helper_todoist_long.format_task_for_display(task)
                    print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
            else:
                print("[dim]No tasks[/dim]")
                
            # Display recurring tasks
            print("\nRecurring:")
            if recurring_tasks:
                for task in recurring_tasks:
                    formatted_task = helper_todoist_long.format_task_for_display(task)
                    print(f"[dodger_blue1]{formatted_task}[/dodger_blue1]")
            else:
                print("[dim]No tasks[/dim]")
            print()
        except Exception as e:
            print(f"[yellow]Warning: Error processing long-term tasks: {str(e)}[/yellow]")
            print()
            
    except Exception as e:
        print(f"[yellow]An error occurred while getting next task: {str(e)}[/yellow]")
        print("Continuing to main loop...")
        print()
        return
              
def get_task_display_info(task):
    display_info = ""
    if task and task.due:
        if task.due.is_recurring:
            display_info += "(r) "
        display_info += f"{task.due.string} | "
    
    if task.priority and task.priority < 4:
        display_info += f"(p{5 - task.priority}) "
    
    return display_info

def display_todoist_tasks(api):
    tasks = fetch_todoist_tasks(api)
    london_tz = pytz.timezone("Europe/London")
    if tasks:
        max_due_time_length = max(
            len(format_due_time(task.due.datetime if task.due else None, london_tz))
            for task in tasks
        )
        tab_size = 8
        for task in tasks:
            due_time_str = task.due.datetime if task.due else None
            due_time = format_due_time(due_time_str, london_tz).ljust(
                max_due_time_length + tab_size
            )
            
            # Check if the task is recurring
            is_recurring = False
            if task.due and hasattr(task.due, 'string'):
                recurrence_patterns = ['every', 'daily', 'weekly', 'monthly', 'yearly']
                is_recurring = any(pattern in task.due.string.lower() for pattern in recurrence_patterns)
            
            recurrence_prefix = "(r) " if is_recurring else ""
            
            # Add priority label if priority is not 4
            priority_label = ""
            if task.priority and task.priority < 4:
                priority_label = f"(p{5 - task.priority}) "
            
            task_name = f"{recurrence_prefix}{priority_label}{task.content}"
            print(f"{due_time}{task_name}")
            
            # Display description if it exists
            if task.description:
                description_indent = " " * (max_due_time_length + tab_size)
                print(f"{description_indent}[italic blue]{task.description}[/italic blue]")

def graft(api, user_message):
    try:
        subprocess.call("reset")
        if user_message.strip().lower() == "graft":
            if os.path.exists("j_grafted_tasks.json"):
                print("You're already grafting. Would you like to reset current graft and pick again? (y/n): ")
                response = input().strip().lower()
                if response != "y":
                    print("Continuing with current graft.")
                    return
            tasks = fetch_todoist_tasks(api)
            if tasks:
                for index, task in enumerate(tasks, start=1):
                    print(f"{index}. {task.content}")
                print("Please type the numbers of the 3 hardest tasks in order of difficulty (e.g., 4,7,9): ")
                selected_indexes = input()
                selected_indexes = [int(i) for i in selected_indexes.split(',')]
                selected_tasks = [tasks[i-1] for i in selected_indexes]
                grafted_tasks = [{"task_name": task.content, "task_id": task.id, "index": i} for i, task in enumerate(selected_tasks, start=1)]
                with open("j_grafted_tasks.json", "w") as file:
                    json.dump(grafted_tasks, file, indent=2)
            else:
                print("No tasks available to graft.")
        elif user_message.strip().lower() == "graft delete":
            if os.path.exists("j_grafted_tasks.json"):
                os.remove("j_grafted_tasks.json")
                print("Grafting process reset successfully.")
            else:
                print("No grafting process found to reset.")
        elif user_message.startswith("graft "):
            index_to_complete = int(user_message.split()[1])
            with open("j_grafted_tasks.json", "r") as file:
                grafted_tasks = json.load(file)
            task_to_complete = next((task for task in grafted_tasks if task["index"] == index_to_complete), None)
            if task_to_complete:
                if complete_todoist_task_by_id(api, task_to_complete["task_id"]):
                    grafted_tasks.remove(task_to_complete)
                    if grafted_tasks:
                        with open("j_grafted_tasks.json", "w") as file:
                            json.dump(grafted_tasks, file, indent=2)
                    else:
                        os.remove("j_grafted_tasks.json")
                        subprocess.call("reset")
                        print_beast_mode_complete()
                else:
                    print("Failed to complete the task with Todoist API.")
            else:
                print("Task index not found in grafted tasks.")
    except Exception as e:
        print(f"An error occurred: {e}")

def check_if_grafting(api):
    graft_file_path = "j_grafted_tasks.json"
    if os.path.exists(graft_file_path):
        with open(graft_file_path, "r") as file:
            grafted_tasks = json.load(file)
            print(f"[red]YOU'RE IN GRAFT MODE BABY, LETS GOOOOoooooooooo![/red]")
            print()
            print()
            for task in grafted_tasks:
                print(f"{task['index']}. {task['task_name']}")
            print()
            print()
        return True
    else:
        return False

def rename_todoist_task(api, user_message):
    try:
        new_task_name = user_message[len("rename "):].strip()
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
        task = api.get_task(task_id)
        if task:
            api.update_task(task_id=task_id, content=new_task_name)
            print(f"Task renamed to: {new_task_name}")
            return True
        else:
            print(f"Task with ID {task_id} not found.")
            return False
    except FileNotFoundError:
        print("Active task file not found.")
        return False
    except KeyError:
        print("Task ID not found in the active task file.")
        return False
    except Exception as error:
        print(f"Error renaming task: {error}")
        return False

def change_active_task_priority(api, user_message):
    try:
        priority_level = user_message.split()[-1]
        if priority_level not in ["1", "2", "3", "4"]:
            print("Invalid priority level. Please choose between 1, 2, 3, or 4.")
            return False
        with open("j_active_task.json", "r") as infile:
            active_task = json.load(infile)
            task_id = active_task["task_id"]
        todoist_priority = 5 - int(priority_level)
        task = api.get_task(task_id)
        if task:
            api.update_task(task_id=task_id, priority=todoist_priority)
            print(f"Task priority updated to p{priority_level}.")
            return True
        else:
            print(f"Task with ID {task_id} not found.")
            return False
    except FileNotFoundError:
        print("Active task file not found.")
        return False
    except KeyError:
        print("Task ID not found in the active task file.")
        return False
    except Exception as error:
        print(f"Error updating task priority: {error}")
        return False

module_call_counter.apply_call_counter_to_all(globals(), __name__)