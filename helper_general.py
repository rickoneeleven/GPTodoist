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
        # Extract the date from the filename
        file_date_str = filename.split("--")[0]
        file_date = datetime.datetime.strptime(file_date_str, "%Y-%m-%d")

        # Check if the file is older than 10 days
        if datetime.datetime.now().date() - file_date.date() > datetime.timedelta(
            days=10
        ):
            # Delete the file
            print()
            print(f"Deleting old backup file '{file_path}'")
            os.remove(file_path)


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
