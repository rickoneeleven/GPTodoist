import json, random, os
from datetime import datetime, timedelta
from rich import print
from todoist_api_python.api import TodoistAPI
import helper_todoist_part2
import helper_tasks, module_call_counter

def timesheet():
    api = TodoistAPI(os.environ["TODOIST_API_KEY"])
    completed_tasks_file = "j_todays_completed_tasks.json"

    # Ask for the timesheet date at the beginning
    while True:
        date_input = input("Enter the date for this timesheet (dd/mm/yy format, or press Enter for yesterday): ")
        if date_input.lower() == '' or date_input.lower() == 'yesterday':
            timesheet_date = datetime.now().date() - timedelta(days=1)
            break
        try:
            timesheet_date = datetime.strptime(date_input, "%d/%m/%y").date()
            break
        except ValueError:
            print("Invalid date format. Please use dd/mm/yy or press Enter for yesterday.")

    # Get the day name for the timesheet date
    day_name = timesheet_date.strftime("%A")

    # Load completed tasks
    try:
        with open(completed_tasks_file, "r") as f:
            completed_tasks = json.load(f)
    except FileNotFoundError:
        print("No completed tasks file found.")
        return

    # Filter tasks based on the timesheet date
    filtered_tasks = [task for task in completed_tasks if datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date() == timesheet_date]
    
    # Sort filtered tasks by datetime and reindex them starting from 1
    filtered_tasks.sort(key=lambda x: datetime.strptime(x['datetime'], "%Y-%m-%d %H:%M:%S"))
    for i, task in enumerate(filtered_tasks, 1):
        task['id'] = i
        
    # Update the original completed_tasks list with new indices for the filtered day
    completed_tasks = [task for task in completed_tasks if datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date() != timesheet_date]
    completed_tasks.extend(filtered_tasks)
    
    # Save the updated tasks back to the file
    with open(completed_tasks_file, "w") as f:
        json.dump(completed_tasks, f, indent=2)

    # Load and display overall objective for the day
    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
        date_str = timesheet_date.strftime("%Y-%m-%d")
        if date_str in diary and 'overall_objective' in diary[date_str]:
            print("\n[yellow2]Your key objective for the day was to try and:[/yellow2]")
            print(f"[yellow]{diary[date_str]['overall_objective']}[/yellow]")
        print()
    except (FileNotFoundError, KeyError):
        print("No overall objective found for this day.")

    if not filtered_tasks:
        print("No completed tasks found for the specified date.")
    else:
        print("Completed tasks:")
        for task in filtered_tasks:
            print(f"{task['datetime']}, {task['id']}, {task['task_name']}")

    # Get user input for task IDs
    selected_ids = input("Enter the IDs of tasks for the timesheet (comma-separated, or press Enter to skip): ").split(',')
    selected_ids = [int(id.strip()) for id in selected_ids if id.strip()]

    timesheet_entries = []

    # Process selected tasks
    for task_id in selected_ids:
        task = next((t for t in filtered_tasks if t['id'] == task_id), None)
        if task:
            print(f"\nTask: {task['task_name']}")
            change_summary = input("Would you like to change task summary? (y/n, default: n): ").strip().lower()
            if change_summary == 'y':
                summary = input("Enter new task summary: ").strip()
                # Add validation check for numeric input
                if any(char.isdigit() for char in summary):
                    confirm = input(f"[red]Are you sure you want to change this task description to '{summary}'? (y/n, default: n): [/red]").strip().lower()
                    if confirm != 'y':
                        summary = task['task_name']
            else:
                summary = task['task_name']
            duration_input = input("Enter time spent in minutes (default 5): ").strip()
            
            # Check if duration is locked (wrapped in parentheses)
            is_locked = False
            if duration_input.startswith('(') and duration_input.endswith(')'):
                is_locked = True
                duration_input = duration_input[1:-1]  # Remove parentheses
            
            duration = int(duration_input) if duration_input else 5
            
            timesheet_entries.append({
                "summary": summary, 
                "duration": duration,
                "is_locked": is_locked,
                "datetime": task['datetime']
            })

    # Print summary of selected tasks
    if timesheet_entries:
        print("\nSelected tasks for timesheet:")
        for entry in timesheet_entries:
            lock_status = "(locked)" if entry.get('is_locked') else ""
            print(f"- {entry['summary']} ({entry['duration']} minutes) {lock_status}")
        print()

    # Prompt for additional tasks with the updated message
    while not timesheet_entries or input(f"Would you like to add any additional tasks? i.e. {day_name}'s flow: {diary.get(date_str, {}).get('overall_objective', 'No overall objective found')} (y/n, default n): ").lower() == 'y':
        summary = input("Enter task summary: ")
        duration_input = input("Enter time spent in minutes (default 5): ").strip()
        
        # Check if duration is locked
        is_locked = False
        if duration_input.startswith('(') and duration_input.endswith(')'):
            is_locked = True
            duration_input = duration_input[1:-1]  # Remove parentheses
        
        duration = int(duration_input) if duration_input else 5
        completion_time = input("Enter the time you completed this task (HH:mm format): ").strip()
        
        # Combine the timesheet date with the completion time
        task_datetime = f"{timesheet_date.strftime('%Y-%m-%d')} {completion_time}"
        
        timesheet_entries.append({
            "summary": summary, 
            "duration": duration,
            "is_locked": is_locked,
            "datetime": task_datetime
        })

        # Print the newly added task
        lock_status = "(locked)" if is_locked else ""
        print(f"Added: {summary} ({duration} minutes) {lock_status}")

    # Sort entries by datetime
    timesheet_entries.sort(key=lambda x: x['datetime'])

    # Calculate total duration of entered tasks, separating locked and unlocked
    locked_duration = sum(entry['duration'] for entry in timesheet_entries if entry.get('is_locked'))
    unlocked_duration = sum(entry['duration'] for entry in timesheet_entries if not entry.get('is_locked'))
    total_duration = locked_duration + unlocked_duration

    # Get random range from user
    rand_low = input("rand low value? (default 420): ").strip()
    rand_low = int(rand_low) if rand_low else 420

    rand_high = input("rand high value? (default 480): ").strip()
    rand_high = int(rand_high) if rand_high else 480

    # Generate random duration and round to nearest 5-minute increment
    target_duration = round(random.randint(rand_low, rand_high) / 5) * 5

    # Check if all entries are locked and match target duration
    all_entries_locked = all(entry.get('is_locked') for entry in timesheet_entries)
    if all_entries_locked:
        # If all entries are locked, use their total as the target duration
        target_duration = total_duration
    else:
        # Only adjust unlocked durations if there are any
        if unlocked_duration > 0:
            if total_duration < target_duration:
                # Add time if less than target
                remaining_to_add = target_duration - total_duration
                while remaining_to_add > 0:
                    for entry in timesheet_entries:
                        if not entry.get('is_locked') and remaining_to_add > 0:
                            entry['duration'] += 5
                            remaining_to_add -= 5
                        if remaining_to_add <= 0:
                            break
            elif total_duration > target_duration:
                # Remove time if more than target
                remaining_to_remove = total_duration - target_duration
                while remaining_to_remove > 0:
                    for entry in timesheet_entries:
                        if not entry.get('is_locked') and entry['duration'] > 5 and remaining_to_remove > 0:
                            entry['duration'] -= 5
                            remaining_to_remove -= 5
                        if remaining_to_remove <= 0:
                            break

    # Sort entries by datetime before saving             
    timesheet_entries.sort(key=lambda x: x['datetime'])

    # Display final timesheet
    print("\n++++++++++++++++++++++++ Final Timesheet:")
    for entry in timesheet_entries:
        lock_status = "(locked)" if entry.get('is_locked') else ""
        print(f"{entry['summary']}: {entry['duration']} minutes {lock_status}")

    total_hours = sum(entry['duration'] for entry in timesheet_entries) / 60
    print(f"\nTotal Time: {total_hours:.2f} hours")
    print("\n++++++++++++++++++++++++ ")
    
    # Remove the datetime and is_locked keys as they're not needed in the final diary entry
    for entry in timesheet_entries:
        del entry['datetime']
        del entry['is_locked']

    # Save to j_diary.json
    diary_entry = {
        "tasks": timesheet_entries,
        "total_duration": sum(entry['duration'] for entry in timesheet_entries),
        "total_hours": round(total_hours, 2)
    }

    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
    except FileNotFoundError:
        diary = {}

    timesheet_date_str = timesheet_date.strftime("%Y-%m-%d")
    if timesheet_date_str in diary:
        # Preserve the overall_objective if it exists
        if 'overall_objective' in diary[timesheet_date_str]:
            diary_entry['overall_objective'] = diary[timesheet_date_str]['overall_objective']
        
        # Merge new entries with existing entries
        existing_entries = diary[timesheet_date_str].get("tasks", [])
        merged_entries = existing_entries + timesheet_entries

        # Recalculate durations for the merged entries
        total_duration = sum(entry['duration'] for entry in merged_entries)
        while total_duration != target_duration:
            if total_duration < target_duration:
                for entry in merged_entries:
                    if total_duration >= target_duration:
                        break
                    if not entry.get('is_locked', False):
                        entry['duration'] += 1
                        total_duration += 1
            else:
                for entry in merged_entries:
                    if total_duration <= target_duration:
                        break
                    if not entry.get('is_locked', False) and entry['duration'] > 5:
                        entry['duration'] -= 1
                        total_duration -= 1

        diary_entry['tasks'] = merged_entries
        diary_entry['total_duration'] = total_duration
        diary_entry['total_hours'] = round(total_duration / 60, 2)

    diary[timesheet_date_str] = diary_entry

    with open("j_diary.json", "w") as f:
        json.dump(diary, f, indent=2)

    print(f"Timesheet for {timesheet_date_str} has been saved to j_diary.json")

    # After finalizing the timesheet
    print("\nCurrent Todoist tasks:")
    helper_todoist_part2.display_todoist_tasks(api)

    print("\nLong-term tasks:")
    helper_tasks.print_tasks()

    # Ask for the day's overall objective
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        diary = {}

    # Print yesterday's objective
    if yesterday_str in diary and 'overall_objective' in diary[yesterday_str]:
        print(f"\n[orange3]Yesterday: {diary[yesterday_str]['overall_objective']}[/orange3]")

    if today_str in diary and 'overall_objective' in diary[today_str]:
        print(f"\nCurrent overall objective for today: {diary[today_str]['overall_objective']}")
        change_objective = input("Would you like to change today's overall objective? (y/n, default n): ").lower()
        if change_objective == 'y':
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


module_call_counter.apply_call_counter_to_all(globals(), __name__)