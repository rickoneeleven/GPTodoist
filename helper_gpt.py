import module_call_counter, helper_messages
import re, openai, os, calendar, time, requests, datetime, json
from datetime import date, timedelta
from rich import print
from rich.progress import Progress, BarColumn, TextColumn

# billing api parameters
url = "https://api.openai.com/v1/usage"
api_key = os.getenv("OPENAI_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}

model_costs = {
    "gpt-3.5-turbo-0301": {"context": 0.0015, "generated": 0.002},
    "gpt-3.5-turbo-0613": {"context": 0.0015, "generated": 0.002},
    "gpt-3.5-turbo-16k": {"context": 0.003, "generated": 0.004},
    "gpt-3.5-turbo-16k-0613": {"context": 0.003, "generated": 0.004},
    "gpt-4-0314": {"context": 0.03, "generated": 0.06},
    "gpt-4-0613": {"context": 0.03, "generated": 0.06},
    "gpt-4-32k": {"context": 0.06, "generated": 0.12},
    "gpt-4-32k-0314": {"context": 0.06, "generated": 0.12},
    "gpt-4-32k-0613": {"context": 0.06, "generated": 0.12},
    "whisper-1": {
        "context": 0.006 / 60,
        "generated": 0,
    },  # Cost is per second, so convert to minutes
}
# end billing api parameters


def get_costs(start_date, end_date):
    now = datetime.datetime.now()
    try:
        with open("j_costs.json", "r") as file:
            stored_costs = json.load(file)
    except FileNotFoundError:
        stored_costs = []

    stored_costs_dict = {d["date"]: d for d in stored_costs}

    date_range = [
        start_date + datetime.timedelta(days=x)
        for x in range((end_date - start_date).days + 1)
    ]
    total_cost = 0

    def get_daily_cost(date):
        params = {"date": date}
        # print(f"Querying billing API for {date}")

        while True:
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                usage_data = response.json()["data"]
                whisper_data = response.json()["whisper_api_data"]
                break
            except requests.HTTPError as err:
                if err.response.status_code == 429:
                    print("[red]Rate limit exceeded. Sleeping for 69 seconds...[/red]")
                    time.sleep(69)
                    continue
                print(f"Request failed: {err}")
                return None
            except KeyError as err:
                print(f"Missing key in API response: {err}")
                return None

        daily_cost = 0
        for data in usage_data + whisper_data:
            model = data.get("model_id") or data.get("snapshot_id")
            if model in model_costs:
                if "num_seconds" in data:
                    cost = data["num_seconds"] * model_costs[model]["context"]
                else:
                    context_tokens = data["n_context_tokens_total"]
                    generated_tokens = data["n_generated_tokens_total"]
                    cost = (context_tokens / 1000 * model_costs[model]["context"]) + (
                        generated_tokens / 1000 * model_costs[model]["generated"]
                    )
                daily_cost += cost
            else:
                print(
                    "[red]model not defined, please add model and associated costs to model_costs object[/red]"
                )
                return None

        return daily_cost

    # Iterate over each date in the defined range
    for date in date_range:
        date_str = date.strftime("%Y-%m-%d")

        # If the date already exists in stored data and it's either not today, or it was queried less than 60 seconds ago,
        # add the stored cost to total_cost then proceed to the next date
        if date_str in stored_costs_dict:
            last_query_time = datetime.datetime.strptime(
                stored_costs_dict[date_str]["query_time"], "%Y-%m-%dT%H:%M:%S.%f"
            )
            if date_str != now.strftime("%Y-%m-%d") or (
                now - last_query_time
            ) < datetime.timedelta(seconds=60):
                total_cost += stored_costs_dict[date_str]["cost"]
                continue

        # If the date is today and doesn't exist in stored data or it was queried more than 60 seconds ago, retrieve the cost from the API
        daily_cost = get_daily_cost(date_str)
        if daily_cost is None:
            return None

        # Record the current time when the API query is made
        query_time = datetime.datetime.now()

        # Update the stored cost data with the newly retrieved cost and query time
        stored_costs_dict[date_str] = {
            "cost": daily_cost,
            "query_time": query_time.isoformat(),
        }
        total_cost += daily_cost

        # Reformat the stored costs dictionary into a list of dictionaries for storing as JSON
        stored_costs = [
            {"date": k, "cost": v["cost"], "query_time": v["query_time"]}
            for k, v in stored_costs_dict.items()
        ]

        # Write the updated stored costs data back into the JSON file
        with open("j_costs.json", "w") as file:
            json.dump(stored_costs, file, indent=2)
        # print(f"Successfully added {date_str} costs to j_costs.json")

    return total_cost


def create_task_id_prompt(user_message):
    # Remove any 4-digit number at the end and everything after it
    user_message = re.sub(r"\b\d{4}.*$", "", user_message).strip()
    prompt = f"""{user_message}. What was the task ID of that task? Respond with [Task ID: X], in that format exactly, including the square brackets. never fabricate a task id. Then try and engage with me in conversation:
    
    The task ID for "kids dooties" is [Task ID: 6973484921].
    
    <attempt to engage in coversation>"""
    return prompt


def where_are_we():
    start_date = datetime.datetime.now().replace(day=1)
    end_date = datetime.datetime.now()
    permitted_dollar_spends = 10

    dollar_amount = round(get_costs(start_date, end_date), 2)

    days_passed = (end_date - end_date.replace(day=1)).days + 1
    days_in_month = calendar.monthrange(end_date.year, end_date.month)[1]
    expected_spending = round(
        (permitted_dollar_spends / days_in_month) * days_passed, 2
    )

    progress = Progress(
        TextColumn("API spends..."), BarColumn(), TextColumn(f"${dollar_amount}")
    )
    progress_percentage = round(
        (dollar_amount / permitted_dollar_spends) * 100, 0
    )  # as a percentage
    with progress:
        task = progress.add_task("[cyan]completion", total=100)
        progress.update(task, completed=progress_percentage)


def get_assistant_response(messages, model_to_use, retries=99, backoff_factor=2):
    print("[bright_black]sending user messages to openai....[/bright_black]")

    if model_to_use == "gpt-4":
        print("[red]USING BIG BRAIN GPT4!!!![/red]")
        messages = helper_messages.summarize_and_shorten_messages(messages, 7000)
    elif model_to_use == "gpt-3.5-turbo":
        messages = helper_messages.summarize_and_shorten_messages(messages, 3000)
    elif model_to_use == "gpt-3.5-turbo-16k":
        messages = helper_messages.summarize_and_shorten_messages(messages, 15000)
    elif model_to_use == "gpt-4-1k":
        messages = helper_messages.summarize_and_shorten_messages(messages, 1000)
        model_to_use = "gpt-4"

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
