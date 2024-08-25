import json
from datetime import datetime, timedelta
from rich import print

def timesheet():
    completed_tasks_file = "j_todays_completed_tasks.json"
    
    # Ask if user wants to include all saved completed tasks
    include_all = input("Would you like to include all saved completed tasks? y/n (default y): ").lower()
    include_all = include_all if include_all else 'y'
    
    if include_all == 'y':
        reference_date = None
        timesheet_date = datetime.now().date() - timedelta(days=1)  # Default to yesterday
    else:
        while True:
            date_input = input("Enter the date to show completed tasks from (dd/mm format, or 'yesterday'): ")
            if date_input.lower() == 'yesterday':
                reference_date = datetime.now().date() - timedelta(days=1)
                timesheet_date = reference_date
                break
            try:
                reference_date = datetime.strptime(date_input + "/" + str(datetime.now().year), "%d/%m/%Y").date()
                timesheet_date = reference_date
                break
            except ValueError:
                print("Invalid date format. Please use dd/mm or 'yesterday'.")

    # Load completed tasks
    try:
        with open(completed_tasks_file, "r") as f:
            completed_tasks = json.load(f)
    except FileNotFoundError:
        print("No completed tasks file found.")
        return

    # Filter tasks based on the reference date
    if reference_date:
        filtered_tasks = [task for task in completed_tasks if datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date() >= reference_date]
    else:
        filtered_tasks = completed_tasks

    if not filtered_tasks:
        print("No completed tasks found for the specified period.")
        return

    # Display filtered tasks
    print("Completed tasks:")
    for task in filtered_tasks:
        print(f"{task['id']}, {task['datetime']}, {task['task_name']}")

    # Get user input for task IDs
    selected_ids = input("Enter the IDs of tasks for the timesheet (comma-separated): ").split(',')
    selected_ids = [int(id.strip()) for id in selected_ids]

    timesheet_entries = []

    # Process selected tasks
    for task_id in selected_ids:
        task = next((t for t in filtered_tasks if t['id'] == task_id), None)
        if task:
            print(f"\nTask: {task['task_name']}")
            summary = input("Enter task summary (press Enter to keep original): ").strip()
            if not summary:
                summary = task['task_name']
            duration = input("Enter time spent in minutes (default 5): ").strip()
            duration = int(duration) if duration else 5
            timesheet_entries.append({"summary": summary, "duration": duration})

    # Ask for additional tasks
    while input("Would you like to add any additional tasks? (y/n, default y): ").lower() != 'n':
        summary = input("Enter task summary: ")
        duration = input("Enter time spent in minutes (default 5): ").strip()
        duration = int(duration) if duration else 5
        timesheet_entries.append({"summary": summary, "duration": duration})

    # Adjust durations to total 420 minutes (7 hours)
    total_duration = sum(entry['duration'] for entry in timesheet_entries)
    target_duration = 420  # 7 hours in minutes

    while total_duration != target_duration:
        if total_duration < target_duration:
            # Add time if less than 7 hours
            for entry in timesheet_entries:
                if total_duration >= target_duration:
                    break
                entry['duration'] += 1
                total_duration += 1
        else:
            # Remove time if more than 7 hours
            for entry in timesheet_entries:
                if total_duration <= target_duration:
                    break
                if entry['duration'] > 5:
                    entry['duration'] -= 1
                    total_duration -= 1

    # Display final timesheet
    print("\n++++++++++++++++++++++++ Final Timesheet:")
    for entry in timesheet_entries:
        print(f"{entry['summary']}: {entry['duration']} minutes")
    
    total_minutes = sum(entry['duration'] for entry in timesheet_entries)
    total_hours = total_minutes / 60
    print(f"\nTotal Time: {total_hours:.2f} hours")
    print("\n++++++++++++++++++++++++ ")

    # Confirm or change the timesheet date
    print(f"Timesheet date: {timesheet_date.strftime('%Y-%m-%d')}")
    change_date = input("Would you like to change this date? (y/n, default n): ").lower()
    if change_date == 'y':
        while True:
            date_input = input("Enter the new date for this timesheet (dd/mm/yy): ")
            try:
                timesheet_date = datetime.strptime(date_input, "%d/%m/%y").date()
                break
            except ValueError:
                print("Invalid date format. Please use dd/mm/yy.")

    # Save to j_diary.json
    diary_entry = {
        "tasks": timesheet_entries,
        "total_duration": total_minutes,
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
        existing_entries = diary[timesheet_date_str]["tasks"]
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