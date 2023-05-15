import openai, os, json, re, time, threading
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


def get_user_input():
    return input("You: ")


def inject_system_message(messages, content):
    system_message = {"role": "system", "content": content}
    messages.append(system_message)


# This variable will be used to signal the chatbot response thread to stop
stop_chatbot_response = False


def listen_for_enter_key():
    global stop_chatbot_response
    input("-------------------------------------------------\n")
    stop_chatbot_response = True


def get_assistant_response(messages):
    global stop_chatbot_response
    stop_chatbot_response = False

    messages = helper_messages.summarize_and_shorten_messages(messages)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages, stream=True
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

    # Initialize a list to collect the chunks of the response
    response_chunks = []
    print()

    # Start a new thread to listen for the ENTER key press
    threading.Thread(target=listen_for_enter_key).start()
    time.sleep(0.5)  # stop collision with listen_for_enter_key message

    # Iterate over the chunks of the response as they arrive
    for chunk in response:
        # Check if the ENTER key has been pressed
        if stop_chatbot_response:
            print("\nInterrupted by user")
            response.close()
            return "[user stopped assistants response]"

        # Check if the chunk's 'delta' contains a 'content' key
        content = chunk["choices"][0].get("delta", {}).get("content")
        if content is not None:
            # If it does, add it to the list and print it
            response_chunks.append(content)
            print(content, end="")

    print("\n-------------------------------------------------")

    # Join the chunks together to form the full response
    full_response = "".join(response_chunks)

    return full_response


def extract_task_id_from_response(response_text):
    match = re.search(r"Task ID: (\d+)", response_text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def handle_user_input(user_message, messages, api, timestamp):
    timestamp_hhmm = parse(timestamp).strftime("%Y-%m-%d %I:%M %p")

    if "```" in user_message.lower():
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
        user_message_with_time = f"{timestamp_hhmm}: {user_message}"
        messages.append({"role": "user", "content": user_message_with_time})

    return messages


def handle_special_commands(user_message, assistant_message, api):
    if "```" in user_message.lower() and "Task ID" in assistant_message:
        task_id = extract_task_id_from_response(assistant_message)
        if task_id is not None:
            task = api.get_task(task_id=task_id)
            if task is not None:
                task_name = task.content
                time_complete = helper_general.get_timestamp()

                if helper_todoist.complete_todoist_task_by_id(api, task_id):
                    print(
                        f"\[green] Task with ID {task_id} successfully marked as complete. [/green]"
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
            system_txt = "Be short and concise with your answers.\n\n" + system_txt
            inject_system_message(messages, system_txt)

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
        handle_special_commands(user_message, assistant_message, api)
        messages.append({"role": "assistant", "content": assistant_message})
        save_json("j_conversation_history.json", messages)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
main_loop()
