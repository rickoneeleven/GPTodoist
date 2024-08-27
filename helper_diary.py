import json
from datetime import datetime, timedelta
from rich import print
import module_call_counter

def diary():
    summary_type = input("Would you like a summary of the day or week? (day/week, default: day): ").lower() or "day"

    if summary_type == "day":
        show_day_summary()
    elif summary_type == "week":
        week_option = input("Which week? (this/last/dd/mm/yy): ").lower()
        if week_option == "this":
            show_week_summary(datetime.now().date())
        elif week_option == "last":
            last_week = datetime.now().date() - timedelta(days=7)
            show_week_summary(last_week)
        else:
            try:
                specified_date = datetime.strptime(week_option, "%d/%m/%y").date()
                show_week_summary(specified_date)
            except ValueError:
                print("[red]Invalid date format. Please use dd/mm/yy.[/red]")
    else:
        print("[red]Invalid input. Please choose 'day' or 'week'.[/red]")

def show_day_summary():
    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
    except FileNotFoundError:
        print("[red]Diary file not found.[/red]")
        return
    except json.JSONDecodeError:
        print("[red]Error reading the diary file.[/red]")
        return

    today = datetime.now().date()
    previous_day = today - timedelta(days=1)

    while previous_day.isoformat() not in diary:
        previous_day -= timedelta(days=1)
        if (today - previous_day).days > 7:  # Limit search to a week
            print("[yellow]No recent entries found in the diary.[/yellow]")
            return

    print(f"[bold blue]Summary for {previous_day.strftime('%A, %B %d, %Y')}:[/bold blue]")
    show_day_entries(diary[previous_day.isoformat()])

def show_week_summary(reference_date):
    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
    except FileNotFoundError:
        print("[red]Diary file not found.[/red]")
        return
    except json.JSONDecodeError:
        print("[red]Error reading the diary file.[/red]")
        return

    start_of_week = reference_date - timedelta(days=reference_date.weekday())
    end_of_week = start_of_week + timedelta(days=4)  # Monday to Friday

    print(f"[bold blue]Summary for the week of {start_of_week.strftime('%B %d')} - {end_of_week.strftime('%B %d, %Y')}:[/bold blue]")

    for day in range(5):  # Monday to Friday
        current_date = start_of_week + timedelta(days=day)
        date_str = current_date.strftime("%Y-%m-%d")
        
        if date_str in diary:
            print(f"\n[bold green]{current_date.strftime('%A, %B %d')}:[/bold green]")
            show_day_entries(diary[date_str])
        else:
            print(f"\n[yellow]{current_date.strftime('%A, %B %d')}: No entries[/yellow]")

def show_day_entries(day_data):
    if 'overall_objective' in day_data:
        print(f"[cyan]Overall objective:[/cyan] {day_data['overall_objective']}")

    if 'tasks' in day_data:
        print("\n[cyan]Tasks:[/cyan]")
        sorted_tasks = sorted(day_data['tasks'], key=lambda x: x['duration'], reverse=True)
        for task in sorted_tasks:
            print(f"- {task['summary']} ({task['duration']} minutes)")

    if 'total_hours' in day_data:
        print(f"\n[cyan]Total hours worked:[/cyan] {day_data['total_hours']}")
        print("-------------------------------------------------------------------")
        
def weekly_audit():
    try:
        with open("j_diary.json", "r") as f:
            diary = json.load(f)
    except FileNotFoundError:
        print("[red]Diary file not found.[/red]")
        return
    except json.JSONDecodeError:
        print("[red]Error reading the diary file.[/red]")
        return

    today = datetime.now().date()
    start_date = today - timedelta(days=today.weekday() + 14)  # Two weeks ago Monday
    end_date = today - timedelta(days=1)  # Yesterday

    missing_data_days = []

    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday to Friday
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in diary:
                total_hours = diary[date_str].get("total_hours", 0)
                if total_hours < 7:
                    missing_data_days.append(current_date)
            else:
                missing_data_days.append(current_date)
        current_date += timedelta(days=1)

    if missing_data_days:
        print("\n[red]Days with less than 7 hours of accountable time:[/red]")
        for day in missing_data_days:
            formatted_date = day.strftime("%d/%m/%y")
            day_of_week = day.strftime("%A")
            print(f"[red]I[/red] {formatted_date} - {day_of_week}")

    # Print today's overall objective if it exists
    today_str = today.strftime("%Y-%m-%d")
    if today_str in diary and 'overall_objective' in diary[today_str]:
        print(f"\nflow with...")
        print(f"[gold1]{diary[today_str]['overall_objective']}[/gold1]")
            
            
if __name__ == "__main__":
    diary()
    
module_call_counter.apply_call_counter_to_all(globals(), __name__)