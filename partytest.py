import module_call_counter, helper_messages
import re, openai, os, calendar, time, requests
from datetime import date, timedelta
from rich import print


def where_are_we():
    try:
        today = date.today()
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_date = (
            today.replace(month=today.month % 12 + 1, day=1) - timedelta(days=1)
        ).strftime("%Y-%m-%d")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f'Bearer {os.getenv("OPENAI_API_KEY")}',
        }
        resp = requests.get(
            f"https://api.openai.com/v1/dashboard/billing/usage?end_date={end_date}&start_date={start_date}",
            headers=headers,
            timeout=3,
        )

        print("Response: ", resp)  # show the full response
        print("Response status code: ", resp.status_code)  # show just the status code

        resp_data = resp.json()

        print("Response data: ", resp_data)  # print the response data
    except requests.exceptions.Timeout:
        print("[yellow1]Request timed out getting costs...[/yellow1]")
        return False
    except Exception as e:
        print(f"[red1]An error occurred: {e}[/red1]")
        return False


where_are_we()
