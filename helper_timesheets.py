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

    # Load completed tasks
    try:
        with open(completed_tasks_file, "r") as f:
            completed_tasks = json.load(f)
    except FileNotFoundError:
        print("No completed tasks file found.")
        return

    # Filter tasks based on the timesheet date
    filtered_tasks = [task for task in completed_tasks if datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date() == timesheet_date]

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
            else:
                summary = task['task_name']
            duration = input("Enter time spent in minutes (default 5): ").strip()
            duration = int(duration) if duration else 5
            timesheet_entries.append({"summary": summary, "duration": duration})

    # Print summary of selected tasks
    if timesheet_entries:
        print("\nSelected tasks for timesheet:")
        for entry in timesheet_entries:
            print(f"- {entry['summary']} ({entry['duration']} minutes)")
        print()

    # Prompt for additional tasks (changed to default 'n')
    while not timesheet_entries or input("Would you like to add any additional tasks? (y/n, default n): ").lower() == 'y':
        summary = input("Enter task summary: ")
        duration = input("Enter time spent in minutes (default 5): ").strip()
        duration = int(duration) if duration else 5
        timesheet_entries.append({"summary": summary, "duration": duration})

        # Print the newly added task
        print(f"Added: {summary} ({duration} minutes)")

    # Calculate total duration of entered tasks
    total_duration = sum(entry['duration'] for entry in timesheet_entries)

    # Generate random duration between 7 and 8 hours (420 to 480 minutes)
    # and round to nearest 5-minute increment
    target_duration = round(random.randint(420, 480) / 5) * 5

    # Adjust durations to match target duration
    if total_duration < target_duration:
        # Add time if less than target
        while total_duration < target_duration:
            for entry in timesheet_entries:
                if total_duration >= target_duration:
                    break
                entry['duration'] += 5
                total_duration += 5
    else:
        # Remove time if more than target
        while total_duration > target_duration:
            for entry in timesheet_entries:
                if total_duration <= target_duration:
                    break
                if entry['duration'] > 5:
                    entry['duration'] -= 5
                    total_duration -= 5

    # Display final timesheet
    print("\n++++++++++++++++++++++++ Final Timesheet:")
    for entry in timesheet_entries:
        print(f"{entry['summary']}: {entry['duration']} minutes")
    
    total_hours = target_duration / 60
    print(f"\nTotal Time: {total_hours:.2f} hours")
    print("\n++++++++++++++++++++++++ ")

    # Save to j_diary.json
    diary_entry = {
        "tasks": timesheet_entries,
        "total_duration": target_duration,  # Changed from total_minutes to target_duration
        "total_hours": round(total_hours, 2)
    }

    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
    except FileNotFoundError:
        diary = {}

    timesheet_date_str = timesheet_date.strftime("%Y-%m-%d")
    if timesheet_date_str in diary:
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
                    entry['duration'] += 1
                    total_duration += 1
            else:
                for entry in merged_entries:
                    if total_duration <= target_duration:
                        break
                    if entry['duration'] > 5:
                        entry['duration'] -= 1
                        total_duration -= 1
        
        diary[timesheet_date_str] = {
            "tasks": merged_entries,
            "total_duration": total_duration,
            "total_hours": round(total_duration / 60, 2)
        }
    else:
        diary[timesheet_date_str] = diary_entry

    with open("j_diary.json", "w") as f:
        json.dump(diary, f, indent=2)

    print(f"Timesheet for {timesheet_date_str} has been saved to j_diary.json")

    # Ask about purging completed tasks, defaulting to 'y'
    purge_tasks = input("Would you like to purge all completed tasks for this date and earlier? (Y/n, default Y): ").lower()
    if purge_tasks != 'n':
        purge_completed_tasks(timesheet_date_str)
        
    # After finalizing the timesheet
    print("\nCurrent Todoist tasks:")
    helper_todoist_part2.display_todoist_tasks(api)
    
    print("\nLong-term tasks:")
    helper_tasks.print_tasks()

    # Ask for the day's overall objective
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        diary = {}

    if today_str in diary and 'overall_objective' in diary[today_str]:
        print(f"\nCurrent overall objective for today: {diary[today_str]['overall_objective']}")
        change_objective = input("Would you like to change today's overall objective? (y/n, default n): ").lower()
        if change_objective == 'y':
            new_objective = input("What key things would you like to achieve today? ")
            diary[today_str]['overall_objective'] = new_objective
    else:
        new_objective = input("What key things would you like to achieve today? ")
        if today_str not in diary:
            diary[today_str] = {}
        diary[today_str]['overall_objective'] = new_objective

    with open("j_diary.json", "w") as f:
        json.dump(diary, f, indent=2)

    print("Overall objective for today has been saved.")

        
def purge_completed_tasks(cutoff_date):
    cutoff_date = datetime.strptime(cutoff_date, "%Y-%m-%d").date()
    
    try:
        with open("j_todays_completed_tasks.json", "r") as f:
            completed_tasks = json.load(f)
        
        # Filter out tasks that are after the cutoff date
        remaining_tasks = [task for task in completed_tasks if datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date() > cutoff_date]
        
        # Save the remaining tasks back to the file
        with open("j_todays_completed_tasks.json", "w") as f:
            json.dump(remaining_tasks, f, indent=2)
        
        print(f"Completed tasks up to and including {cutoff_date} have been purged.")
    except FileNotFoundError:
        print("No completed tasks file found.")
    except json.JSONDecodeError:
        print("Error reading the completed tasks file.")
    except Exception as e:
        print(f"An error occurred while purging tasks: {e}")
        
module_call_counter.apply_call_counter_to_all(globals(), __name__)