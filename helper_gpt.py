import module_call_counter, helper_messages
import re, openai, os, calendar, time
from datetime import date, timedelta
from rich import print


def create_task_id_prompt(user_message):
    # Remove any 4-digit number at the end and everything after it
    user_message = re.sub(r"\b\d{4}.*$", "", user_message).strip()
    prompt = f"{user_message}. What was the task ID of that task? Respond with [Task ID: X], in that format exactly, including the square brackets. never fabricate a task id. Then lets continue our conversation about my healthy lifestyle, eating and weight. Make it engaging, ask me a question you've not asked yet it our interactions."
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
    buffer_spends = round(expected_spending - gbp_amount, 2)

    if gbp_amount <= expected_spending:
        print(f"[green1]£{buffer_spends}  ;)[/green1]\n")
    else:
        print(f"[red1]£{buffer_spends}  ;([/red1]\n")


def get_assistant_response(messages, model_to_use, retries=99, backoff_factor=2):
    messages = helper_messages.summarize_and_shorten_messages(messages)
    if model_to_use == "gpt-4":
        print("[red]USING BIG BRAIN GPT4!!!![/red]")

    for retry in range(retries):
        try:
            response = openai.ChatCompletion.create(
                model=model_to_use, messages=messages, stream=True
            )

            response_chunks = []
            print()

            try:
                for chunk in response:
                    content = chunk["choices"][0].get("delta", {}).get("content")
                    if content is not None:
                        response_chunks.append(content)
                        print(content, end="")

                print("\n-------------------------------------------------")

                full_response = "".join(response_chunks)

                return full_response
            except Exception as e:
                print(f"Error while streaming response: {e}")
                return "[error occurred during assistant response]"
        except openai.error.RateLimitError:
            if retry < retries - 1:  # Check if there are retries left
                sleep_time = backoff_factor**retry  # Exponential backoff
                print(f"Rate limit exceeded? Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print("Retry limit exceeded. Please try again later.")
                return "[rate limit exceeded]"
        except Exception as e:
            if retry < retries - 1:  # Check if there are retries left
                sleep_time = backoff_factor**retry  # Exponential backoff
                print(f"An error occurred: {e}. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print("Retry limit exceeded. Please try again later.")
                return "[an error occurred while getting assistant response]"


module_call_counter.apply_call_counter_to_all(globals(), __name__)
