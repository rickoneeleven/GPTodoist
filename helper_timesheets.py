# File: helper_timesheets.py
import json, random, os
from datetime import datetime, timedelta
# <<< CHANGE: Import Union >>>
from typing import Union
from rich import print
from todoist_api_python.api import TodoistAPI # Keep for potential future use or context
import traceback # For logging errors

# Import specific functions/modules needed
import module_call_counter
import helper_todoist_long
import helper_todoist_part2
from helper_diary import find_most_recent_objective # Import from helper_diary

# --- Constants ---
COMPLETED_TASKS_FILENAME = "j_todays_completed_tasks.json"
DIARY_FILENAME = "j_diary.json"
DEFAULT_TASK_DURATION = 5
DEFAULT_RAND_LOW = 420 # 7 hours
DEFAULT_RAND_HIGH = 480 # 8 hours

# --- Helper Functions ---

def _load_json(filename: str, default_value=None):
    """Loads JSON data from a file, handling errors and defaults."""
    if not os.path.exists(filename):
        # print(f"[yellow]File not found: {filename}[/yellow]") # Less verbose
        return default_value if default_value is not None else {}

    try:
        with open(filename, "r") as f:
            data = json.load(f)
        # Basic type validation if default value suggests a type
        if default_value is not None and not isinstance(data, type(default_value)):
             print(f"[red]Error: Expected {type(default_value)} in {filename}, found {type(data)}. Returning default.[/red]")
             return default_value
        return data
    except json.JSONDecodeError:
        print(f"[red]Error reading JSON from {filename}. File might be corrupted.[/red]")
        return default_value if default_value is not None else {}
    except IOError as e:
        print(f"[red]Error accessing file {filename}: {e}[/red]")
        return default_value if default_value is not None else {}
    except Exception as e:
        print(f"[red]An unexpected error occurred loading {filename}: {e}[/red]")
        traceback.print_exc()
        return default_value if default_value is not None else {}

def _save_json(filename: str, data: dict | list):
    """Saves data to a JSON file."""
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except IOError as e:
        print(f"[red]Error writing to file {filename}: {e}[/red]")
        return False
    except Exception as e:
        print(f"[red]An unexpected error occurred saving {filename}: {e}[/red]")
        traceback.print_exc()
        return False

def prompt_user(message: str) -> str:
    """Displays a formatted prompt and gets user input."""
    # Using simple input for robustness, rich print only for display
    print(f"[bold bright_magenta]{message}[/bold bright_magenta]", end=" ")
    return input()

# <<< CHANGE: Use Union in the type hint >>>
def get_timesheet_date() -> Union[datetime.date, None]:
    """Gets and validates the timesheet date from user input."""
    retries = 3
    for _ in range(retries):
        try:
            date_input = prompt_user("Timesheet date? (dd/mm/yy, Enter=yesterday):").strip()
            if not date_input or date_input.lower() == 'yesterday':
                return datetime.now().date() - timedelta(days=1)
            return datetime.strptime(date_input, "%d/%m/%y").date()
        except ValueError:
            print("[yellow]Invalid date format. Please use dd/mm/yy or press Enter for yesterday.[/yellow]")
    print("[red]Too many invalid date attempts.[/red]")
    return None

def load_and_filter_tasks(timesheet_date: datetime.date) -> list:
    """Loads, filters, sorts, and re-indexes completed tasks for the specified date."""
    all_tasks = _load_json(COMPLETED_TASKS_FILENAME, default_value=[])
    if not isinstance(all_tasks, list):
        print(f"[red]Invalid data in {COMPLETED_TASKS_FILENAME}, cannot load tasks.[/red]")
        return []

    date_tasks = []
    other_tasks = []
    parse_error_count = 0

    for task in all_tasks:
        if not isinstance(task, dict):
            print(f"[yellow]Skipping invalid entry in completed tasks: {task}[/yellow]")
            other_tasks.append(task) # Keep invalid tasks in the 'other' list
            continue

        datetime_str = task.get('datetime')
        if not isinstance(datetime_str, str):
            print(f"[yellow]Skipping task with missing/invalid datetime: {task.get('task_name', 'N/A')}[/yellow]")
            other_tasks.append(task) # Keep task if date is invalid
            continue

        try:
            task_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            if task_datetime.date() == timesheet_date:
                date_tasks.append(task)
            else:
                other_tasks.append(task)
        except ValueError:
            parse_error_count += 1
            other_tasks.append(task) # Keep tasks with parse errors

    if parse_error_count > 0:
        print(f"[yellow]Could not parse datetime for {parse_error_count} tasks.[/yellow]")

    # Sort tasks for the specific date
    date_tasks.sort(key=lambda x: datetime.strptime(x.get('datetime', ''), "%Y-%m-%d %H:%M:%S") if x.get('datetime') else datetime.min)

    # Re-index the tasks for the specific date (1-based index)
    for i, task in enumerate(date_tasks):
        task['id'] = i + 1 # Add/Update 'id' for display/selection

    # Recombine and save if changes occurred (re-indexing)
    updated_all_tasks = other_tasks + date_tasks
    if len(updated_all_tasks) == len(all_tasks): # Check if list content actually changed due to re-indexing etc.
         # Only save if re-indexing actually happened or errors occurred requiring rewrite
         if any(task['id'] != i+1 for i, task in enumerate(date_tasks)) or parse_error_count > 0:
             _save_json(COMPLETED_TASKS_FILENAME, updated_all_tasks)
         # else: print("[dim]No changes to completed tasks file needed.[/dim]") # Debug

    return date_tasks # Return only the tasks for the specified date

def display_tasks_for_selection(tasks: list):
    """Displays the filtered tasks for the user to select."""
    if not tasks:
        print("\n[yellow]No completed tasks found for the selected date.[/yellow]")
        return

    print("\n[cyan]Completed tasks for selection:[/cyan]")
    for task in tasks:
         # Safely access keys
         task_id = task.get('id', '?')
         task_dt = task.get('datetime', '?:??')
         task_name = task.get('task_name', 'Unknown Task')
         print(f"  ID: {task_id}, Time: {task_dt.split(' ')[-1]}, Task: {task_name}") # Show time part only


def get_selected_task_ids(filtered_tasks: list) -> list[int]:
    """Gets and validates task IDs from user input."""
    if not filtered_tasks:
        return [] # No tasks to select

    valid_ids = {task.get('id') for task in filtered_tasks if isinstance(task.get('id'), int)}
    if not valid_ids:
        print("[yellow]No tasks with valid IDs available for selection.[/yellow]")
        return []

    while True:
        try:
            id_input = prompt_user("Enter task IDs for timesheet (comma-separated, Enter=skip):").strip()
            if not id_input:
                return []

            selected_ids = []
            raw_ids = [id_str.strip() for id_str in id_input.split(',') if id_str.strip()]
            all_valid = True
            for id_str in raw_ids:
                 num_id = int(id_str)
                 if num_id in valid_ids:
                     selected_ids.append(num_id)
                 else:
                     print(f"[yellow]ID {num_id} is not a valid task ID for this date.[/yellow]")
                     all_valid = False

            if all_valid:
                 # Remove duplicates while preserving order (if needed, though set conversion is easier)
                 return list(dict.fromkeys(selected_ids)) # Order-preserving unique IDs
            # If not all valid, loop continues

        except ValueError:
            print("[yellow]Invalid input. Please enter numbers separated by commas.[/yellow]")


def get_task_details_from_user(task: dict) -> Union[dict, None]: # <<< CHANGE: Use Union >>>
    """Gets updated summary and duration for a selected task."""
    original_summary = task.get('task_name', 'Unknown Task')
    print(f"\nProcessing Task ID {task.get('id', '?')}: [white]{original_summary}[/white]")

    # Get task summary
    new_summary = original_summary
    change_summary = prompt_user("Change summary? (y/N):").strip().lower()
    if change_summary == 'y':
        entered_summary = prompt_user("Enter new summary:").strip()
        if entered_summary: # Only update if something was entered
             # Warn if numbers are present, requires confirmation
             if any(char.isdigit() for char in entered_summary):
                 confirm_change = prompt_user(f"[red]New summary '{entered_summary}' contains numbers. Confirm? (y/N):[/red]").strip().lower()
                 if confirm_change == 'y':
                     new_summary = entered_summary
                 else:
                     print("[yellow]Summary change cancelled.[/yellow]")
             else:
                 new_summary = entered_summary
        else:
             print("[yellow]No new summary entered, keeping original.[/yellow]")


    # Get task duration
    while True:
        try:
            duration_input = prompt_user(f"Time spent in minutes? (Enter={DEFAULT_TASK_DURATION}, wrap in () to lock):").strip()
            is_locked = False
            if duration_input.startswith('(') and duration_input.endswith(')'):
                is_locked = True
                duration_input = duration_input[1:-1].strip() # Get value inside parentheses

            if not duration_input:
                duration = DEFAULT_TASK_DURATION
            else:
                duration = int(duration_input)

            if duration <= 0:
                print(f"[yellow]Duration must be positive. Using default {DEFAULT_TASK_DURATION}.[/yellow]")
                duration = DEFAULT_TASK_DURATION

            # Return collected details
            return {
                "summary": new_summary,
                "duration": duration,
                "is_locked": is_locked,
                "datetime": task.get('datetime') # Keep original datetime for sorting
            }
        except ValueError:
            print("[yellow]Invalid number entered for duration.[/yellow]")
            # Loop continues to re-prompt

def get_additional_task_details(timesheet_date: datetime.date) -> Union[dict, None]: # <<< CHANGE: Use Union >>>
    """Gets details for tasks added manually."""
    print("\nAdding additional task...")
    summary = prompt_user("Enter task summary:").strip()
    if not summary:
        print("[yellow]Task summary cannot be empty. Skipping additional task.[/yellow]")
        return None

    # Get duration
    while True:
        try:
            duration_input = prompt_user(f"Time spent in minutes? (Enter={DEFAULT_TASK_DURATION}, wrap in () to lock):").strip()
            is_locked = False
            if duration_input.startswith('(') and duration_input.endswith(')'):
                is_locked = True
                duration_input = duration_input[1:-1].strip()

            if not duration_input:
                duration = DEFAULT_TASK_DURATION
            else:
                duration = int(duration_input)

            if duration <= 0:
                print(f"[yellow]Duration must be positive. Using default {DEFAULT_TASK_DURATION}.[/yellow]")
                duration = DEFAULT_TASK_DURATION
            break # Exit duration loop
        except ValueError:
            print("[yellow]Invalid number entered for duration.[/yellow]")

    # Get completion time
    while True:
        completion_time_str = prompt_user("Completion time? (HH:mm format):").strip()
        try:
            completion_time = datetime.strptime(completion_time_str, "%H:%M").time()
            task_datetime = datetime.combine(timesheet_date, completion_time)
            datetime_str = task_datetime.strftime("%Y-%m-%d %H:%M:%S") # Ensure seconds are included
            break # Exit time loop
        except ValueError:
            print("[yellow]Invalid time format. Please use HH:mm (e.g., 14:30).[/yellow]")

    return {
        "summary": summary,
        "duration": duration,
        "is_locked": is_locked,
        "datetime": datetime_str # Store formatted string
    }

def get_random_target_duration() -> int:
    """Gets random range, calculates target duration (multiple of 5)."""
    while True:
        try:
            low_input = prompt_user(f"Target minutes range - low? (Enter={DEFAULT_RAND_LOW}):").strip()
            rand_low = int(low_input) if low_input else DEFAULT_RAND_LOW

            if rand_low < 0:
                print("[yellow]Low value cannot be negative.[/yellow]")
                continue

            high_input = prompt_user(f"Target minutes range - high? (Enter={DEFAULT_RAND_HIGH}):").strip()
            rand_high = int(high_input) if high_input else DEFAULT_RAND_HIGH

            if rand_high <= rand_low:
                print("[yellow]High value must be greater than low value.[/yellow]")
                continue

            # Generate random duration and round to nearest 5 minutes
            target = random.randint(rand_low, rand_high)
            target_duration = round(target / 5) * 5
            print(f"[cyan]Target total duration: {target_duration} minutes ({target_duration/60:.2f} hours).[/cyan]")
            return target_duration

        except ValueError:
            print("[yellow]Invalid number entered. Please enter integers.[/yellow]")


def adjust_durations(timesheet_entries: list, target_duration: int) -> list:
    """Adjusts unlocked task durations to meet the target total duration."""
    locked_duration = sum(entry['duration'] for entry in timesheet_entries if entry.get('is_locked'))
    unlocked_entries = [entry for entry in timesheet_entries if not entry.get('is_locked')]
    unlocked_duration = sum(entry['duration'] for entry in unlocked_entries)
    current_total = locked_duration + unlocked_duration

    if not unlocked_entries:
        print("[yellow]All tasks are locked. Total duration may not match target.[/yellow]")
        return timesheet_entries # No unlocked tasks to adjust

    needed_adjustment = target_duration - current_total
    if needed_adjustment == 0:
        return timesheet_entries # Already at target

    # --- Adjustment Logic ---
    # Distribute change +/- 5 mins at a time across unlocked tasks
    step = 5 if needed_adjustment > 0 else -5
    remaining_adjustment = abs(needed_adjustment)

    while remaining_adjustment > 0:
        adjusted_this_round = False
        # Iterate through unlocked tasks to apply adjustment step
        for entry in unlocked_entries:
            if remaining_adjustment <= 0: break

            # Check if adjustment is possible (don't make duration <= 0 when subtracting)
            if step < 0 and entry['duration'] <= abs(step):
                continue # Cannot subtract from this task

            entry['duration'] += step
            remaining_adjustment -= abs(step)
            adjusted_this_round = True

        # If no tasks could be adjusted in a round (e.g., all too small to subtract from), break to prevent infinite loop
        if not adjusted_this_round:
            print("[yellow]Warning: Could not fully adjust durations to target (tasks may be too short).[/yellow]")
            break

    # Verify final total (for debugging/info)
    final_total = sum(entry['duration'] for entry in timesheet_entries)
    if final_total != target_duration and remaining_adjustment > 0:
         print(f"[yellow]Final adjusted duration ({final_total} mins) differs from target ({target_duration} mins).[/yellow]")
    elif final_total == target_duration:
         print("[green]Durations adjusted successfully to meet target.[/green]")


    return timesheet_entries


def save_timesheet_to_diary(timesheet_entries: list, timesheet_date: datetime.date, diary_data: dict): # Removed current_objective param
    """Formats and saves the timesheet entries into the diary file."""
    # Prepare entries for saving (remove temporary keys)
    entries_to_save = []
    for entry in timesheet_entries:
        saved_entry = {
            "summary": entry.get('summary', 'Unknown Task'),
            "duration": entry.get('duration', 0)
            # 'datetime' and 'is_locked' are not saved
        }
        entries_to_save.append(saved_entry)

    total_duration = sum(entry['duration'] for entry in entries_to_save)
    total_hours = total_duration / 60

    timesheet_date_str = timesheet_date.strftime("%Y-%m-%d")

    # Create or update the diary entry for the date
    diary_entry = diary_data.get(timesheet_date_str, {}) # Get existing or new dict
    if not isinstance(diary_entry, dict): # Ensure it's a dict
        print(f"[yellow]Overwriting invalid diary entry for {timesheet_date_str}.[/yellow]")
        diary_entry = {}

    diary_entry["tasks"] = entries_to_save
    diary_entry["total_duration"] = total_duration
    diary_entry["total_hours"] = round(total_hours, 2)

    # Objective for the timesheet_date is preserved automatically if it existed
    # because we loaded it into diary_data and are only updating specific keys here.

    diary_data[timesheet_date_str] = diary_entry

    if _save_json(DIARY_FILENAME, diary_data):
        print(f"\n[green]Timesheet for {timesheet_date_str} saved successfully to {DIARY_FILENAME}[/green]")
    else:
        print(f"\n[red]Failed to save timesheet for {timesheet_date_str} to {DIARY_FILENAME}[/red]")


def update_objective_for_today(diary_data: dict):
    """Handles displaying the last objective and prompting user to update today's."""
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")

    # 1. Find and display the most recent objective
    last_objective, last_objective_date = find_most_recent_objective(diary_data, today)

    if last_objective:
        days_ago = (today - last_objective_date).days
        day_word = "day" if days_ago == 1 else "days"
        date_str_formatted = last_objective_date.strftime('%A, %d %B')

        if days_ago == 0:
            print(f"\n[bold]Current Objective[/bold] (Set today):")
        else:
            print(f"\n[bold]Most Recent Objective[/bold] (Set {days_ago} {day_word} ago - {date_str_formatted}):")
        print(f"[yellow]{last_objective}[/yellow]")
    else:
        print("\n[yellow]No recent objective found in diary.[/yellow]")
        last_objective = None # Ensure it's None if not found

    # 2. Ask user if they want to update (Default is YES)
    update_choice = prompt_user("Update objective for today? (Y/n):").lower().strip()

    new_objective = last_objective # Default to keeping the last one

    if update_choice != 'n': # Treat Enter or 'y' as yes
        entered_objective = prompt_user("Enter new objective for today:").strip()
        if entered_objective:
            new_objective = entered_objective
            print(f"Objective for today set to: [gold1]{new_objective}[/gold1]")
        else:
            print("[yellow]No new objective entered. Keeping previous objective (if any).[/yellow]")
            # new_objective remains last_objective
    else: # User explicitly entered 'n'
         if last_objective:
              print("[cyan]Keeping the most recent objective.[/cyan]")
         else:
              print("[cyan]No objective set for today.[/cyan]")
         # new_objective remains last_objective


    # 3. Save the final objective under today's date string
    # Ensure today's entry exists as a dict
    if today_str not in diary_data or not isinstance(diary_data.get(today_str), dict):
        diary_data[today_str] = {}

    # Only save if there's actually an objective to save
    if new_objective is not None:
        diary_data[today_str]['overall_objective'] = new_objective
        _save_json(DIARY_FILENAME, diary_data) # Save the updated diary data
        # print(f"[green]Objective for {today_str} saved.[/green]") # Optional confirmation
    elif today_str in diary_data and 'overall_objective' in diary_data[today_str]:
         # If user chose not to update AND there was no previous objective,
         # remove any potentially existing objective for today.
         del diary_data[today_str]['overall_objective']
         if not diary_data[today_str]: # Remove empty dict if objective was the only key
             del diary_data[today_str]
         _save_json(DIARY_FILENAME, diary_data)
         print("[cyan]Cleared objective for today.[/cyan]")


# --- Main Timesheet Function ---

def timesheet():
    """Main function orchestrating the timesheet creation process."""
    try:
        # Initialize API (needed for displaying tasks at the end)
        # Consider passing API object if called from elsewhere, or making it global/singleton if appropriate
        try:
            api_key = os.environ.get("TODOIST_API_KEY")
            if not api_key:
                 print("[red]TODOIST_API_KEY environment variable not set.[/red]")
                 return # Cannot proceed without API key for final steps
            api = TodoistAPI(api_key)
        except Exception as api_init_error:
            print(f"[red]Failed to initialize Todoist API: {api_init_error}[/red]")
            return


        # 1. Get Date
        timesheet_date = get_timesheet_date()
        if not timesheet_date: return # Exit if date selection failed

        # 2. Load Data
        filtered_tasks = load_and_filter_tasks(timesheet_date)
        diary_data = _load_json(DIARY_FILENAME, default_value={})

        # 3. Task Selection
        display_tasks_for_selection(filtered_tasks)
        selected_ids = get_selected_task_ids(filtered_tasks)

        # 4. Process Selected Tasks
        timesheet_entries = []
        task_map = {task.get('id'): task for task in filtered_tasks if task.get('id')} # Map ID to task dict
        for task_id in selected_ids:
            task = task_map.get(task_id)
            if task:
                entry_details = get_task_details_from_user(task)
                if entry_details:
                    timesheet_entries.append(entry_details)

        # 5. Process Additional Tasks
        while True:
            add_more = prompt_user("Add another task manually? (y/N):").lower().strip()
            if add_more == 'y':
                additional_entry = get_additional_task_details(timesheet_date)
                if additional_entry:
                    timesheet_entries.append(additional_entry)
                    lock_status = "(locked)" if additional_entry.get('is_locked') else ""
                    print(f"  Added: {additional_entry['summary']} ({additional_entry['duration']} mins) {lock_status}")
            else:
                break # Exit additional task loop

        if not timesheet_entries:
            print("[yellow]No tasks selected or added. Timesheet process aborted.[/yellow]")
            return

        # 6. Sort Entries by Time
        timesheet_entries.sort(key=lambda x: datetime.strptime(x.get('datetime', '1900-01-01 00:00:00'), "%Y-%m-%d %H:%M:%S"))

        # 7. Adjust Durations
        target_duration = get_random_target_duration()
        timesheet_entries = adjust_durations(timesheet_entries, target_duration)

        # 8. Display Final Timesheet
        print("\n[bold green] --- Final Timesheet --- [/bold green]")
        total_duration = 0
        for entry in timesheet_entries:
            lock_status = "[red](locked)[/red]" if entry.get('is_locked') else ""
            summary = entry.get('summary', 'Unknown Task')
            duration = entry.get('duration', 0)
            print(f"  {summary}: {duration} minutes {lock_status}")
            total_duration += duration
        total_hours = total_duration / 60
        print(f"\nTotal Time: {total_duration} minutes ({total_hours:.2f} hours)")
        print("[bold green]-------------------------[/bold green]")

        # 9. Save Timesheet
        save_timesheet_to_diary(timesheet_entries, timesheet_date, diary_data) # Pass updated diary_data

        # 10. Display Long-Term Tasks
        try:
            helper_todoist_long.display_tasks(api)
        except Exception as e:
            print(f"[red]Error displaying long-term tasks: {e}[/red]")

        # 11. Display Current Tasks (Optional - maybe remove if too noisy?)
        try:
            print("\n[cyan]Refreshing current Todoist tasks view...[/cyan]")
            helper_todoist_part2.display_todoist_tasks(api)
        except Exception as e:
            print(f"[red]Error displaying current Todoist tasks: {e}[/red]")

        # 12. Update Today's Objective (Uses updated diary_data)
        # Reload diary data *after* saving the timesheet to get the latest state
        updated_diary_data = _load_json(DIARY_FILENAME, default_value={})
        update_objective_for_today(updated_diary_data)

    except Exception as e:
        print(f"\n[bold red]An unexpected error occurred during the timesheet process:[/bold red]")
        print(f"[red]{e}[/red]")
        traceback.print_exc() # Log stack trace for debugging
        # Optionally offer retry
        # retry = prompt_user("Would you like to try again? (y/N):").lower().strip()
        # if retry == 'y':
        #     timesheet()

# Apply call counter decorator
if 'module_call_counter' in globals() and hasattr(module_call_counter, 'apply_call_counter_to_all'):
     module_call_counter.apply_call_counter_to_all(globals(), __name__)
else:
     print("[yellow]Warning: module_call_counter not fully available in helper_timesheets.[/yellow]")