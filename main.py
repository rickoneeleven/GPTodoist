import openai, os, json, re, time
import helper_todoist, helper_gpt, helper_parse, cext_cmd_check, module_call_counter, helper_general
import helper_messages, helper_code

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
    messages[:] = [msg for msg in messages if msg["role"] != "system"]
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
    print(
        f"\n\n{assistant_message}\n--------------------------------------------------------------"
    )


def clear_active_tasks_messages(messages):
    messages[:] = [
        msg
        for msg in messages
        if not (msg["role"] == "system" and msg["content"].startswith("Active Tasks:"))
    ]


def main_loop():
    while True:
        messages = load_json("j_conversation_history.json")
        clear_active_tasks_messages(messages)
        user_message = get_user_input()

        system_txt = ""
        loaded_files = load_json("j_loaded_files.json")
        for file in loaded_files:
            content = read_file(file["filename"])
            shrunk_content = helper_code.shrink_code(content)
            system_txt += f"{file['filename']}:\n{shrunk_content}\n"

        timestamp = helper_general.get_timestamp()

        if user_message.lower().startswith("add task"):
            task_data = helper_parse.get_taskname_time_day_as_tuple(user_message)
            if task_data:
                # This line unpacks the task_data tuple (or a list) into three separate variables: task_name, task_time, and task_day.
                task_name, task_time, task_day = task_data
                task = helper_todoist.add_todoist_task(
                    api, task_name, task_time, task_day
                )
                if task:
                    print(f"Task '{task.content}' successfully added.")
                else:
                    print("Failed to add task.")
            continue
        elif user_message.lower() == "commands":
            helper_general.print_commands()
            continue
        elif cext_cmd_check.ifelse_commands(
            api, user_message
        ):  # look at me mama, i can flyyyyyyyyyyy!
            continue
        elif user_message.lower().startswith("complete"):
            task_name = user_message[len("complete") :].strip()
            task_id = "manual entry"
            helper_todoist.update_todays_completed_tasks(task_name, task_id, timestamp)
            print(
                f"Manually completed task '\033[91m{task_name}\033[0m' added to today's completed tasks."
            )
            continue

        inject_system_message(messages, system_txt)

        tasks = helper_todoist.fetch_todoist_tasks(api)
        timestamp_hhmm = parse(timestamp).strftime("%Y-%m-%d %I:%M %p")
        if tasks:
            task_list = "\n".join(
                [
                    f"- {task.content} (due: {parse(task.due.datetime).strftime('%Y-%m-%d %I:%M %p') if task.due and task.due.datetime else timestamp_hhmm}) [Task ID: {task.id}]"
                    for task in tasks
                ]
            )
            todoist_tasks_message = f"Here are the users active tasks, they may ask you to reference the ID:\n{task_list}"
            messages.append({"role": "system", "content": todoist_tasks_message})
        else:
            todoist_tasks_message = "Active Tasks:\n [All tasks complete!]"
            messages.append({"role": "system", "content": todoist_tasks_message})
        # ----------------------- bot parsing todoist stuff and then todoist api interaction
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

        assistant_message = get_assistant_response(messages)
        display_assistant_response(assistant_message)
        # ----------------------- todoist: complete a task
        if "```" in user_message.lower() and "Task ID" in assistant_message:
            task_id = extract_task_id_from_response(assistant_message)
            if task_id is not None:
                task = api.get_task(task_id=task_id)
                if task is not None:
                    task_name = task.content
                    time_complete = helper_general.get_timestamp()

                    if helper_todoist.complete_todoist_task_by_id(api, task_id):
                        print(
                            f"\033[91m Task with ID {task_id} successfully marked as complete. \033[0m"
                        )
                        helper_todoist.update_todays_completed_tasks(
                            task_name, task_id, time_complete
                        )
                    else:
                        print("Failed to complete the task.")
        if (
            user_message.lower().startswith("move task")
            and "Task ID" in assistant_message
        ):
            task_id = extract_task_id_from_response(assistant_message)
            if task_id is not None:
                helper_todoist.update_task_due_date(api, user_message, task_id)
                helper_todoist.get_next_todoist_task(api)
            else:
                print("penis")

        # ----------------------- END: bot parsing todoist stuff and then todoist api interaction
        messages.append({"role": "assistant", "content": assistant_message})
        save_json("j_conversation_history.json", messages)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
main_loop()
