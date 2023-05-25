import module_call_counter
import re, openai, os, calendar
from datetime import date, timedelta
from rich import print


def create_task_id_prompt(user_message):
    # Remove any 4-digit number at the end and everything after it
    user_message = re.sub(r"\b\d{4}.*$", "", user_message).strip()
    prompt = f"{user_message}. What was the task ID of that task? Respond with [Task ID: X], in that format exactly, including the square brackets. never fabricate a task id, and also ask me about when i've eaten today. i'm trying to lose weight and could do with your help."
    return prompt


def where_are_we(exchange_rate, max_spends_gbp):
    today = date.today()
    start_date = today.replace(day=1).strftime("%Y-%m-%d")
    end_date = (
        today.replace(month=today.month % 12 + 1, day=1) - timedelta(days=1)
    ).strftime("%Y-%m-%d")

    openai.api_key = os.environ["OPENAI_API_KEY"]
    r = openai.api_requestor.APIRequestor()
    resp_tuple = r.request(
        "GET", f"/dashboard/billing/usage?end_date={end_date}&start_date={start_date}"
    )
    resp = resp_tuple[0]
    resp_data = resp.data
    dollar_amount = round(resp_data["total_usage"] / 100, 2)

    gbp_amount = round(dollar_amount / exchange_rate, 2)

    days_passed = (today - today.replace(day=1)).days + 1
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    expected_spending = round((max_spends_gbp / days_in_month) * days_passed, 2)

    if gbp_amount <= expected_spending:
        print(
            f"[light_sea_green]Your spending is on track! You've spent £{gbp_amount} (${dollar_amount}) out of £{max_spends_gbp} so far, and you should be at £{expected_spending} by now.[/light_sea_green]\n"
        )
    else:
        print(
            f"[bright_magenta]Your spending is above the expected limit! You've spent £{gbp_amount} (${dollar_amount}) out of £{max_spends_gbp} so far, and you should be at £{expected_spending} by now.[/bright_magenta]\n"
        )


module_call_counter.apply_call_counter_to_all(globals(), __name__)
