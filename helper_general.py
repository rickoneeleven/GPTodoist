import datetime
import pytz
from dateutil.parser import parse


def convert_to_london_timezone(timestamp: str) -> str:
    utc_datetime = parse(timestamp)
    london_tz = pytz.timezone("Europe/London")
    london_datetime = utc_datetime.astimezone(london_tz)
    return london_datetime.strftime("%Y-%m-%d %H:%M:%S")


def get_timestamp():
    london_tz = pytz.timezone("Europe/London")
    return datetime.datetime.now(london_tz).strftime("%Y-%m-%d %H:%M:%S")


def print_commands():
    commands = {
        "add task": "add task [task name]/[task name 1800]/[task name 1800 tomorrow]",
        "~~~": "~~~ anywhere in message causes filters to be bypassed",
        "```": "``` anywhere in message asks the bot to try and mark the task complete on todoist",
        "done": "queries the todoist api direct to complete the active task in j_active_task.json",
        "time": "updates task's due time. [time 1800] -> 1800 today, [time 1800 tomorrow] -> you guessed it!",
        "delete": "deletes the active task from todoist, doesn't add to completed json file",
        "all": "show all tasks",
        "clear": "clear the screen",
        "add long": "add long [task name] to add task to j_long_term_tasks.json",
        "move task": "move task [task name] uses the bot to get the taskid, and move task time",
        "show long": "print list of long term tasks",
        "rename long": "renames long term task. rename long [id] [new task name]",
        "delete long": "deletes long term task. delete long [id]",
        "weather": "show the weather for today",
        "add file <filename>": "adds file to system messages",
        "reset": "deletes j_conversation_history.json, j_loaded_files.json and empties system_messages.txt",
    }
    print()
    max_command_len = max(len(command) for command in commands)
    for command, description in commands.items():
        print(f"{command.ljust(max_command_len)}   -   {description}")
    print()
