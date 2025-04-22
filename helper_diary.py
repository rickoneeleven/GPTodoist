# File: helper_diary.py
import json, os
from datetime import datetime, timedelta
# <<< CHANGE: Import Union >>>
from typing import Union
from rich import print
import module_call_counter
import traceback # Added for logging unexpected errors

# --- Constants ---
DIARY_FILENAME = "j_diary.json"
OPTIONS_FILENAME = "j_options.json"
COMPLETED_TASKS_FILENAME = "j_todays_completed_tasks.json"
DEFAULT_OPTIONS = {"enable_diary_prompts": "yes"}
PURGE_WEEKS = 5
MIN_WEEKDAY_HOURS = 7
AUDIT_LOOKBACK_WEEKS = 5
OBJECTIVE_LOOKBACK_DAYS = 30 # Max days to look back for an objective

# --- Helper Functions ---

def _load_json(filename: str, default_value=None):
    """Loads JSON data from a file, handling errors and defaults."""
    if not os.path.exists(filename):
        if default_value is not None:
            # Optionally create the file with default value
            try:
                with open(filename, "w") as f:
                    json.dump(default_value, f, indent=2)
                print(f"[cyan]Created missing file: {filename}[/cyan]")
                return default_value
            except IOError as e:
                print(f"[red]Error creating default file {filename}: {e}[/red]")
                return default_value if isinstance(default_value, (dict, list)) else {} # Return empty dict/list on create error
        else:
            # print(f"[yellow]File not found: {filename}[/yellow]") # Less verbose
            return {} if default_value is None else default_value # Default to empty dict if no default provided

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
        return {} if default_value is None else default_value
    except IOError as e:
        print(f"[red]Error accessing file {filename}: {e}[/red]")
        return {} if default_value is None else default_value
    except Exception as e:
        print(f"[red]An unexpected error occurred loading {filename}: {e}[/red]")
        traceback.print_exc()
        return {} if default_value is None else default_value

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

def get_options():
    """Loads options, creating default if necessary."""
    return _load_json(OPTIONS_FILENAME, default_value=DEFAULT_OPTIONS)

# <<< CHANGE: Use Union in the type hint >>>
def find_most_recent_objective(diary_data: dict, start_date: datetime.date) -> tuple[Union[str, None], Union[datetime.date, None]]:
    """
    Finds the most recent objective in the diary by looking back from start_date.

    Args:
        diary_data: The loaded diary dictionary.
        start_date: The date object to start looking back from.

    Returns:
        tuple: (objective_text, objective_date) or (None, None) if not found.
    """
    current_date = start_date
    for _ in range(OBJECTIVE_LOOKBACK_DAYS): # Limit lookback
        date_str = current_date.strftime("%Y-%m-%d")
        entry = diary_data.get(date_str)
        if isinstance(entry, dict) and 'overall_objective' in entry:
            objective = entry['overall_objective']
            if objective: # Ensure objective is not empty
                return objective, current_date

        current_date -= timedelta(days=1)

    # If loop finishes without finding a non-empty objective
    return None, None

# --- Core Functions ---

def purge_old_completed_tasks():
    """Removes completed tasks older than PURGE_WEEKS weeks."""
    tasks = _load_json(COMPLETED_TASKS_FILENAME, default_value=[])
    if not isinstance(tasks, list):
        print(f"[red]Invalid data in {COMPLETED_TASKS_FILENAME}, cannot purge.[/red]")
        return # Don't proceed if data is not a list

    cutoff_datetime = datetime.now() - timedelta(weeks=PURGE_WEEKS)
    updated_tasks = []
    parse_error_count = 0

    for task in tasks:
        if not isinstance(task, dict):
            print(f"[yellow]Skipping invalid entry during purge: {task}[/yellow]")
            continue # Skip non-dict items

        datetime_str = task.get('datetime')
        if not isinstance(datetime_str, str):
            print(f"[yellow]Skipping task with missing/invalid datetime field: {task.get('task_name', 'N/A')}[/yellow]")
            updated_tasks.append(task) # Keep task if date is invalid? Or discard? Keep for now.
            continue

        try:
            task_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            if task_datetime > cutoff_datetime:
                updated_tasks.append(task)
        except ValueError:
            parse_error_count += 1
            updated_tasks.append(task) # Keep tasks with parse errors

    if parse_error_count > 0:
         print(f"[yellow]Could not parse datetime for {parse_error_count} tasks during purge.[/yellow]")

    if len(tasks) > len(updated_tasks):
        if _save_json(COMPLETED_TASKS_FILENAME, updated_tasks):
            print(f"[cyan]Purged {len(tasks) - len(updated_tasks)} tasks older than {PURGE_WEEKS} weeks.[/cyan]")
        else:
            print(f"[red]Failed to save purged tasks to {COMPLETED_TASKS_FILENAME}.[/red]")

def weekly_audit():
    """Performs weekly audit checks and displays the most recent objective."""
    options = get_options()
    diary_data = _load_json(DIARY_FILENAME, default_value={})

    # --- Audit Check ---
    if options.get("enable_diary_prompts", "yes").lower() == "yes":
        today = datetime.now().date()
        # Calculate start date: Monday of AUDIT_LOOKBACK_WEEKS weeks ago
        start_audit_date = today - timedelta(days=today.weekday() + (7 * (AUDIT_LOOKBACK_WEEKS -1)))
        end_audit_date = today - timedelta(days=1) # Yesterday

        missing_data_days = []
        current_date = start_audit_date
        while current_date <= end_audit_date:
            # Check only Mon-Fri
            if current_date.weekday() < 5:
                date_str = current_date.strftime("%Y-%m-%d")
                day_data = diary_data.get(date_str)
                # Check if entry exists and if total_hours is less than minimum
                if isinstance(day_data, dict):
                    total_hours = day_data.get("total_hours", 0)
                    # Ensure total_hours is a number before comparing
                    if isinstance(total_hours, (int, float)) and total_hours < MIN_WEEKDAY_HOURS:
                         missing_data_days.append(current_date)
                    elif not isinstance(total_hours, (int, float)):
                         print(f"[yellow]Warning: Invalid 'total_hours' ({total_hours}) for {date_str} in audit.[/yellow]")
                         # Optionally add to missing_data_days if invalid hours means data is missing
                         missing_data_days.append(current_date)
                else:
                    # Entry for the day doesn't exist
                    missing_data_days.append(current_date)
            current_date += timedelta(days=1)

        if missing_data_days:
            print(f"\n[red]Days in the last {AUDIT_LOOKBACK_WEEKS} weeks with < {MIN_WEEKDAY_HOURS} hours logged:[/red]")
            for day in missing_data_days:
                formatted_date = day.strftime("%d/%m/%y")
                day_of_week = day.strftime("%A")
                print(f"[red]! Missing/Low Hours ![/red] {formatted_date} - {day_of_week}")
            print() # Add space after audit section


    # --- Display Most Recent Objective ---
    today = datetime.now().date()
    # Find the most recent objective starting from today
    objective, objective_date = find_most_recent_objective(diary_data, today)

    if objective:
        print(f"\n[bold]Most Recent Objective[/bold] (Set on {objective_date.strftime('%A, %d %B %Y') if objective_date else 'Unknown'}):")
        print(f"[gold1]{objective}[/gold1]")
    else:
        print("\n[yellow]No recent overall objective found in diary.[/yellow]")

    print() # Add trailing space

def _prompt_for_summary_details():
    """Handles user input for selecting day or week summary."""
    summary_type = input("Summary of day or week? (day/week, default: day): ").lower().strip() or "day"
    if summary_type == "day":
        return "day", None
    elif summary_type == "week":
        week_option = input("Which week? (this/last/dd/mm/yy, default: this): ").lower().strip() or "this"
        if week_option == "this":
            return "week", datetime.now().date()
        elif week_option == "last":
            return "week", datetime.now().date() - timedelta(days=7)
        else:
            try:
                specified_date = datetime.strptime(week_option, "%d/%m/%y").date()
                return "week", specified_date
            except ValueError:
                print("[red]Invalid date format. Please use dd/mm/yy.[/red]")
                return None, None
    else:
        print("[red]Invalid input. Please choose 'day' or 'week'.[/red]")
        return None, None

def show_day_entries(day_data):
    """Prints formatted entries for a single day."""
    if not isinstance(day_data, dict):
        print("[yellow]No data available for this day.[/yellow]")
        return

    tasks = day_data.get('tasks')
    if isinstance(tasks, list) and tasks:
        print("\n[cyan]Tasks:[/cyan]")
        for task in tasks:
             # Safely access keys with defaults
             summary = task.get('summary', 'Unknown Task')
             duration = task.get('duration', '?')
             print(f"- {summary} ({duration} minutes)")
    else:
        print("\n[dim]No tasks logged.[/dim]")

    total_hours = day_data.get('total_hours')
    if isinstance(total_hours, (int, float)):
        print(f"\n[cyan]Total hours worked:[/cyan] {total_hours:.2f}") # Format to 2 decimal places
    else:
        print("\n[dim]Total hours not recorded.[/dim]")

    objective = day_data.get('overall_objective')
    if objective:
         print(f"\n[cyan]Objective:[/cyan] [gold1]{objective}[/gold1]")

    print("--------------------------------------------------")


def show_day_summary(diary_data):
    """Shows the summary for the most recent day with entries."""
    today = datetime.now().date()
    target_day = today - timedelta(days=1) # Start looking from yesterday
    found_entry = False

    for _ in range(14): # Look back up to 2 weeks
        date_str = target_day.strftime("%Y-%m-%d")
        if date_str in diary_data:
            print(f"\n[bold blue]Summary for {target_day.strftime('%A, %B %d, %Y')}:[/bold blue]")
            show_day_entries(diary_data[date_str])
            found_entry = True
            break
        target_day -= timedelta(days=1)

    if not found_entry:
        print("[yellow]No diary entries found in the last 14 days.[/yellow]")


def show_week_summary(diary_data, reference_date):
    """Shows the summary for the week containing the reference_date."""
    start_of_week = reference_date - timedelta(days=reference_date.weekday()) # Monday
    end_of_week = start_of_week + timedelta(days=4) # Friday

    print(f"\n[bold blue]Summary for Week: {start_of_week.strftime('%d %b')} - {end_of_week.strftime('%d %b %Y')}[/bold blue]")

    week_dates = [start_of_week + timedelta(days=i) for i in range(5)] # Mon-Fri Dates

    for current_date in week_dates:
        date_str = current_date.strftime("%Y-%m-%d")
        # <<< MODIFIED: Added %Y to include the year >>>
        print(f"\n[bold green]--- {current_date.strftime('%A, %B %d, %Y')} ---[/bold green]")
        if date_str in diary_data:
            show_day_entries(diary_data[date_str])
        else:
            print("[dim]No entries found for this day.[/dim]")
            print("--------------------------------------------------")

        # Optional: Add prompt to continue after each day or pair of days if too long
        # if current_date.weekday() % 2 == 1 and current_date != end_of_week: # After Tue, Thu
        #      input("\nPress Enter to continue...")


def diary():
    """Main function to trigger diary summary display based on user input."""
    diary_data = _load_json(DIARY_FILENAME, default_value={})
    if not diary_data:
        print("[yellow]Diary file is empty or could not be read.[/yellow]")
        return

    summary_type, reference_date = _prompt_for_summary_details()

    if summary_type == "day":
        show_day_summary(diary_data)
    elif summary_type == "week" and reference_date:
        show_week_summary(diary_data, reference_date)
    # Error messages handled within _prompt_for_summary_details


def update_todays_objective(new_objective: str):
    """Updates the overall objective for today in the diary file."""
    if not new_objective or not isinstance(new_objective, str):
        print("[red]Invalid objective provided.[/red]")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    diary_data = _load_json(DIARY_FILENAME, default_value={})

    # Ensure the entry for today exists and is a dictionary
    if today_str not in diary_data or not isinstance(diary_data[today_str], dict):
        diary_data[today_str] = {} # Initialize if missing or invalid type

    diary_data[today_str]['overall_objective'] = new_objective

    if _save_json(DIARY_FILENAME, diary_data):
        print(f"Today's overall objective updated: [gold1]{new_objective}[/gold1]")
    else:
        print("[red]Failed to save updated objective to diary file.[/red]")


# Apply call counter decorator (assuming module_call_counter exists and works)
if 'module_call_counter' in globals() and hasattr(module_call_counter, 'apply_call_counter_to_all'):
     module_call_counter.apply_call_counter_to_all(globals(), __name__)
else:
     print("[yellow]Warning: module_call_counter not fully available in helper_diary.[/yellow]")