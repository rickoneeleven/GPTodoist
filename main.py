import openai, os, json, re, time
import helper_todoist, helper_gpt, cext_cmd_check, module_call_counter, helper_general
import helper_messages, helper_code
from rich import print

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


def write_to_file(filename, data):
    with open(filename, "a") as file:
        file.write(
            f"\n-----------------------------------------------{helper_general.get_timestamp()}\n"
        )
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


stop_chatbot_response = False


def listen_for_enter_key():
    global stop_chatbot_response
    input("-------------------------------------------------\n")
    stop_chatbot_response = True


def get_assistant_response(messages, model_to_use):
    messages = helper_messages.summarize_and_shorten_messages(messages)
    if model_to_use == "gpt-4":
        print("[red]USING BIG BRAIN GPT4!!!![/red]")
    try:
        response = openai.ChatCompletion.create(
            model=model_to_use, messages=messages, stream=True
        )
    except openai.error.RateLimitError as e:
        print(e)
        print()
        print("Rate limit exceeded? Retrying in a few seconds...")
        time.sleep(10)  # Wait for 10 seconds before retrying
        return get_assistant_response(messages)  # Retry the function call
    except Exception as e:
        print(f"Error while getting assistant response: {e}")
        return ""

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


def extract_task_id_from_response(response_text):
    match = re.search(r"Task ID: (\d+)", response_text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def handle_user_input(user_message, messages, api, timestamp):
    timestamp_hhmm = parse(timestamp).strftime("%Y-%m-%d %I:%M %p")

    # check the model to use based on the user's message
    model_to_use = "gpt-3.5-turbo"  # default model
    processed = False  # flag to indicate whether the user message was processed

    if user_message.startswith("3 "):
        model_to_use = "gpt-3.5-turbo"
        user_message = user_message[2:]  # remove the prefix
        processed = True
    elif user_message.startswith("4 "):
        model_to_use = "gpt-4"
        user_message = user_message[2:]  # remove the prefix
        processed = True

    if "~~~" in user_message.lower():
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
    elif user_message.lower().startswith("refactor"):
        model_to_use = "gpt-4"
        user_message = " ".join(user_message.split()[1:])
        prompt = f"""look at {user_message} and suggest one refactor following the guidelines
              ---
                - Improve Code Readability
                - Remove Dead Code
                - DRY (Don't Repeat Yourself)
                - Use Pythonic Conventions
                - Simplify Conditional Logic
                - Improve Data Structures 
              ---
                remember to always encompass any code output with triple ticks and only GIVE ME ONE REFACTOR"""
        user_message_with_time = f"{timestamp_hhmm}: {prompt}"
        messages.append({"role": "user", "content": user_message_with_time})
    else:
        user_message_with_time = f"{timestamp_hhmm}: {user_message}"
        messages.append({"role": "user", "content": user_message_with_time})

    return messages, model_to_use, processed


def handle_special_commands(user_message, assistant_message, api):
    if "~~~" in user_message.lower() and "Task ID" in assistant_message:
        task_id = extract_task_id_from_response(assistant_message)
        if task_id is not None:
            task = api.get_task(task_id=task_id)
            if task is not None:
                task_name = task.content
                time_complete = helper_general.get_timestamp()

                if helper_todoist.complete_todoist_task_by_id(api, task_id):
                    print(
                        f"[green] Task with ID {task_id} successfully marked as complete. [/green]"
                    )
                    helper_todoist.update_todays_completed_tasks(
                        task_name, task_id, time_complete
                    )
                else:
                    print("Failed to complete the task.")
    if user_message.lower().startswith("move task") and "Task ID" in assistant_message:
        task_id = extract_task_id_from_response(assistant_message)
        if task_id is not None:
            helper_todoist.update_task_due_date(api, user_message, task_id)
            helper_todoist.get_next_todoist_task(api)
        else:
            print("Failed to move the task.")


def main_loop():
    while True:
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

        # Create a string that lists all the loaded files
        file_list = ", ".join([file["filename"] for file in loaded_files])

        # Prepend the file list to user_message
        if file_list:
            user_message += f" {file_list}"

        timestamp = helper_general.get_timestamp()
        messages, model_to_use, processed = handle_user_input(
            user_message, messages, api, timestamp
        )

        if not processed:
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

        assistant_message = get_assistant_response(messages, model_to_use)
        handle_special_commands(user_message, assistant_message, api)
        messages.append({"role": "assistant", "content": assistant_message})
        save_json("j_conversation_history.json", messages)

        # Extract code between triple backticks and write to refactored.py
        code_sections = re.findall(r"~~~(.*?)~~~", assistant_message, re.DOTALL)
        if code_sections:
            for i, code in enumerate(code_sections):
                # Remove leading and trailing newlines
                code = code.strip()
                write_to_file("refactored.py", code)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
main_loop()
