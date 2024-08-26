import json
from datetime import datetime, timedelta
from rich import print
import module_call_counter

def diary():
    summary_type = input("Would you like a summary of the day or week? (day/week, default: day): ").lower() or "day"

    if summary_type == "day":
        show_day_summary()
    elif summary_type == "week":
        show_week_summary()
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

def show_week_summary():
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
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=4)  # Monday to Friday

    print(f"[bold blue]Summary for the week of {start_of_week.strftime('%B %d')} - {end_of_week.strftime('%B %d, %Y')}:[/bold blue]")

    for day in range(5):  # Monday to Friday
        current_date = start_of_week + timedelta(days=day)
        if current_date > today:
            # Skip future dates
            continue
        if current_date.isoformat() in diary:
            print(f"\n[bold green]{current_date.strftime('%A, %B %d')}:[/bold green]")
            show_day_entries(diary[current_date.isoformat()])
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

if __name__ == "__main__":
    diary()
    
module_call_counter.apply_call_counter_to_all(globals(), __name__)