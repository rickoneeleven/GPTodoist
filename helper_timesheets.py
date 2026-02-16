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
import helper_parse # <<< ADDED: Import helper_parse for multi-line input
from helper_effects import _clear_screen as _clear_screen

# --- Exceptions ---
class ResetTimesheet(Exception):
    """Raised to signal a user-requested reset of the timesheet process."""

# --- Constants ---
DEFAULT_TASK_DURATION = 5
DEFAULT_RAND_LOW = 420 # 7 hours
DEFAULT_RAND_HIGH = 480 # 8 hours
# Using constants from helper_diary for consistency
AUDIT_LOOKBACK_WEEKS = helper_diary.AUDIT_LOOKBACK_WEEKS
MIN_WEEKDAY_HOURS = helper_diary.MIN_WEEKDAY_HOURS

# --- Helper Functions ---

def prompt_user(message: str) -> str:
    """Displays a formatted prompt and gets single-line user input."""
    print(f"[bold bright_magenta]{message}[/bold bright_magenta]", end=" ")
    return input()

def _find_earliest_outstanding_timesheet_date() -> Optional[date]:
    """
    Finds the earliest weekday date within the lookback period that is missing
    or has insufficient hours logged in the diary.
    """
    print("[cyan]Checking for earliest outstanding timesheet date...[/cyan]")
    diary_data = state_manager.get_diary_data()
    today = datetime.now().date()
    earliest_outstanding_date = None

    for days_back in range(1, AUDIT_LOOKBACK_WEEKS * 7 + 1):
        current_date = today - timedelta(days=days_back)

        if current_date.weekday() < 5: # Check only Mon-Fri
            date_str = current_date.strftime("%Y-%m-%d")
            day_data = diary_data.get(date_str)
            is_outstanding = False

            if day_data is None:
                is_outstanding = True
            elif isinstance(day_data, dict):
                total_hours = day_data.get("total_hours")
                if total_hours is None or not isinstance(total_hours, (int, float)) or total_hours < MIN_WEEKDAY_HOURS:
                    is_outstanding = True
            else:
                is_outstanding = True
                print(f"[yellow]Warning: Invalid diary data type for {date_str} during outstanding check.[/yellow]")

            if is_outstanding:
                earliest_outstanding_date = current_date

    if earliest_outstanding_date:
        print(f"[green]Found earliest outstanding date: {earliest_outstanding_date.strftime('%d/%m/%y')}[/green]")
    else:
        print("[cyan]No outstanding timesheet dates found within the lookback period.[/cyan]")

    return earliest_outstanding_date

def get_timesheet_date() -> Optional[date]:
    """Gets and validates the timesheet date from user input, defaulting to earliest outstanding."""
    retries = 3
    for attempt in range(retries):
        try:
            prompt_message = f"Timesheet date? (dd/mm/yy, Enter=earliest outstanding within {AUDIT_LOOKBACK_WEEKS} weeks):"
            date_input = prompt_user(prompt_message).strip()

            if not date_input:
                outstanding_date = _find_earliest_outstanding_timesheet_date()
                if outstanding_date:
                    return outstanding_date
                else:
                    print("[yellow]No outstanding date found. Defaulting to yesterday.[/yellow]")
                    return datetime.now().date() - timedelta(days=1)
            elif date_input.lower() == 'yesterday':
                 return datetime.now().date() - timedelta(days=1)
            else:
                 return datetime.strptime(date_input, "%d/%m/%y").date()

        except ValueError:
            print("[yellow]Invalid date format. Please use dd/mm/yy or press Enter.[/yellow]")
            if date_input:
                if attempt == retries - 1:
                    print("[red]Too many invalid date attempts.[/red]")
                    return None
            # If Enter was pressed and _find_earliest failed, this loop structure implicitly retries
            # or defaults, which is handled.

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
        task['id'] = i + 1 # Assign a temporary display ID

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
            all_valid_input = True
            for id_str in raw_ids:
                 num_id = int(id_str)
                 if num_id in valid_ids:
                     selected_ids.append(num_id)
                 else:
                     print(f"[yellow]ID {num_id} is not a valid task ID for this date.[/yellow]")
                     all_valid_input = False
            
            if all_valid_input: # Only return if all provided IDs were valid after parsing
                 return list(dict.fromkeys(selected_ids)) # Remove duplicates while preserving order

        except ValueError:
            print("[yellow]Invalid input. Please enter numbers separated by commas.[/yellow]")


def sequential_select_task_ids(filtered_tasks: list) -> list[int]:
    """Sequential selection UX: clear screen, show one task, default include on Enter/y."""
    if not filtered_tasks:
        return []

    selected_ids: list[int] = []
    total = len(filtered_tasks)

    for idx, task in enumerate(filtered_tasks, start=1):
        # Clear the screen to focus on a single task
        try:
            _clear_screen()
        except Exception:
            # Fallback ANSI clear if helper effects is not supported
            print("\033[2J\033[H", end="")

        task_id = task.get('id', '?')
        task_dt = task.get('datetime', '')
        task_name = task.get('task_name', 'Unknown Task')
        time_part = task_dt.split(' ')[-1] if isinstance(task_dt, str) and ' ' in task_dt else task_dt

        print(f"[cyan]Completed tasks {idx}/{total}[/cyan]")
        print("[bold]Include this task in timesheet?[/bold] [dim](Enter=Yes, n=No, r=reset)[/dim]")
        print(f"  Time: [white]{time_part or '?'}[/white]")
        print(f"  Task: [white]{task_name}[/white]")

        while True:
            choice = prompt_user("Include? (Enter=y / n / r=reset):").strip().lower()
            if choice in ("", "y", "yes"):
                if isinstance(task_id, int):
                    selected_ids.append(task_id)
                break
            if choice in ("n", "no"):
                break
            if choice in ("r", "reset"):
                confirm = prompt_user("Reset timesheet process and start again? (y/N):").strip().lower()
                if confirm == 'y':
                    raise ResetTimesheet()
                # else continue prompting for this task
                continue
            print("[yellow]Press Enter for Yes, 'n' for No, or 'r' to reset.[/yellow]")

    return selected_ids


def get_task_details_from_user(task: dict) -> Optional[dict]:
    """Gets updated summary (supports multi-line) and duration for a selected task."""
    original_summary = task.get('task_name', 'Unknown Task')
    print(f"\nProcessing Task ID {task.get('id', '?')}: [white]{original_summary}[/white]")

    new_summary = original_summary
    change_summary_choice = prompt_user("Change summary? (y/N):").strip().lower()
    if change_summary_choice == 'y':
        # <<< MODIFIED: Use helper_parse.get_user_input for multi-line summary >>>
        entered_summary = helper_parse.get_user_input(
            prompt_message="Enter new summary (end with 'qq' on the same line): "
        ).strip() # .strip() applied to the whole multi-line input

        if entered_summary:
             # Check for numbers in summary can remain as is
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
                "datetime": task.get('datetime') # Preserve original datetime for sorting
            }
        except ValueError:
            print("[yellow]Invalid number entered for duration.[/yellow]")


def get_additional_task_details(timesheet_date: date) -> Optional[dict]:
    """Gets details for tasks added manually (summary supports multi-line)."""
    print("\nAdding additional task...")
    # <<< MODIFIED: Use helper_parse.get_user_input for multi-line summary >>>
    summary = helper_parse.get_user_input(
        prompt_message="Enter task summary (end with 'qq' on the same line): "
    ).strip()

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
            task_datetime_obj = datetime.combine(timesheet_date, completion_time)
            datetime_str_for_save = task_datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
            break
        except ValueError:
            print("[yellow]Invalid time format. Please use HH:mm (e.g., 14:30).[/yellow]")

    return {
        "summary": summary,
        "duration": duration,
        "is_locked": is_locked,
        "datetime": datetime_str_for_save
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
            target_duration = round(target / 5) * 5 # Ensure multiple of 5
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
        return timesheet_entries # No unlocked tasks to adjust

    needed_adjustment = target_duration - current_total
    if needed_adjustment == 0:
        return timesheet_entries # Already at target

    # Distribute adjustment among unlocked tasks
    # This logic attempts to distribute more evenly rather than just picking one.
    # It prioritizes making adjustments in multiples of 5 where possible.
    
    # Make copies to avoid modifying during iteration if logic becomes more complex
    # For this specific iterative adjustment, modifying in place is complex to get perfect.
    # A simpler approach might be to calculate per-task adjustment based on proportion.
    # However, let's stick to the iterative "step" logic from the original if that's preferred.

    # Iterative adjustment:
    remaining_adjustment_abs = abs(needed_adjustment)
    adjustment_sign = 1 if needed_adjustment > 0 else -1

    while remaining_adjustment_abs > 0 and any(unlocked_entries):
        made_change_in_cycle = False
        # Try to adjust each unlocked task by a small step (e.g., 5 minutes)
        # Sort by duration to prioritize adjusting shorter/longer tasks depending on sign
        # For adding time: add to shorter tasks first (or distribute)
        # For removing time: remove from longer tasks first
        unlocked_entries.sort(key=lambda x: x['duration'], reverse=(adjustment_sign < 0))

        for entry in unlocked_entries:
            if remaining_adjustment_abs == 0: break

            adjustment_step = min(remaining_adjustment_abs, 5) * adjustment_sign

            if entry['duration'] + adjustment_step < 5 and adjustment_step < 0: # Don't reduce below 5 mins
                # If trying to reduce, but it would go below 5, try smaller step
                adjustment_step = (5 - entry['duration']) # This will make it 5, if entry > 0
                if entry['duration'] + adjustment_step < 5 : # still less than 5 after trying to make it 5
                    continue # skip this task for reduction

            entry['duration'] += adjustment_step
            remaining_adjustment_abs -= abs(adjustment_step)
            made_change_in_cycle = True
        
        if not made_change_in_cycle: # No task could be adjusted further
            break
            
    final_total = sum(entry['duration'] for entry in timesheet_entries)
    if final_total != target_duration:
         print(f"[yellow]Final adjusted duration ({final_total} mins) differs from target ({target_duration} mins). Check task lengths/locks or adjustment logic.[/yellow]")
    elif needed_adjustment != 0:
         print("[green]Durations adjusted successfully to meet target.[/green]")

    return timesheet_entries


def save_timesheet_to_diary(timesheet_entries: list, timesheet_date: date):
    """Formats and saves the timesheet entries into the diary file using state_manager."""
    entries_to_save = []
    for entry in timesheet_entries:
        # Ensure all necessary keys are present with defaults
        saved_entry = {
            "summary": entry.get('summary', 'Unknown Task'),
            "duration": entry.get('duration', 0)
            # 'datetime' and 'is_locked' are not typically saved in the final diary task entry
        }
        entries_to_save.append(saved_entry)

    total_duration_minutes = sum(entry['duration'] for entry in entries_to_save)
    total_hours = total_duration_minutes / 60

    timesheet_date_str = timesheet_date.strftime("%Y-%m-%d")

    diary_update_payload = {
        "tasks": entries_to_save,
        "total_duration": total_duration_minutes, # Store as minutes
        "total_hours": round(total_hours, 2) # Store rounded hours
    }

    if state_manager.update_diary_entry(timesheet_date_str, diary_update_payload):
        print(f"\n[green]Timesheet for {timesheet_date_str} saved successfully.[/green]")
        print(f"  Total time logged: {total_duration_minutes} minutes ({total_hours:.2f} hours).")
    else:
        print(f"\n[red]Failed to save timesheet for {timesheet_date_str}.[/red]")


def update_objective_for_today():
    """Handles displaying the last objective and prompting user to update today's, using state_manager."""
    today = datetime.now().date()
    lookback_days_for_objective = AUDIT_LOOKBACK_WEEKS * 7
    last_objective, last_objective_date = state_manager.find_most_recent_objective(today, lookback_days=lookback_days_for_objective)

    if last_objective:
        if last_objective_date:
            days_ago = (today - last_objective_date).days
            day_word = "day" if days_ago == 1 else "days"
            date_str_formatted = last_objective_date.strftime('%A, %d %B')

            if days_ago == 0: # Objective set today
                print(f"\n[bold]Current Objective[/bold] (Set today):")
            else:
                print(f"\n[bold]Most Recent Objective[/bold] (Set {days_ago} {day_word} ago - {date_str_formatted}):")
            print(f"[yellow]{last_objective}[/yellow]")
        else: # Should ideally not happen if objective found
             print(f"\n[bold]Current Objective[/bold] (Date Unknown):")
             print(f"[yellow]{last_objective}[/yellow]")
    else:
        print("\n[yellow]No recent objective found in diary.[/yellow]")
        last_objective = None # Ensure it's None if not found

    update_choice = prompt_user("Update objective for today? (Y/n):").lower().strip()
    new_objective_to_set = None

    if update_choice != 'n':
        # <<< MODIFIED: Use helper_parse.get_user_input for multi-line objective >>>
        entered_objective = helper_parse.get_user_input(
            prompt_message="Enter new objective for today (end with 'qq' on the same line): "
        ).strip()
        if entered_objective:
            new_objective_to_set = entered_objective
        else:
            print("[yellow]No new objective entered. Keeping previous objective (if any).[/yellow]")
    else: # User chose 'n'
         if last_objective:
              print("[cyan]Keeping the most recent objective for today.[/cyan]")
              new_objective_to_set = last_objective # Re-set the same objective for today
         else:
              print("[cyan]No objective will be set for today.[/cyan]")

    if new_objective_to_set is not None: # Only update if there's something to set
        state_manager.update_todays_objective(new_objective_to_set)
        # Success/failure message handled by state_manager.update_todays_objective

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
            import traceback
            traceback.print_exc()
            return

        timesheet_date = get_timesheet_date()
        if not timesheet_date: return

        while True:  # allow user-requested reset without re-asking date
            try:
                filtered_tasks = load_and_filter_tasks(timesheet_date)
                # New sequential selection UX: clear screen between tasks, default include on Enter
                selected_ids = sequential_select_task_ids(filtered_tasks)

                timesheet_entries = []
                task_map = {task.get('id'): task for task in filtered_tasks if isinstance(task.get('id'), int)}
                selected_tasks = [task_map.get(task_id) for task_id in selected_ids if task_map.get(task_id)]

                # Phase 1: Rename pass (one at a time, clear screen, default No)
                renamed_summaries: dict[int, str] = {}
                for idx, task in enumerate(selected_tasks, start=1):
                    try:
                        _clear_screen()
                    except Exception:
                        print("\033[2J\033[H", end="")

                    task_id = task.get('id', '?')
                    original_summary = task.get('task_name', 'Unknown Task')
                    task_dt = task.get('datetime', '')
                    time_part = task_dt.split(' ')[-1] if isinstance(task_dt, str) and ' ' in task_dt else task_dt

                    print(f"[cyan]Rename tasks {idx}/{len(selected_tasks)}[/cyan]")
                    print(f"  Time: [white]{time_part or '?'}[/white]")
                    print(f"  Task: [white]{original_summary}[/white]")

                    while True:
                        choice = prompt_user("Rename this task? (Enter=No, y=Yes, r=reset):").strip().lower()
                        if choice in ("r", "reset"):
                            confirm_rnm = prompt_user("Reset timesheet process and start again? (y/N):").strip().lower()
                            if confirm_rnm == 'y':
                                raise ResetTimesheet()
                            else:
                                continue
                        if choice in ("", "n", "no"):
                            renamed_summaries[task_id] = original_summary
                            break
                        if choice in ("y", "yes"):
                            entered_summary = helper_parse.get_user_input(
                                prompt_message="Enter new summary (end with 'qq' on the same line): "
                            ).strip()
                            if entered_summary:
                                if any(ch.isdigit() for ch in entered_summary):
                                    confirm = prompt_user(f"[red]New summary '{entered_summary}' contains numbers. Confirm? (y/N):[/red]").strip().lower()
                                    if confirm == 'y':
                                        renamed_summaries[task_id] = entered_summary
                                    else:
                                        print("[yellow]Summary change cancelled.[/yellow]")
                                        renamed_summaries[task_id] = original_summary
                                else:
                                    renamed_summaries[task_id] = entered_summary
                            else:
                                print("[yellow]No new summary entered, keeping original.[/yellow]")
                                renamed_summaries[task_id] = original_summary
                            break
                        print("[yellow]Press Enter for No, 'y' for Yes, or 'r' to reset.[/yellow]")

                # Phase 2: Duration pass (one at a time, clear screen, default 5)
                for idx, task in enumerate(selected_tasks, start=1):
                    try:
                        _clear_screen()
                    except Exception:
                        print("\033[2J\033[H", end="")

                    task_id = task.get('id', '?')
                    task_dt = task.get('datetime', '')
                    time_part = task_dt.split(' ')[-1] if isinstance(task_dt, str) and ' ' in task_dt else task_dt
                    summary_for_entry = renamed_summaries.get(task_id, task.get('task_name', 'Unknown Task'))

                    print(f"[cyan]Set time {idx}/{len(selected_tasks)}[/cyan]")
                    print(f"  Time: [white]{time_part or '?'}[/white]")
                    print(f"  Task: [white]{summary_for_entry}[/white]")

                    while True:
                        try:
                            duration_input = prompt_user(f"Enter minutes (Enter={DEFAULT_TASK_DURATION}, wrap in () to lock, r=reset):").strip()
                            if duration_input.lower() in ('r', 'reset'):
                                confirm_r = prompt_user("Reset timesheet process and start again? (y/N):").strip().lower()
                                if confirm_r == 'y':
                                    raise ResetTimesheet()
                                else:
                                    continue

                            is_locked = False
                            if duration_input.startswith('(') and duration_input.endswith(')'):
                                is_locked = True
                                duration_input = duration_input[1:-1].strip()

                            duration = int(duration_input) if duration_input else DEFAULT_TASK_DURATION
                            if duration <= 0:
                                print(f"[yellow]Duration must be positive. Using default {DEFAULT_TASK_DURATION}.[/yellow]")
                                duration = DEFAULT_TASK_DURATION

                            timesheet_entries.append({
                                'summary': summary_for_entry,
                                'duration': duration,
                                'is_locked': is_locked,
                                'datetime': task.get('datetime')
                            })
                            break
                        except ValueError:
                            print("[yellow]Invalid number entered for duration.[/yellow]")

                while True:
                    add_more_choice = prompt_user("Add another task manually? (y/N):").lower().strip()
                    if add_more_choice == 'y':
                        additional_entry = get_additional_task_details(timesheet_date)
                        if additional_entry:
                            timesheet_entries.append(additional_entry)
                            lock_status_display = "(locked)" if additional_entry.get('is_locked') else ""
                            print(f"  Added: {additional_entry['summary']} ({additional_entry['duration']} mins) {lock_status_display}")
                    else:
                        break

                if not timesheet_entries:
                    print("[yellow]No tasks selected or added. Timesheet process aborted.[/yellow]")
                    return

                try:
                    # Sort entries by their original completion time for logical order before adjustment/saving
                    timesheet_entries.sort(key=lambda x: datetime.strptime(x.get('datetime', ''), "%Y-%m-%d %H:%M:%S") if isinstance(x.get('datetime'), str) else datetime.min)
                except ValueError:
                     print("[yellow]Warning: Error sorting timesheet entries by datetime. Order may be incorrect before saving.[/yellow]")

                target_duration_minutes = get_random_target_duration()
                timesheet_entries = adjust_durations(timesheet_entries, target_duration_minutes)

                print("\n[bold green] --- Final Timesheet --- [/bold green]")
                current_total_duration = 0
                for entry in timesheet_entries: # Iterate over potentially adjusted entries
                    lock_status_display = "[red](locked)[/red]" if entry.get('is_locked') else ""
                    summary_display = entry.get('summary', 'Unknown Task')
                    duration_display = entry.get('duration', 0)
                    print(f"  {summary_display}: {duration_display} minutes {lock_status_display}")
                    current_total_duration += duration_display
                total_hours_display = current_total_duration / 60
                print(f"\nTotal Time: {current_total_duration} minutes ({total_hours_display:.2f} hours)")
                print("[bold green]-------------------------[/bold green]")

                save_timesheet_to_diary(timesheet_entries, timesheet_date)

                try:
                    helper_todoist_long.display_tasks(api)
                except Exception as e_long_tasks:
                    print(f"[red]Error displaying long-term tasks post-timesheet: {e_long_tasks}[/red]")

                try:
                    print("\n[cyan]Refreshing active filter tasks (grouped for objective)...[/cyan]")
                    from helper_display import display_todoist_tasks_grouped_for_objective
                    display_todoist_tasks_grouped_for_objective(api)
                except Exception as e_current_tasks:
                    print(f"[red]Error displaying current Todoist tasks post-timesheet: {e_current_tasks}[/red]")

                update_objective_for_today()
                break  # Completed successfully, exit reset loop
            except ResetTimesheet:
                print("[yellow]Timesheet process reset. Starting selection again.[/yellow]")
                continue

    except Exception as e_main_timesheet:
        print(f"\n[bold red]An unexpected error occurred during the timesheet process:[/bold red]")
        print(f"[red]{e_main_timesheet}[/red]")
        import traceback
        traceback.print_exc()

# Apply call counter decorator
if 'module_call_counter' in globals() and hasattr(module_call_counter, 'apply_call_counter_to_all'):
     module_call_counter.apply_call_counter_to_all(globals(), __name__)
else:
     print("[yellow]Warning: module_call_counter not fully available in helper_timesheets.[/yellow]")
