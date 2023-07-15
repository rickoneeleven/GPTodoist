import module_call_counter, helper_messages
import re, openai, os, calendar, time, requests
from datetime import date, timedelta
from rich import print


def create_task_id_prompt(user_message):
    # Remove any 4-digit number at the end and everything after it
    user_message = re.sub(r"\b\d{4}.*$", "", user_message).strip()
    prompt = f"{user_message}. What was the task ID of that task? Respond with [Task ID: X], in that format exactly, including the square brackets. never fabricate a task id. Then present me with an interesting fact. I'll tell you if I thought it was or not, to help guide you in the future."
    return prompt


def where_are_we(exchange_rate, max_spends_gbp):
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

        resp_data = resp.json()
        dollar_amount = round(resp_data["total_usage"] / 100, 2)

        gbp_amount = round(dollar_amount / exchange_rate, 2)

        days_passed = (today - today.replace(day=1)).days + 1
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        expected_spending = round((max_spends_gbp / days_in_month) * days_passed, 2)
        buffer_spends = round(expected_spending - gbp_amount, 2)

        if gbp_amount <= expected_spending:
            print(f"[green1]£{buffer_spends}  ;)[/green1]")
        else:
            print(f"[red1]£{buffer_spends}  ;([/red1]")
    except requests.exceptions.Timeout:
        print("[yellow1]Request timed out getting costs...[/yellow1]")
        return False
    except Exception as e:
        print(f"[red1]An error occurred: {e}[/red1]")
        return False


def get_assistant_response(messages, model_to_use, retries=99, backoff_factor=2):
    print("[bright_black]sending user messages to openai....[/bright_black]")

    if model_to_use == "gpt-4":
        print("[red]USING BIG BRAIN GPT4!!!![/red]")
        messages = helper_messages.summarize_and_shorten_messages(messages, 7000)
    elif model_to_use == "gpt-3.5-turbo":
        messages = helper_messages.summarize_and_shorten_messages(messages, 3000)
    elif model_to_use == "gpt-3.5-turbo-16k":
        messages = helper_messages.summarize_and_shorten_messages(messages, 15000)

    for retry in range(retries):
        try:
            response = openai.ChatCompletion.create(
                model=model_to_use, messages=messages, stream=True
            )

            response_chunks = []
            print()

            for chunk in response:
                content = chunk["choices"][0].get("delta", {}).get("content")
                if content is not None:
                    response_chunks.append(content)
                    print(content, end="")

            print("\n-------------------------------------------------")

            full_response = "".join(response_chunks)

            return full_response

        except Exception as e:  # Catch any exception, not just specific ones
            if retry < retries - 1:  # Check if there are retries left
                sleep_time = backoff_factor**retry  # Exponential backoff
                print(f"An error occurred: {e}. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print("Retry limit exceeded. Please try again later.")
                return "[an error occurred while getting assistant response]"


module_call_counter.apply_call_counter_to_all(globals(), __name__)
