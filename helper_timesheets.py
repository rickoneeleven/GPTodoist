import json, random, os
from datetime import datetime, timedelta
from rich import print
from todoist_api_python.api import TodoistAPI
import helper_todoist_part2
import helper_tasks, module_call_counter

def get_timesheet_date():
    """Get and validate the timesheet date from user input."""
    while True:
        try:
            date_input = input("Enter the date for this timesheet (dd/mm/yy format, or press Enter for yesterday): ")
            if date_input.lower() in ('', 'yesterday'):
                return datetime.now().date() - timedelta(days=1)
            return datetime.strptime(date_input, "%d/%m/%y").date()
        except ValueError:
            print("[yellow]Invalid date format. Please use dd/mm/yy or press Enter for yesterday.[/yellow]")

def load_completed_tasks(timesheet_date):
    """Load and filter completed tasks for the specified date."""
    completed_tasks_file = "j_todays_completed_tasks.json"
    try:
        with open(completed_tasks_file, "r") as f:
            completed_tasks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("[yellow]No completed tasks file found or error reading file. Creating new file.[/yellow]")
        completed_tasks = []

    # Filter and sort tasks for the specified date
    filtered_tasks = [
        task for task in completed_tasks 
        if datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date() == timesheet_date
    ]
    filtered_tasks.sort(key=lambda x: datetime.strptime(x['datetime'], "%Y-%m-%d %H:%M:%S"))
    
    # Update task IDs
    for i, task in enumerate(filtered_tasks, 1):
        task['id'] = i
    
    # Update original completed_tasks list
    completed_tasks = [
        task for task in completed_tasks 
        if datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date() != timesheet_date
    ]
    completed_tasks.extend(filtered_tasks)
    
    # Save updated tasks
    with open(completed_tasks_file, "w") as f:
        json.dump(completed_tasks, f, indent=2)
        
    return filtered_tasks

def load_diary_objective(timesheet_date):
    """Load and display the overall objective for the specified date."""
    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
        date_str = timesheet_date.strftime("%Y-%m-%d")
        if date_str in diary and 'overall_objective' in diary[date_str]:
            print("\n[yellow2]Your key objective for the day was to try and:[/yellow2]")
            print(f"[yellow]{diary[date_str]['overall_objective']}[/yellow]")
        print()
        return diary, date_str
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        print("[yellow]No overall objective found for this day.[/yellow]")
        return {}, timesheet_date.strftime("%Y-%m-%d")

def get_selected_task_ids(filtered_tasks):
    """Get and validate task IDs from user input."""
    while True:
        try:
            id_input = input("Enter the IDs of tasks for the timesheet (comma-separated, or press Enter to skip): ")
            if not id_input.strip():
                return []
            selected_ids = [int(id.strip()) for id in id_input.split(',') if id.strip()]
            if all(any(task['id'] == id for task in filtered_tasks) for id in selected_ids):
                return selected_ids
            print("[yellow]Some task IDs were not found. Please try again.[/yellow]")
        except ValueError:
            print("[yellow]Please enter valid numbers separated by commas.[/yellow]")

def get_task_details(task):
    """Get updated summary and duration for a task."""
    print(f"\nTask: {task['task_name']}")
    
    # Get task summary
    summary = task['task_name']
    if input("Would you like to change task summary? (y/n, default: n): ").strip().lower() == 'y':
        summary = input("Enter new task summary: ").strip()
        if any(char.isdigit() for char in summary):
            if input(f"[red]Are you sure you want to change this task description to '{summary}'? (y/n, default: n): [/red]").strip().lower() != 'y':
                summary = task['task_name']
    
    # Get task duration
    while True:
        try:
            duration_input = input("Enter time spent in minutes (default 5): ").strip()
            
            is_locked = False
            if duration_input.startswith('(') and duration_input.endswith(')'):
                is_locked = True
                duration_input = duration_input[1:-1]
            
            duration = int(duration_input) if duration_input else 5
            
            if duration <= 0:
                print("[yellow]Duration must be positive. Using default of 5 minutes.[/yellow]")
                duration = 5
            return {
                "summary": summary,
                "duration": duration,
                "is_locked": is_locked,
                "datetime": task['datetime']
            }
        except ValueError:
            print("[yellow]Please enter a valid number. Using default of 5 minutes.[/yellow]")
            return {
                "summary": summary,
                "duration": 5,
                "is_locked": is_locked,
                "datetime": task['datetime']
            }

def get_additional_task_details(day_name, diary, date_str):
    """Get details for additional tasks."""
    summary = input("Enter task summary: ")
    
    # Get duration
    while True:
        try:
            duration_input = input("Enter time spent in minutes (default 5): ").strip()
            
            is_locked = False
            if duration_input.startswith('(') and duration_input.endswith(')'):
                is_locked = True
                duration_input = duration_input[1:-1]
            
            duration = int(duration_input) if duration_input else 5
            
            if duration <= 0:
                print("[yellow]Duration must be positive. Using default of 5 minutes.[/yellow]")
                duration = 5
            break
        except ValueError:
            print("[yellow]Please enter a valid number. Using default of 5 minutes.[/yellow]")
            duration = 5
            break

    # Get completion time
    while True:
        try:
            completion_time = input("Enter the time you completed this task (HH:mm format): ").strip()
            datetime.strptime(completion_time, "%H:%M")
            break
        except ValueError:
            print("[yellow]Invalid time format. Please use HH:mm format (e.g., 14:30)[/yellow]")
    
    return {
        "summary": summary,
        "duration": duration,
        "is_locked": is_locked,
        "datetime": f"{date_str} {completion_time}"
    }

def get_random_range():
    """Get and validate random range for duration adjustment."""
    while True:
        try:
            rand_low = input("rand low value? (default 420): ").strip()
            rand_low = int(rand_low) if rand_low else 420
            
            if rand_low < 0:
                print("[yellow]Low value cannot be negative. Using default 420.[/yellow]")
                rand_low = 420
                continue
                
            while True:
                rand_high = input("rand high value? (default 480): ").strip()
                rand_high = int(rand_high) if rand_high else 480
                
                if rand_high < 0:
                    print("[yellow]High value cannot be negative. Using default 480.[/yellow]")
                    rand_high = 480
                    continue
                    
                if rand_high <= rand_low:
                    print("[yellow]High value must be greater than low value. Please try again.[/yellow]")
                    continue
                    
                return rand_low, rand_high
        except ValueError:
            print("[yellow]Please enter valid numbers. Using defaults (420-480).[/yellow]")
            return 420, 480

def adjust_durations(timesheet_entries, target_duration):
    """Adjust task durations to match target duration."""
    locked_duration = sum(entry['duration'] for entry in timesheet_entries if entry.get('is_locked'))
    unlocked_duration = sum(entry['duration'] for entry in timesheet_entries if not entry.get('is_locked'))
    total_duration = locked_duration + unlocked_duration

    # If all entries are locked, use their total as target
    if all(entry.get('is_locked') for entry in timesheet_entries):
        return timesheet_entries

    # Only adjust unlocked durations if there are any
    if unlocked_duration > 0:
        if total_duration < target_duration:
            remaining_to_add = target_duration - total_duration
            while remaining_to_add > 0:
                for entry in timesheet_entries:
                    if not entry.get('is_locked') and remaining_to_add > 0:
                        entry['duration'] += 5
                        remaining_to_add -= 5
                    if remaining_to_add <= 0:
                        break
        elif total_duration > target_duration:
            remaining_to_remove = total_duration - target_duration
            while remaining_to_remove > 0:
                for entry in timesheet_entries:
                    if not entry.get('is_locked') and entry['duration'] > 5 and remaining_to_remove > 0:
                        entry['duration'] -= 5
                        remaining_to_remove -= 5
                    if remaining_to_remove <= 0:
                        break
    
    return timesheet_entries

def save_timesheet(timesheet_entries, timesheet_date, diary):
    """Save the timesheet entries to the diary."""
    # Remove unnecessary keys and calculate totals
    for entry in timesheet_entries:
        del entry['datetime']
        del entry['is_locked']

    total_duration = sum(entry['duration'] for entry in timesheet_entries)
    total_hours = total_duration / 60

    diary_entry = {
        "tasks": timesheet_entries,
        "total_duration": total_duration,
        "total_hours": round(total_hours, 2)
    }

    timesheet_date_str = timesheet_date.strftime("%Y-%m-%d")
    
    # Preserve overall objective if it exists
    if timesheet_date_str in diary and 'overall_objective' in diary[timesheet_date_str]:
        diary_entry['overall_objective'] = diary[timesheet_date_str]['overall_objective']

    diary[timesheet_date_str] = diary_entry

    with open("j_diary.json", "w") as f:
        json.dump(diary, f, indent=2)

    print(f"Timesheet for {timesheet_date_str} has been saved to j_diary.json")

def update_todays_objective(diary):
    """Update the overall objective for today."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Print yesterday's objective
    if yesterday_str in diary and 'overall_objective' in diary[yesterday_str]:
        print(f"\n[orange3]Yesterday: {diary[yesterday_str]['overall_objective']}[/orange3]")

    if today_str in diary and 'overall_objective' in diary[today_str]:
        print(f"\nCurrent overall objective for today: {diary[today_str]['overall_objective']}")
        if input("Would you like to change today's overall objective? (y/n, default n): ").lower() == 'y':
            new_objective = input("What key things would you like to achieve today? Check meetings | ..")
            diary[today_str]['overall_objective'] = new_objective
    else:
        new_objective = input("What key things would you like to achieve today? Check meetings | ..")
        if today_str not in diary:
            diary[today_str] = {}
        diary[today_str]['overall_objective'] = new_objective

    with open("j_diary.json", "w") as f:
        json.dump(diary, f, indent=2)

    print("Overall objective for today has been saved.")

def timesheet():
    """Main timesheet function orchestrating the timesheet creation process."""
    try:
        api = TodoistAPI(os.environ["TODOIST_API_KEY"])

        # Get timesheet date
        timesheet_date = get_timesheet_date()
        day_name = timesheet_date.strftime("%A")

        # Load completed tasks and diary
        filtered_tasks = load_completed_tasks(timesheet_date)
        diary, date_str = load_diary_objective(timesheet_date)

        if not filtered_tasks:
            print("No completed tasks found for the specified date.")
        else:
            print("Completed tasks:")
            for task in filtered_tasks:
                print(f"{task['datetime']}, {task['id']}, {task['task_name']}")

        # Get selected tasks and process them
        selected_ids = get_selected_task_ids(filtered_tasks)
        timesheet_entries = []

        for task_id in selected_ids:
            task = next((t for t in filtered_tasks if t['id'] == task_id), None)
            if task:
                entry = get_task_details(task)
                timesheet_entries.append(entry)

        # Handle additional tasks
        while not timesheet_entries or input(f"Would you like to add any additional tasks? i.e. {day_name}'s flow: {diary.get(date_str, {}).get('overall_objective', 'No overall objective found')} (y/n, default n): ").lower() == 'y':
            entry = get_additional_task_details(day_name, diary, date_str)
            timesheet_entries.append(entry)
            lock_status = "(locked)" if entry['is_locked'] else ""
            print(f"Added: {entry['summary']} ({entry['duration']} minutes) {lock_status}")

        # Sort entries by datetime
        timesheet_entries.sort(key=lambda x: x['datetime'])

        # Get random range and target duration
        rand_low, rand_high = get_random_range()
        target_duration = round(random.randint(rand_low, rand_high) / 5) * 5

        # Adjust durations to match target
        timesheet_entries = adjust_durations(timesheet_entries, target_duration)

        # Display final timesheet
        print("\n++++++++++++++++++++++++ Final Timesheet:")
        for entry in timesheet_entries:
            lock_status = "(locked)" if entry.get('is_locked') else ""
            print(f"{entry['summary']}: {entry['duration']} minutes {lock_status}")

        total_hours = sum(entry['duration'] for entry in timesheet_entries) / 60
        print(f"\nTotal Time: {total_hours:.2f} hours")
        print("\n++++++++++++++++++++++++ ")

        # Save timesheet and handle final tasks
        save_timesheet(timesheet_entries, timesheet_date, diary)

        # Display current tasks
        print("\nCurrent Todoist tasks:")
        helper_todoist_part2.display_todoist_tasks(api)

        print("\nLong-term tasks:")
        helper_tasks.print_tasks()

        # Update today's objective
        update_todays_objective(diary)

    except Exception as e:
        print(f"\n[red]An error occurred: {str(e)}[/red]")
        print("[yellow]Would you like to try again? (y/n):[/yellow]")
        retry = input().lower().strip()
        if retry == 'y':
            timesheet()  # Recursive call to restart the timesheet process

module_call_counter.apply_call_counter_to_all(globals(), __name__)