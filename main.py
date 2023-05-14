import openai, os, json, re, time
import helper_todoist, helper_gpt, cext_cmd_check, module_call_counter, helper_general
import helper_messages, helper_code

from rich import print
from rich.syntax import Syntax

from dateutil.parser import parse
from todoist_api_python.api import TodoistAPI

openai.api_key = os.environ["OPENAI_API_KEY"]
TODOIST_API_KEY = os.environ["TODOIST_API_KEY"]
api = TodoistAPI(TODOIST_API_KEY)

read_file = lambda file_path: open(file_path, "r").read()

save_json = lambda file_path, data: json.dump(data, open(file_path, "w"), indent=2)
load_json = (
    lambda file_path: json.load(open(file_path, "r"))
    if os.path.exists(file_path)
    else []
)


def get_user_input():
    return input("You: ")


def inject_system_message(messages, content):
    system_message = {"role": "system", "content": content}
    messages.append(system_message)


def get_assistant_response(messages):
    messages = helper_messages.summarize_and_shorten_messages(messages)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages
        )
    except openai.error.RateLimitError as e:
        print(e)
        print()
        print("Rate limit exceeded? Retrying in a few seconds...")
        time.sleep(10)  # Wait for 10 seconds before retrying
        return get_assistant_response(messages)  # Retry the function call
    except Exception as e:
        print(f"Error while getting assistant response: {e}")
        return None
    return response.choices[0].message["content"]


def extract_task_id_from_response(response_text):
    match = re.search(r"Task ID: (\d+)", response_text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def display_assistant_response(assistant_message):
    print("\n")
    # Split the message into parts based on triple backticks
    parts = re.split(r"(```)", assistant_message)

    # Initialize a flag to track whether we're inside a code block
    in_code_block = False

    # Iterate over the parts
    for part in parts:
        if part == "```":
            # If we encounter triple backticks, toggle the in_code_block flag
            in_code_block = not in_code_block
        elif in_code_block:
            # If we're inside a code block, apply syntax highlighting
            syntax = Syntax(part, "python", theme="monokai", line_numbers=False)
            print(syntax)
        else:
            # If we're not inside a code block, print the part as is
            print(part)
    print("\n--------------------------------------------------------------")


def handle_user_input(user_message, messages, api, timestamp):
    timestamp_hhmm = parse(timestamp).strftime("%Y-%m-%d %I:%M %p")

    if "```" in user_message.lower():
        task_id_prompt = helper_gpt.create_task_id_prompt(
            " ".join(user_message.split()[1:])
        )
        messages.append({"role": "user", "content": task_id_prompt})
    elif user_message.lower().startswith("move task"):
        task_id_prompt = helper_gpt.create_task_id_prompt(
            " ".join(user_message.split()[2:])
        )
        messages.append({"role": "user", "content": task_id_prompt})
    else:
        user_message_with_time = f"{timestamp_hhmm}: {user_message}"
        messages.append({"role": "user", "content": user_message_with_time})

    return messages


def main_loop():
    while True:
        messages = load_json("j_conversation_history.json")
        loaded_files = load_json("j_loaded_files.json")
        # Print the loaded files
        if loaded_files:
            print(
                f"[red]{', '.join([file['filename'] for file in loaded_files])} loaded into memory...[/red]"
            )
        user_message = get_user_input()

        messages[:] = [
            msg for msg in messages if msg["role"] != "system"
        ]  # remove system messages
        system_txt = ""
        for file in loaded_files:
            content = read_file(file["filename"])
            shrunk_content = helper_code.shrink_code(content)
            system_txt += f"---\n\n{file['filename']}:\n{shrunk_content}\n"

        timestamp = helper_general.get_timestamp()

        if system_txt.strip():  # checks it's not an empty file
            system_txt = (
                "+++You are a refactoring bot, help the user with the files below.+++\n\n"
                + system_txt
            )
            inject_system_message(messages, system_txt)

        tasks = helper_todoist.fetch_todoist_tasks(api)
        if tasks:
            task_list = "\n".join(
                [f"- {task.content} [Task ID: {task.id}]" for task in tasks]
            )
            todoist_tasks_message = f"My outstanding tasks today:\n{task_list}"
            messages.append({"role": "system", "content": todoist_tasks_message})
        else:
            todoist_tasks_message = "Active Tasks:\n [All tasks complete!]"
            messages.append({"role": "system", "content": todoist_tasks_message})

        # Check if the user message is a command
        if cext_cmd_check.ifelse_commands(api, user_message):
            # If it is a command, start the next iteration of the loop
            continue

        # If not a command, handle the user input
        messages = handle_user_input(user_message, messages, api, timestamp)

        # Load the JSON file if it exists, otherwise create an empty list
        if os.path.isfile("j_loaded_files.json"):
            with open("j_loaded_files.json", "r") as file:
                loaded_files = json.load(file)
        else:
            loaded_files = []

        assistant_message = get_assistant_response(messages)
        display_assistant_response(assistant_message)

        messages.append({"role": "assistant", "content": assistant_message})
        save_json("j_conversation_history.json", messages)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
main_loop()
