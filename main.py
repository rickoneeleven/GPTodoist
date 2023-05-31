import openai, os, json
import helper_todoist, helper_gpt, helper_commands, module_call_counter, helper_general
import helper_code, helper_messages
from rich import print

from dateutil.parser import parse
from todoist_api_python.api import TodoistAPI

openai.api_key = os.environ["OPENAI_API_KEY"]
TODOIST_API_KEY = os.environ["TODOIST_API_KEY"]
api = TodoistAPI(TODOIST_API_KEY)
last_user_message = ""


def get_user_input():
    global last_user_message
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
    user_input = user_input.rstrip("\n")
    if user_input not in ["4", "3"]:
        last_user_message = user_input
    return user_input


def resubmit_last_message():
    global last_user_message
    if last_user_message:
        return "4 " + last_user_message


def inject_system_message(messages, content):
    system_message = {"role": "system", "content": content}
    messages.append(system_message)


def handle_user_input(user_message, messages, api, timestamp):
    global last_user_message
    timestamp_hhmm = parse(timestamp).strftime("%Y-%m-%d %I:%M %p")

    # check the model to use based on the user's message
    model_to_use = "gpt-3.5-turbo"  # default model
    pass_to_bot = True  # flag to indicate whether the user message was pass_to_bot

    if (
        user_message == "4"
    ):  # ooops, the last message we sent didn't have a bot prefix, so we're just sending a 4, and grabbing the last user message
        if last_user_message:
            user_message = "4 " + last_user_message
        else:
            print("No previous message to resubmit")
            return

    if (
        user_message == "3"
    ):  # ooops, the last message we sent didn't have a bot prefix, so we're just sending a 3, and grabbing the last user message
        if last_user_message:
            user_message = "3 " + last_user_message
        else:
            print("No previous message to resubmit")
            return

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


def process_loaded_files(messages, loaded_files):
    system_txt = "be super short and concise with your answers, only showing functions if they have been refactored. "
    for file in loaded_files:
        content = helper_general.read_file(file["filename"])
        system_txt += f"---\n\n{file['filename']}:\n{content}\n"
        system_message = {"role": "system", "content": system_txt}
        messages.append(system_message)
    return messages


helper_messages.print_conversation_history()


def main_loop():
    while True:
        helper_gpt.where_are_we(1.24, 20)
        messages = helper_general.load_json("j_conversation_history.json")
        loaded_files = helper_general.load_json("j_loaded_files.json")
        if loaded_files:
            print(
                f"[red]{', '.join([file['filename'] for file in loaded_files])} loaded into memory...[/red]"
            )
            messages = process_loaded_files(
                messages, loaded_files
            )  # to get correct tokkie count
        helper_messages.current_tokkies(messages)
        user_message = get_user_input()
        print("processing...")

        if helper_commands.ifelse_commands(api, user_message):
            continue

        messages[:] = [
            msg for msg in messages if msg["role"] != "system"
        ]  # remove system messages

        timestamp = helper_general.get_timestamp()
        messages, model_to_use, pass_to_bot = handle_user_input(
            user_message, messages, api, timestamp
        )

        if not pass_to_bot:
            print("eh?\n")
            continue

        for (
            file
        ) in (
            loaded_files
        ):  # we do this logic so the system message is after user message, bot responds well
            messages = process_loaded_files(messages, loaded_files)

        if os.path.isfile("j_loaded_files.json"):
            with open("j_loaded_files.json", "r") as file:
                loaded_files = json.load(file)
        else:
            loaded_files = []

        assistant_message = helper_gpt.get_assistant_response(messages, model_to_use)
        helper_todoist.handle_special_commands(user_message, assistant_message, api)
        messages.append({"role": "assistant", "content": assistant_message})
        helper_general.save_json("j_conversation_history.json", messages)

        # Extract code between triple backticks and write to refactored.py
        helper_code.extract_and_save_code_sections(assistant_message)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
main_loop()
