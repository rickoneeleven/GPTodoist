import datetime, os, pytz, json, shutil, time
import helper_general
from dateutil.parser import parse
from typing import Any, Union
from rich import print


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
        "~~~": "~~~ anywhere in message asks the bot to try and mark the task complete on todoist",
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
        "touch long <id>": "reset the date of long task to today",
        "reset": "resets us back to default chat",
        "fresh": "starts a brand new chat session",
        "ignore": "ignore on a new line on it's own, tells the prompt to ignore everything typed before it",
        "save <filename>": "save food, would save the current conversation to a json called food",
        "show conv": "show conversations",
        "load conv <id>": "load conversation based on id",
        "delete conv <id>": "delete conversation based on id",
        "replay": "prints conversation history",
        "weather": "show detailed weather information",
        "flip": "flips your active todoist filter. note: you can nly have two filters for this to work",
        "ring": "advise the system you have eaten your last main meal of the day",
    }
    print()
    max_command_len = max(len(command) for command in commands)
    for command, description in commands.items():
        print(f"{command.ljust(max_command_len)}   -   {description}")
    print()


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
        file.write(
            f"#{helper_general.get_timestamp()} ---------------------------------\n"
        )
        file.write(data)
        file.write("\n\n")


def backup_json_files():
    # Check if the 'backups' folder exists, and create it if it doesn't
    backups_dir = "backups"
    if not os.path.exists(backups_dir):
        print("Creating 'backups' folder...")
        os.makedirs(backups_dir)

    # Generate the current date-time string
    # current_datetime = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d")

    # Loop through all files in the current directory
    for filename in os.listdir("."):
        # Check if the file has a '.json' extension
        if filename.endswith(".json"):
            # Backup the file to the 'backups' folder
            source_file = filename
            backup_file = os.path.join(backups_dir, f"{current_datetime}--{filename}")

            print(f"Backing up '{source_file}' to '{backup_file}'")
            shutil.copy2(source_file, backup_file)

    # Loop through all files in the 'backups' directory
    for filename in os.listdir(backups_dir):
        file_path = os.path.join(backups_dir, filename)
        # Check if the file is older than 10 days
        if datetime.datetime.now() - datetime.datetime.fromtimestamp(
            os.path.getctime(file_path)
        ) > datetime.timedelta(days=10):
            # Delete the file
            print()
            print(f"Deleting old backup file '{file_path}'")
            os.remove(file_path)


def check_j_conv_default():
    file_name = "j_conv_DEFAULT.json"

    if os.path.exists(file_name):
        print("[dark_khaki]Remember to save your conversation[/dark_khaki]")
    else:
        print("[dodger_blue1]On main branch[/dodger_blue1]")


def connectivity_check():
    for i in range(6):
        response = os.system("ping -c 1 8.8.4.4 > /dev/null 2>&1")
        if response == 0:
            return True
        time.sleep(1)
        print()
        print()
        print("[red]connection is sad face, retrying...[/red]")
        print()
        print()
    print("[yellow]_____________ CONNECTION FAILED _____________[/yellow]")
    print()
    print()
    return False
