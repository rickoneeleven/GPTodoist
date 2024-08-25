import json
from datetime import datetime, timedelta
from rich import print

def timesheet():
    while True:
        # Ask user which day to reference
        use_yesterday = input("Would you like to reference yesterday's completed tasks? (y/n, default y): ").lower()
        use_yesterday = use_yesterday if use_yesterday else 'y'
        
        if use_yesterday == 'y':
            reference_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            date_input = input("Enter the date to reference (dd/mm format, or 'c' to cancel): ")
            if date_input.lower() == 'c':
                print("Timesheet entry cancelled.")
                return
            try:
                reference_date = datetime.strptime(date_input + "/" + str(datetime.now().year), "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                print("Invalid date format. Please use dd/mm.")
                continue

        # Load completed tasks
        try:
            with open("j_todays_completed_tasks.json", "r") as f:
                completed_tasks = json.load(f)
        except FileNotFoundError:
            print("No completed tasks file found.")
            return

        # Filter tasks for the reference date
        reference_tasks = [task for task in completed_tasks if task['datetime'].startswith(reference_date)]

        if not reference_tasks:
            print(f"No completed tasks found for {reference_date}.")
            retry = input("Would you like to enter another date? (y/n, default y): ").lower()
            if retry != 'n':
                continue
            else:
                print("Timesheet entry cancelled.")
                return
        
        break  # Exit the loop if we have tasks for the selected date

    # Display referenced tasks
    print(f"Completed tasks for {reference_date}:")
    for task in reference_tasks:
        print(f"{task['id']}, {task['datetime']}, {task['task_name']}")

    # Get user input for task IDs
    selected_ids = input("Enter the IDs of tasks for the timesheet (comma-separated): ").split(',')
    selected_ids = [int(id.strip()) for id in selected_ids]

    timesheet_entries = []

    # Process selected tasks
    for task_id in selected_ids:
        task = next((t for t in reference_tasks if t['id'] == task_id), None)
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

    # Adjust durations to total 480 minutes
    total_duration = sum(entry['duration'] for entry in timesheet_entries)
    while total_duration < 480:
        for entry in timesheet_entries:
            if total_duration >= 480:
                break
            entry['duration'] += 5
            total_duration += 5

    # Display final timesheet
    print("\n++++++++++++++++++++++++ Final Timesheet:")
    for entry in timesheet_entries:
        print(f"{entry['summary']}: {entry['duration']} minutes")
    
    total_minutes = sum(entry['duration'] for entry in timesheet_entries)
    total_hours = total_minutes / 60
    print(f"\nTotal Time: {total_hours:.2f} hours")
    print("\n++++++++++++++++++++++++ ")

    # Confirm date for the timesheet
    use_reference_date = input(f"Is this timesheet for {reference_date}? (y/n, default y): ").lower()
    use_reference_date = use_reference_date if use_reference_date else 'y'
    if use_reference_date != 'y':
        while True:
            date_input = input("Enter the date for this timesheet (dd/mm/yy): ")
            try:
                timesheet_date = datetime.strptime(date_input, "%d/%m/%y").strftime("%Y-%m-%d")
                break
            except ValueError:
                print("Invalid date format. Please use dd/mm/yy.")
    else:
        timesheet_date = reference_date

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

    if timesheet_date in diary:
        # Append new entries to existing date
        diary[timesheet_date]["tasks"].extend(diary_entry["tasks"])
        diary[timesheet_date]["total_duration"] += diary_entry["total_duration"]
        diary[timesheet_date]["total_hours"] += diary_entry["total_hours"]
    else:
        diary[timesheet_date] = diary_entry

    with open("j_diary.json", "w") as f:
        json.dump(diary, f, indent=2)

    print(f"Timesheet for {timesheet_date} has been saved to j_diary.json")

    # New code to ask about purging completed tasks
    purge_tasks = input("Would you like to purge all completed tasks for this date and earlier? (y/n, default n): ").lower()
    if purge_tasks == 'y':
        purge_completed_tasks(timesheet_date)

# The purge_completed_tasks function remains unchanged