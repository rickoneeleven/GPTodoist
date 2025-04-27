# File: helper_diary.py
# <<< REMOVED: json, os imports as file I/O is handled by state_manager >>>
from datetime import datetime, timedelta
from typing import Union, Tuple, Optional # Keep typing imports
from rich import print
import module_call_counter
# <<< REMOVED: traceback import if only used for file I/O errors >>>
import state_manager # <<< ADDED: Import the state manager

# --- Constants ---
# <<< REMOVED: Filename constants (DIARY_FILENAME, OPTIONS_FILENAME, COMPLETED_TASKS_FILENAME) >>>
# <<< KEPT: Application logic constants >>>
DEFAULT_OPTIONS = {"enable_diary_prompts": "yes"} # Kept for reference if needed, though state_manager has its own default
PURGE_WEEKS = 5
MIN_WEEKDAY_HOURS = 7
AUDIT_LOOKBACK_WEEKS = 5
OBJECTIVE_LOOKBACK_DAYS = 30 # Max days to look back for an objective

# --- Helper Functions ---

# <<< REMOVED: _load_json function >>>
# <<< REMOVED: _save_json function >>>

# --- Options Helper (Now uses State Manager) ---
def get_options() -> dict:
    """Loads options using the state manager."""
    # <<< MODIFIED: Call state_manager >>>
    return state_manager.get_options()

# --- Objective Helper (Now uses State Manager) ---
# <<< MODIFIED: This function now acts as a simple wrapper or could be removed >>>
def find_most_recent_objective(diary_data: dict, start_date: datetime.date) -> tuple[Optional[str], Optional[datetime.date]]:
    """
    Finds the most recent objective by calling the state manager.
    Note: diary_data parameter is no longer used here, kept for signature compatibility if needed, but ideally removed later.
    """
    # <<< MODIFIED: Call state_manager >>>
    # Pass the lookback period defined in this module
    return state_manager.find_most_recent_objective(start_date, lookback_days=OBJECTIVE_LOOKBACK_DAYS)


# --- Core Functions ---

def purge_old_completed_tasks():
    """Removes old completed tasks by calling the state manager."""
    # <<< MODIFIED: Call state_manager >>>
    days_to_keep = PURGE_WEEKS * 7
    try:
        purged_count = state_manager.purge_old_completed_tasks_log(days_to_keep=days_to_keep)
        # State manager handles logging success/failure details internally
        if purged_count == -1:
             print("[red]Failed to purge old completed tasks (save error).[/red]")
        # elif purged_count > 0: # Logging now done inside state_manager
        #     print(f"[cyan]Purged {purged_count} tasks older than {PURGE_WEEKS} weeks.[/cyan]")

    except Exception as e:
         # Catch unexpected errors during the call to state_manager
         print(f"[red]An unexpected error occurred during completed task purge process: {e}[/red]")
         # Consider logging traceback here if needed
         # import traceback
         # traceback.print_exc()

def weekly_audit():
    """Performs weekly audit checks and displays the most recent objective using state_manager."""
    # <<< MODIFIED: Use state_manager >>>
    options = state_manager.get_options()
    diary_data = state_manager.get_diary_data()

    # --- Audit Check ---
    if options.get("enable_diary_prompts", "yes").lower() == "yes":
        today = datetime.now().date()
        # Calculate start date: Monday of AUDIT_LOOKBACK_WEEKS weeks ago
        start_audit_date = today - timedelta(days=today.weekday() + (7 * (AUDIT_LOOKBACK_WEEKS - 1)))
        end_audit_date = today - timedelta(days=1) # Yesterday

        missing_data_days = []
        current_date = start_audit_date
        while current_date <= end_audit_date:
            # Check only Mon-Fri
            if current_date.weekday() < 5:
                date_str = current_date.strftime("%Y-%m-%d")
                day_data = diary_data.get(date_str) # Data comes from state_manager via diary_data
                # Check if entry exists and if total_hours is less than minimum
                if isinstance(day_data, dict):
                    total_hours = day_data.get("total_hours", 0)
                    # Ensure total_hours is a number before comparing
                    if isinstance(total_hours, (int, float)) and total_hours < MIN_WEEKDAY_HOURS:
                         missing_data_days.append(current_date)
                    elif not isinstance(total_hours, (int, float)):
                         print(f"[yellow]Warning: Invalid 'total_hours' ({total_hours}) for {date_str} in audit.[/yellow]")
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
    # <<< MODIFIED: Call state_manager to find objective >>>
    objective, objective_date = state_manager.find_most_recent_objective(today, lookback_days=OBJECTIVE_LOOKBACK_DAYS)

    if objective:
        date_display = objective_date.strftime('%A, %d %B %Y') if objective_date else 'Unknown'
        print(f"\n[bold]Most Recent Objective[/bold] (Set on {date_display}):")
        print(f"[gold1]{objective}[/gold1]")
    else:
        print("\n[yellow]No recent overall objective found in diary.[/yellow]")

    print() # Add trailing space


def _prompt_for_summary_details():
    """Handles user input for selecting day or week summary. (No changes needed)"""
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
    """Prints formatted entries for a single day. (No changes needed)"""
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
    """Shows the summary for the most recent day with entries. (No changes needed in logic, relies on passed diary_data)"""
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
    """Shows the summary for the week containing the reference_date. (No changes needed in logic, relies on passed diary_data)"""
    start_of_week = reference_date - timedelta(days=reference_date.weekday()) # Monday
    end_of_week = start_of_week + timedelta(days=4) # Friday

    print(f"\n[bold blue]Summary for Week: {start_of_week.strftime('%d %b')} - {end_of_week.strftime('%d %b %Y')}[/bold blue]")

    week_dates = [start_of_week + timedelta(days=i) for i in range(5)] # Mon-Fri Dates

    for current_date in week_dates:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"\n[bold green]--- {current_date.strftime('%A, %B %d, %Y')} ---[/bold green]")
        if date_str in diary_data:
            show_day_entries(diary_data[date_str])
        else:
            print("[dim]No entries found for this day.[/dim]")
            print("--------------------------------------------------")


def diary():
    """Main function to trigger diary summary display based on user input."""
    # <<< MODIFIED: Use state_manager >>>
    diary_data = state_manager.get_diary_data()
    if not diary_data:
        print("[yellow]Diary file is empty or could not be read.[/yellow]")
        return

    summary_type, reference_date = _prompt_for_summary_details()

    if summary_type == "day":
        show_day_summary(diary_data) # Pass loaded data
    elif summary_type == "week" and reference_date:
        show_week_summary(diary_data, reference_date) # Pass loaded data
    # Error messages handled within _prompt_for_summary_details


def update_todays_objective(new_objective: str):
    """Updates the overall objective for today using the state manager."""
    # <<< MODIFIED: Call state_manager >>>
    if not state_manager.update_todays_objective(new_objective):
        # State manager handles internal errors and validation printing
        print("[red]Diary objective update failed (see previous messages).[/red]")
    # Success message is printed inside state_manager.update_todays_objective


# Apply call counter decorator (No changes needed)
if 'module_call_counter' in globals() and hasattr(module_call_counter, 'apply_call_counter_to_all'):
     module_call_counter.apply_call_counter_to_all(globals(), __name__)
else:
     print("[yellow]Warning: module_call_counter not fully available in helper_diary.[/yellow]")