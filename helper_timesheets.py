import json
from datetime import datetime, timedelta
from rich import print

def timesheet():
    # Ask user which day to reference
    use_yesterday = input("Would you like to reference yesterday's completed tasks? (y/n): ").lower() == 'y'
    
    if use_yesterday:
        reference_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        while True:
            date_input = input("Enter the date to reference (dd/mm format): ")
            try:
                reference_date = datetime.strptime(date_input + "/" + str(datetime.now().year), "%d/%m/%Y").strftime("%Y-%m-%d")
                break
            except ValueError:
                print("Invalid date format. Please use dd/mm.")

    # Load completed tasks
    with open("j_todays_completed_tasks.json", "r") as f:
        completed_tasks = json.load(f)

    # Filter tasks for the reference date
    reference_tasks = [task for task in completed_tasks if task['datetime'].startswith(reference_date)]

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
            duration = int(input("Enter time spent in minutes: "))
            timesheet_entries.append({"summary": summary, "duration": duration})

    # Ask for additional tasks
    while input("Would you like to add any additional tasks? (y/n): ").lower() == 'y':
        summary = input("Enter task summary: ")
        duration = int(input("Enter time spent in minutes: "))
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
    print("\nFinal Timesheet:")
    for entry in timesheet_entries:
        print(f"{entry['summary']}: {entry['duration']} minutes")
    
    total_minutes = sum(entry['duration'] for entry in timesheet_entries)
    total_hours = total_minutes / 60
    print(f"\nTotal Time: {total_hours:.2f} hours")

    # Confirm date for the timesheet
    use_reference_date = input(f"Is this timesheet for {reference_date}? (y/n): ").lower() == 'y'
    if not use_reference_date:
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
        timesheet_date: {
            "tasks": timesheet_entries,
            "total_duration": total_minutes,
            "total_hours": round(total_hours, 2)
        }
    }

    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
    except FileNotFoundError:
        diary = {}

    diary.update(diary_entry)

    with open("j_diary.json", "w") as f:
        json.dump(diary, f, indent=2)

    print(f"Timesheet for {timesheet_date} has been saved to j_diary.json")