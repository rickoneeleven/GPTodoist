# File: helper_timesheets.py
import os
import random
from datetime import datetime, timedelta, date # Import date explicitly
from typing import Union, List, Dict, Optional
from rich import print
from todoist_api_python.api import TodoistAPI

# Import specific functions/modules needed
import module_call_counter
import helper_todoist_long
import helper_todoist_part2
import state_manager
import helper_diary # Import helper_diary for constants

# --- Constants ---
# <<< KEPT: Application logic constants >>>
DEFAULT_TASK_DURATION = 5
DEFAULT_RAND_LOW = 420 # 7 hours
DEFAULT_RAND_HIGH = 480 # 8 hours
# Using constants from helper_diary for consistency
AUDIT_LOOKBACK_WEEKS = helper_diary.AUDIT_LOOKBACK_WEEKS
MIN_WEEKDAY_HOURS = helper_diary.MIN_WEEKDAY_HOURS

# --- Helper Functions ---

def prompt_user(message: str) -> str:
    """Displays a formatted prompt and gets user input."""
    print(f"[bold bright_magenta]{message}[/bold bright_magenta]", end=" ")
    return input()

# --- New Helper Function to find earliest outstanding date ---
def _find_earliest_outstanding_timesheet_date() -> Optional[date]:
    """
    Finds the earliest weekday date within the lookback period that is missing
    or has insufficient hours logged in the diary.
    """
    print("[cyan]Checking for earliest outstanding timesheet date...[/cyan]")
    diary_data = state_manager.get_diary_data()
    today = datetime.now().date()
    earliest_outstanding_date = None

    # Iterate backwards from yesterday
    for days_back in range(1, AUDIT_LOOKBACK_WEEKS * 7 + 1):
        current_date = today - timedelta(days=days_back)

        # Check only Mon-Fri
        if current_date.weekday() < 5:
            date_str = current_date.strftime("%Y-%m-%d")
            day_data = diary_data.get(date_str)
            is_outstanding = False

            if day_data is None:
                is_outstanding = True
            elif isinstance(day_data, dict):
                total_hours = day_data.get("total_hours")
                # Check if total_hours is missing, not a number, or less than minimum
                if total_hours is None or not isinstance(total_hours, (int, float)) or total_hours < MIN_WEEKDAY_HOURS:
                    is_outstanding = True
            else:
                # Entry exists but is not a dictionary (invalid data)
                is_outstanding = True
                print(f"[yellow]Warning: Invalid diary data type for {date_str} during outstanding check.[/yellow]")

            if is_outstanding:
                # We found an outstanding day. Since we iterate backwards,
                # the *last* one we find in the loop is the *earliest* date chronologically.
                earliest_outstanding_date = current_date
                # Continue loop to find even earlier dates

    if earliest_outstanding_date:
        print(f"[green]Found earliest outstanding date: {earliest_outstanding_date.strftime('%d/%m/%y')}[/green]")
    else:
        print("[cyan]No outstanding timesheet dates found within the lookback period.[/cyan]")

    return earliest_outstanding_date
# --- End New Helper Function ---

def get_timesheet_date() -> Optional[date]:
    """Gets and validates the timesheet date from user input, defaulting to earliest outstanding."""
    retries = 3
    for attempt in range(retries):
        try:
            # --- MODIFIED Prompt ---
            prompt = f"Timesheet date? (dd/mm/yy, Enter=earliest outstanding within {AUDIT_LOOKBACK_WEEKS} weeks):"
            date_input = prompt_user(prompt).strip()

            # --- MODIFIED Default Logic ---
            if not date_input:
                outstanding_date = _find_earliest_outstanding_timesheet_date()
                if outstanding_date:
                    return outstanding_date
                else:
                    # No outstanding found, default to yesterday
                    print("[yellow]No outstanding date found. Defaulting to yesterday.[/yellow]")
                    return datetime.now().date() - timedelta(days=1)
            # --- End Modified Default Logic ---

            # Keep original logic for explicit date entry
            # Allow 'yesterday' explicitly as well
            elif date_input.lower() == 'yesterday':
                 return datetime.now().date() - timedelta(days=1)
            else:
                 return datetime.strptime(date_input, "%d/%m/%y").date()

        except ValueError:
            print("[yellow]Invalid date format. Please use dd/mm/yy or press Enter.[/yellow]")
            # Decrement retries only on explicit invalid format, not on Enter failure
            if date_input: # Only decrement if user actually typed something invalid
                if attempt == retries - 1: # Check if it was the last attempt
                    print("[red]Too many invalid date attempts.[/red]")
                    return None
            else:
                 # If Enter was pressed and _find_earliest failed, allow retry without counting as invalid *format*
                 # However, if _find_earliest keeps failing, this could loop indefinitely if not handled.
                 # The current logic defaults to yesterday if None is returned, breaking the loop.
                 pass


    # Should only be reached if retries exhausted on explicit invalid format
    return None


def load_and_filter_tasks(timesheet_date: date) -> list:
    """Loads completed tasks via state_manager, filters by date, sorts, and re-indexes for display."""
    all_tasks = state_manager.get_completed_tasks_log()
    date_tasks = []
    parse_error_count = 0

    for task in all_tasks:
        if not isinstance(task, dict):
            continue

        datetime_str = task.get('datetime')
        if not isinstance(datetime_str, str):
            continue

        try:
            task_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            if task_datetime.date() == timesheet_date:
                date_tasks.append(task)
        except ValueError:
            parse_error_count += 1

    if parse_error_count > 0:
        print(f"[yellow]Warning: Could not parse datetime for {parse_error_count} tasks while filtering for timesheet.[/yellow]")

    try:
        date_tasks.sort(key=lambda x: datetime.strptime(x.get('datetime', ''), "%Y-%m-%d %H:%M:%S") if isinstance(x.get('datetime'), str) else datetime.min)
    except ValueError:
         print("[yellow]Warning: Error sorting tasks by datetime due to format issues. Order may be incorrect.[/yellow]")

    for i, task in enumerate(date_tasks):
        task['id'] = i + 1

    return date_tasks


def display_tasks_for_selection(tasks: list):
    """Displays the filtered tasks for the user to select."""
    if not tasks:
        print("\n[yellow]No completed tasks found for the selected date.[/yellow]")
        return

    print("\n[cyan]Completed tasks for selection:[/cyan]")
    for task in tasks:
         task_id = task.get('id', '?')
         task_dt = task.get('datetime', '?:??')
         task_name = task.get('task_name', 'Unknown Task')
         time_part = task_dt.split(' ')[-1] if ' ' in task_dt else task_dt
         print(f"  ID: {task_id}, Time: {time_part}, Task: {task_name}")


def get_selected_task_ids(filtered_tasks: list) -> list[int]:
    """Gets and validates task IDs (temporary display IDs) from user input."""
    if not filtered_tasks:
        return []

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
                 return list(dict.fromkeys(selected_ids))

        except ValueError:
            print("[yellow]Invalid input. Please enter numbers separated by commas.[/yellow]")


def get_task_details_from_user(task: dict) -> Optional[dict]:
    """Gets updated summary and duration for a selected task."""
    original_summary = task.get('task_name', 'Unknown Task')
    print(f"\nProcessing Task ID {task.get('id', '?')}: [white]{original_summary}[/white]")

    new_summary = original_summary
    change_summary = prompt_user("Change summary? (y/N):").strip().lower()
    if change_summary == 'y':
        entered_summary = prompt_user("Enter new summary:").strip()
        if entered_summary:
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

            return {
                "summary": new_summary,
                "duration": duration,
                "is_locked": is_locked,
                "datetime": task.get('datetime')
            }
        except ValueError:
            print("[yellow]Invalid number entered for duration.[/yellow]")


def get_additional_task_details(timesheet_date: date) -> Optional[dict]:
    """Gets details for tasks added manually."""
    print("\nAdding additional task...")
    summary = prompt_user("Enter task summary:").strip()
    if not summary:
        print("[yellow]Task summary cannot be empty. Skipping additional task.[/yellow]")
        return None

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
            break
        except ValueError:
            print("[yellow]Invalid number entered for duration.[/yellow]")

    while True:
        completion_time_str = prompt_user("Completion time? (HH:mm format):").strip()
        try:
            completion_time = datetime.strptime(completion_time_str, "%H:%M").time()
            task_datetime = datetime.combine(timesheet_date, completion_time)
            datetime_str = task_datetime.strftime("%Y-%m-%d %H:%M:%S")
            break
        except ValueError:
            print("[yellow]Invalid time format. Please use HH:mm (e.g., 14:30).[/yellow]")

    return {
        "summary": summary,
        "duration": duration,
        "is_locked": is_locked,
        "datetime": datetime_str
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
        if current_total != target_duration:
             print(f"[yellow]All tasks are locked. Total duration ({current_total}m) may not match target ({target_duration}m).[/yellow]")
        return timesheet_entries

    needed_adjustment = target_duration - current_total
    if needed_adjustment == 0:
        return timesheet_entries

    step = 5 if needed_adjustment > 0 else -5
    remaining_adjustment = abs(needed_adjustment)

    while remaining_adjustment > 0:
        adjusted_this_round = False
        # Ensure we iterate enough times if the step needs to be applied multiple times per task
        # Use a copy of the list for stable iteration if modifying durations directly affects future checks
        # In this specific logic, direct modification is likely fine.
        num_unlocked = len(unlocked_entries)
        if num_unlocked == 0: break # Safety check

        # Distribute adjustment somewhat evenly
        adjustment_per_task = remaining_adjustment // num_unlocked
        extra_adjustment = remaining_adjustment % num_unlocked

        applied_adjustment = 0
        for i, entry in enumerate(unlocked_entries):
            adjustment_to_apply = 0
            # Apply the base step first if needed
            if step != 0:
                # Check if adjustment is possible (don't make duration <= 0 when subtracting)
                if step < 0 and entry['duration'] <= abs(step):
                    continue # Cannot subtract from this task

                # Apply one step
                entry['duration'] += step
                applied_adjustment += abs(step)
                adjusted_this_round = True

                # Break if this single step satisfied remaining_adjustment
                if applied_adjustment >= remaining_adjustment:
                    break


        # If after applying one step to all possible tasks, we still need adjustment, loop again.
        # Update remaining_adjustment based on what was actually applied.
        remaining_adjustment -= applied_adjustment

        # If no adjustments were made in a round (e.g., all tasks too short), break
        if not adjusted_this_round and remaining_adjustment > 0:
            print("[yellow]Warning: Could not fully adjust durations to target (tasks may be too short or step size issue).[/yellow]")
            break

    final_total = sum(entry['duration'] for entry in timesheet_entries)
    if final_total != target_duration:
         print(f"[yellow]Final adjusted duration ({final_total} mins) differs from target ({target_duration} mins). Check task lengths/locks.[/yellow]")
    elif needed_adjustment != 0: # Only print success if adjustment happened
         print("[green]Durations adjusted successfully to meet target.[/green]")

    return timesheet_entries


def save_timesheet_to_diary(timesheet_entries: list, timesheet_date: date):
    """Formats and saves the timesheet entries into the diary file using state_manager."""
    entries_to_save = []
    for entry in timesheet_entries:
        saved_entry = {
            "summary": entry.get('summary', 'Unknown Task'),
            "duration": entry.get('duration', 0)
        }
        entries_to_save.append(saved_entry)

    total_duration = sum(entry['duration'] for entry in entries_to_save)
    total_hours = total_duration / 60

    timesheet_date_str = timesheet_date.strftime("%Y-%m-%d")

    diary_update_payload = {
        "tasks": entries_to_save,
        "total_duration": total_duration,
        "total_hours": round(total_hours, 2)
    }

    if state_manager.update_diary_entry(timesheet_date_str, diary_update_payload):
        print(f"\n[green]Timesheet for {timesheet_date_str} saved successfully.[/green]")
    else:
        print(f"\n[red]Failed to save timesheet for {timesheet_date_str}.[/red]")


def update_objective_for_today():
    """Handles displaying the last objective and prompting user to update today's, using state_manager."""
    today = datetime.now().date()
    # <<< MODIFIED: Use lookback constant defined in this file >>>
    lookback = AUDIT_LOOKBACK_WEEKS * 7 # Calculate lookback days from weeks
    last_objective, last_objective_date = state_manager.find_most_recent_objective(today, lookback_days=lookback)

    if last_objective:
        if last_objective_date:
            days_ago = (today - last_objective_date).days
            day_word = "day" if days_ago == 1 else "days"
            date_str_formatted = last_objective_date.strftime('%A, %d %B')

            if days_ago == 0:
                print(f"\n[bold]Current Objective[/bold] (Set today):")
            else:
                print(f"\n[bold]Most Recent Objective[/bold] (Set {days_ago} {day_word} ago - {date_str_formatted}):")
            print(f"[yellow]{last_objective}[/yellow]")
        else:
             print(f"\n[bold]Current Objective[/bold] (Date Unknown):")
             print(f"[yellow]{last_objective}[/yellow]")
    else:
        print("\n[yellow]No recent objective found in diary.[/yellow]")
        last_objective = None

    update_choice = prompt_user("Update objective for today? (Y/n):").lower().strip()
    new_objective_to_set = None

    if update_choice != 'n':
        entered_objective = prompt_user("Enter new objective for today:").strip()
        if entered_objective:
            new_objective_to_set = entered_objective
        else:
            print("[yellow]No new objective entered. Keeping previous objective (if any).[/yellow]")
    else:
         if last_objective:
              print("[cyan]Keeping the most recent objective.[/cyan]")
         else:
              print("[cyan]No objective will be set for today.[/cyan]")

    if new_objective_to_set is not None:
        state_manager.update_todays_objective(new_objective_to_set)

# --- Main Timesheet Function ---

def timesheet():
    """Main function orchestrating the timesheet creation process."""
    try:
        try:
            api_key = os.environ.get("TODOIST_API_KEY")
            if not api_key:
                 print("[red]TODOIST_API_KEY environment variable not set.[/red]")
                 return
            api = TodoistAPI(api_key)
        except Exception as api_init_error:
            print(f"[red]Failed to initialize Todoist API: {api_init_error}[/red]")
            return

        # 1. Get Date (Uses updated logic)
        timesheet_date = get_timesheet_date()
        if not timesheet_date: return

        # 2. Load Data
        filtered_tasks = load_and_filter_tasks(timesheet_date)

        # 3. Task Selection
        display_tasks_for_selection(filtered_tasks)
        selected_ids = get_selected_task_ids(filtered_tasks)

        # 4. Process Selected Tasks
        timesheet_entries = []
        task_map = {task.get('id'): task for task in filtered_tasks if isinstance(task.get('id'), int)}
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
                break

        if not timesheet_entries:
            print("[yellow]No tasks selected or added. Timesheet process aborted.[/yellow]")
            return

        # 6. Sort Entries by Time
        try:
            timesheet_entries.sort(key=lambda x: datetime.strptime(x.get('datetime', ''), "%Y-%m-%d %H:%M:%S") if isinstance(x.get('datetime'), str) else datetime.min)
        except ValueError:
             print("[yellow]Warning: Error sorting timesheet entries by datetime. Order may be incorrect.[/yellow]")

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
        save_timesheet_to_diary(timesheet_entries, timesheet_date)

        # 10. Display Long-Term Tasks
        try:
            helper_todoist_long.display_tasks(api)
        except Exception as e:
            print(f"[red]Error displaying long-term tasks: {e}[/red]")

        # 11. Display Current Tasks
        try:
            print("\n[cyan]Refreshing current Todoist tasks view...[/cyan]")
            helper_todoist_part2.display_todoist_tasks(api)
        except Exception as e:
            print(f"[red]Error displaying current Todoist tasks: {e}[/red]")

        # 12. Update Today's Objective
        update_objective_for_today()

    except Exception as e:
        print(f"\n[bold red]An unexpected error occurred during the timesheet process:[/bold red]")
        print(f"[red]{e}[/red]")
        import traceback
        traceback.print_exc()

# Apply call counter decorator
if 'module_call_counter' in globals() and hasattr(module_call_counter, 'apply_call_counter_to_all'):
     module_call_counter.apply_call_counter_to_all(globals(), __name__)
else:
     print("[yellow]Warning: module_call_counter not fully available in helper_timesheets.[/yellow]")