import openai, os, json, signal, readline, sys, re
import helper_todoist, helper_gpt, helper_commands, module_call_counter, helper_general, module_weather
import helper_code, helper_messages
from rich import print
from dateutil.parser import parse
from todoist_api_python.api import TodoistAPI


def handle_sigint(signal_received, frame):
    print("CTRL+C detected. Re-running main.py")
    os.execl(sys.executable, sys.executable, *sys.argv)


signal.signal(signal.SIGINT, handle_sigint)

openai.api_key = os.environ["OPENAI_API_KEY"]
TODOIST_API_KEY = os.environ["TODOIST_API_KEY"]
api = TodoistAPI(TODOIST_API_KEY)
last_user_message = ""
readline.set_auto_history(
    True
)  # fakenews, here to stop readlines import warning, we use readlines so input() supports left and right arrows


def get_user_input():
    global last_user_message
    print("You: ", end="")
    user_input = ""
    while True:
        line = input()
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


def handle_user_input(user_message, messages, api, timestamp):
    global last_user_message
    timestamp_hhmm = parse(timestamp).strftime("%Y-%m-%d %I:%M %p")

    # check the model to use based on the user's message
    model_to_use = "gpt-3.5-turbo"  # default model
    pass_to_bot = True  # flag to indicate whether the user message was pass_to_bot

    if user_message in (
        "3",
        "4",
    ):  # ooops, the last message we sent didn't have a bot prefix, so we're just sending a 3 or a 4, and grabbing the last user message
        if last_user_message:
            user_message = f"{user_message} {last_user_message}"
        else:
            print("No previous message to resubmit")
            return

    if user_message.startswith("3 "):
        model_to_use = "gpt-3.5-turbo-16k"
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
    system_txt = "General refactoring rules: 1. Never show full refactored file, only the function in question unless asked by the user.\nLatest version of file(s) for your consideration: "
    function_pattern = re.compile(r"def\s+(\w+)\s*\(")

    for file in loaded_files:
        content = helper_general.read_file(file["filename"])
        functions = function_pattern.findall(content)
        functions_formatted = "\n".join([f"{func}():" for func in functions])

        print(f"[red]{file['filename']} loaded into memory...[/red]")  # Print filename
        print(functions_formatted)  # Print function names

        system_txt += f"\n\n---\n{file['filename']}:\n{functions_formatted}\n"

    system_message = {"role": "system", "content": system_txt}
    messages.append(system_message)

    return messages


helper_messages.print_conversation_history()


def main_loop():
    while True:
        helper_gpt.where_are_we(1.24, 20)
        helper_todoist.get_next_todoist_task(api)
        module_weather.today()
        messages = helper_general.load_json("j_conversation_history.json")
        helper_messages.remove_old_code(
            messages
        )  # strip ass responses with code between triple ticks, older that 3 ass messages ago, so when suggesting refactors, it doesn't bring back old code
        helper_messages.current_tokkies(messages)
        helper_general.check_j_conv_default()
        user_message = get_user_input()
        print("processing... ++++++++++++++++++++++++++++++++++++++++++++++")

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

        assistant_message = helper_gpt.get_assistant_response(messages, model_to_use)
        helper_todoist.handle_special_commands(user_message, assistant_message, api)
        messages.append({"role": "assistant", "content": assistant_message})
        helper_general.save_json("j_conversation_history.json", messages)

        # Extract code between triple backticks and write to refactored.py
        helper_code.extract_and_save_code_sections(assistant_message)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
main_loop()
