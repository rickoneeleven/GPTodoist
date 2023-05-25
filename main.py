import openai, os, json, re
import helper_todoist, helper_gpt, cext_cmd_check, module_call_counter, helper_general
import helper_code
from rich import print

from dateutil.parser import parse
from todoist_api_python.api import TodoistAPI
from typing import Any, Union

openai.api_key = os.environ["OPENAI_API_KEY"]
TODOIST_API_KEY = os.environ["TODOIST_API_KEY"]
api = TodoistAPI(TODOIST_API_KEY)


def read_file(file_path: str) -> str:
    with open(file_path, "r") as f:
        return f.read()


def save_json(file_path: str, data: Any) -> None:
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def load_json(file_path: str) -> Union[dict, list]:
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    else:
        return []


def write_to_file(filename, data):
    with open(filename, "a") as file:
        # file.write(f"\n-----------------------------------------------{helper_general.get_timestamp()}\n")
        file.write("\n\n\n\n\n")
        file.write(data)


def get_user_input():
    print("You: ", end="")
    user_input = ""
    while True:
        line = input()  # No need to strip trailing whitespaces
        if line == "ignore":
            # Ignore everything above
            user_input = ""
        elif line == "!!":
            # Submit everything above and ignore "!!"
            break
        elif line.endswith("qq"):  # User input ended
            user_input += line[:-2]  # Add the current line without the trailing "qq"
            break
        else:
            user_input += line + "\n"  # Add the current line to user_input
    return user_input.rstrip("\n")  # Remove trailing newline


def inject_system_message(messages, content):
    system_message = {"role": "system", "content": content}
    messages.append(system_message)


def handle_user_input(user_message, messages, api, timestamp):
    timestamp_hhmm = parse(timestamp).strftime("%Y-%m-%d %I:%M %p")

    # check the model to use based on the user's message
    model_to_use = "gpt-3.5-turbo"  # default model
    pass_to_bot = True  # flag to indicate whether the user message was pass_to_bot

    if user_message.startswith("3 "):
        model_to_use = "gpt-3.5-turbo"
        user_message = user_message[2:]  # remove the prefix
        user_message_with_time = f"{timestamp_hhmm}: {user_message}"
        messages.append({"role": "user", "content": user_message_with_time})
    elif user_message.startswith("4 "):
        model_to_use = "gpt-4"
        user_message = user_message[2:]  # remove the prefix
        user_message_with_time = f"{timestamp_hhmm}: {user_message}"
        messages.append({"role": "user", "content": user_message_with_time})
    elif "~~~" in user_message.lower():
        helper_todoist.insert_tasks_into_system_prompt(api, messages)
        task_id_prompt = helper_gpt.create_task_id_prompt(
            " ".join(user_message.split()[1:])
        )
        messages.append({"role": "user", "content": task_id_prompt})
    elif user_message.lower().startswith("move task"):
        helper_todoist.insert_tasks_into_system_prompt(api, messages)
        task_id_prompt = helper_gpt.create_task_id_prompt(
            " ".join(user_message.split()[2:])
        )
        messages.append({"role": "user", "content": task_id_prompt})
    else:
        pass_to_bot = False

    return messages, model_to_use, pass_to_bot


def print_conversation_history():
    conversation_file = "j_conversation_history.json"
    if os.path.exists(conversation_file):
        conversation_history = load_json(conversation_file)
        for message in conversation_history:
            print(f"{message['role'].capitalize()}: {message['content']}")
        print("\n\n")


print_conversation_history()


def main_loop():
    while True:
        helper_gpt.where_are_we(1.24, 20)
        messages = load_json("j_conversation_history.json")
        loaded_files = load_json("j_loaded_files.json")
        if loaded_files:
            print(
                f"[red]{', '.join([file['filename'] for file in loaded_files])} loaded into memory...[/red]"
            )
        user_message = get_user_input()
        print("processing...")

        if cext_cmd_check.ifelse_commands(api, user_message):
            continue

        messages[:] = [
            msg for msg in messages if msg["role"] != "system"
        ]  # remove system messages
        system_txt = ""

        timestamp = helper_general.get_timestamp()
        messages, model_to_use, pass_to_bot = handle_user_input(
            user_message, messages, api, timestamp
        )

        if not pass_to_bot:
            print("eh?\n")
            continue

        for file in loaded_files:
            content = read_file(file["filename"])
            shrunk_content = helper_code.shrink_code(content)
            system_txt += f"---\n\n{file['filename']}:\n{shrunk_content}\n"

        if system_txt.strip():  # checks it's not an empty file
            system_message = {"role": "system", "content": system_txt}
            messages.append(system_message)

        if os.path.isfile("j_loaded_files.json"):
            with open("j_loaded_files.json", "r") as file:
                loaded_files = json.load(file)
        else:
            loaded_files = []

        assistant_message = helper_gpt.get_assistant_response(messages, model_to_use)
        helper_todoist.handle_special_commands(user_message, assistant_message, api)
        messages.append({"role": "assistant", "content": assistant_message})
        save_json("j_conversation_history.json", messages)

        # Extract code between triple backticks and write to refactored.py
        code_sections = re.findall(r"```(.*?)```", assistant_message, re.DOTALL)
        if code_sections:
            for i, code in enumerate(code_sections):
                # Remove leading and trailing newlines
                code = code.strip()
                write_to_file("refactored.py", code)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
main_loop()
