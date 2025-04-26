# File: helper_general.py
import datetime, os, pytz, json, shutil, time, traceback, platform, subprocess
from dateutil.parser import parse
from typing import Any, Union, Dict, List
from rich import print

# --- Constants ---
OPTIONS_FILENAME = "j_options.json"
DEFAULT_OPTIONS = {"enable_diary_prompts": "yes", "last_backup_timestamp": None}
# <<< Restored backup_retention_days >>>
backup_retention_days = 10

# --- Robust JSON Handling ---
# <<< load_json and save_json remain unchanged >>>
def load_json(file_path: str, default_value: Union[Dict, List, None] = None) -> Union[Dict, List]:
    """
    Loads JSON data from a file path with robust error handling.

    Args:
        file_path: The path to the JSON file.
        default_value: The value to return if the file is missing or invalid.
                       If None, returns {} for dict-like defaults or [] for list-like.

    Returns:
        The loaded dictionary or list, or the default value on error.
    """
    # Determine appropriate empty default if none provided
    empty_default: Union[Dict, List]
    if isinstance(default_value, list):
        empty_default = []
    else: # Includes default_value=None or dict
        empty_default = {}
    effective_default = default_value if default_value is not None else empty_default
    if not os.path.exists(file_path):
        return effective_default
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        # Basic type validation if default value suggests a type
        if default_value is not None and not isinstance(data, type(default_value)):
             print(f"[red]Error: Expected {type(default_value)} in {file_path}, found {type(data)}. Returning default.[/red]")
             return effective_default
        # Check type if no default provided (expect dict or list)
        elif default_value is None and not isinstance(data, (dict, list)):
             print(f"[red]Error: Expected dict or list in {file_path}, found {type(data)}. Returning empty {type(empty_default)}.[/red]")
             return empty_default
        return data
    except json.JSONDecodeError:
        print(f"[red]Error reading JSON from {file_path}. File might be corrupted. Returning default.[/red]")
        return effective_default
    except IOError as e:
        print(f"[red]Error accessing file {file_path}: {e}. Returning default.[/red]")
        return effective_default
    except Exception as e:
        print(f"[red]An unexpected error occurred loading {file_path}: {e}. Returning default.[/red]")
        traceback.print_exc()
        return effective_default

def save_json(file_path: str, data: Any) -> bool:
    """
    Saves data to a JSON file with error handling.

    Args:
        file_path: The path to save the JSON file.
        data: The data structure (dict, list, etc.) to save.

    Returns:
        True if saving was successful, False otherwise.
    """
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except TypeError as e:
        print(f"[red]Error saving JSON to {file_path}: Data contains non-serializable types. {e}[/red]")
        traceback.print_exc()
        return False
    except IOError as e:
        print(f"[red]Error writing to file {file_path}: {e}[/red]")
        return False
    except Exception as e:
        print(f"[red]An unexpected error occurred saving {file_path}: {e}[/red]")
        traceback.print_exc()
        return False

# --- Other Helper Functions ---
# <<< convert_to_london_timezone, get_timestamp, read_file, write_to_file remain unchanged >>>
def convert_to_london_timezone(timestamp: str) -> str:
    """Converts an ISO format timestamp string to London time 'YYYY-MM-DD HH:MM:S'."""
    try:
        utc_datetime = parse(timestamp) # dateutil.parser handles ISO format including Z or offset
        london_tz = pytz.timezone("Europe/London")
        # Ensure parsed datetime is aware before converting
        if utc_datetime.tzinfo is None:
             utc_datetime = pytz.utc.localize(utc_datetime)
             print("[yellow]Warning: Naive datetime string received in convert_to_london_timezone. Assuming UTC.[/yellow]")

        london_datetime = utc_datetime.astimezone(london_tz)
        return london_datetime.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError) as e:
         print(f"[red]Error converting timestamp '{timestamp}' to London time: {e}[/red]")
         return timestamp # Return original on error
    except Exception as e:
        print(f"[red]Unexpected error in convert_to_london_timezone: {e}[/red]")
        traceback.print_exc()
        return timestamp # Return original on error

def get_timestamp() -> str:
    """Returns the current timestamp in London time ('YYYY-MM-DD HH:MM:S')."""
    london_tz = pytz.timezone("Europe/London")
    return datetime.datetime.now(london_tz).strftime("%Y-%m-%d %H:%M:%S")

def read_file(file_path: str) -> str:
    """Reads entire content of a file. Consider specific loaders (like load_json) instead."""
    try:
        with open(file_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[red]Error: File not found at {file_path}[/red]")
        return ""
    except IOError as e:
        print(f"[red]Error reading file {file_path}: {e}[/red]")
        return ""
    except Exception as e:
        print(f"[red]Unexpected error reading file {file_path}: {e}[/red]")
        traceback.print_exc()
        return ""

def write_to_file(filename, data):
    """Appends data with a timestamp prefix. Consider structured logging."""
    try:
        with open(filename, "a") as file:
            file.write(f"#{get_timestamp()} ---------------------------------\n")
            file.write(str(data)) # Ensure data is string
            file.write("\n\n")
    except IOError as e:
         print(f"[red]Error writing to log file {filename}: {e}[/red]")
    except Exception as e:
         print(f"[red]Unexpected error writing log file {filename}: {e}[/red]")
         traceback.print_exc()

# <<< REVERTED: backup_json_files >>>
def backup_json_files():
    """
    Creates/updates daily backups of JSON files (YYYY-MM-DD--filename.json)
    and prunes backups older than backup_retention_days.
    """
    backups_dir = "backups"
    # backup_retention_days defined as a constant above
    files_backed_up = 0
    files_deleted = 0

    # Ensure backup directory exists
    try:
        if not os.path.exists(backups_dir):
            print(f"Creating backups directory: '{backups_dir}'")
            os.makedirs(backups_dir)
    except OSError as e:
        print(f"[red]Error creating backup directory '{backups_dir}': {e}. Backup aborted.[/red]")
        return

    # --- Create/Update Daily Backups ---
    # Use UTC date for consistency in naming
    current_date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    print(f"[cyan]Starting JSON backup process (Date: {current_date_str})...[/cyan]")
    try:
        for filename in os.listdir("."):
            if filename.endswith(".json"):
                source_file = os.path.join(".", filename)
                # Backup filename uses only the date prefix
                backup_file = os.path.join(backups_dir, f"{current_date_str}--{filename}")

                # shutil.copy2 handles overwriting the file if it already exists for today.
                try:
                    # print(f"Backing up '{source_file}' to '{backup_file}' (will overwrite if exists)") # Verbose
                    shutil.copy2(source_file, backup_file) # copy2 preserves metadata and overwrites
                    files_backed_up += 1
                except IOError as e:
                    print(f"[red]Error copying '{source_file}' to '{backup_file}': {e}[/red]")
                except Exception as e:
                    print(f"[red]Unexpected error backing up '{source_file}': {e}[/red]")

    except FileNotFoundError:
         print("[red]Error listing files in current directory '.' for backup.[/red]")
    except Exception as e:
         print(f"[red]Unexpected error during backup creation phase: {e}[/red]")
         traceback.print_exc()

    if files_backed_up > 0:
        print(f"[green]Backed up/updated {files_backed_up} JSON file(s) for date {current_date_str}.[/green]")
    else:
        print(f"[cyan]No JSON files found to back up.[/cyan]")

    # --- Prune Old Daily Backups ---
    print("[cyan]Checking for old daily backups to prune...[/cyan]")
    try:
        # Calculate cutoff datetime (aware in UTC)
        cutoff_datetime = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=backup_retention_days)

        for filename in os.listdir(backups_dir):
            file_path = os.path.join(backups_dir, filename)
            if not os.path.isfile(file_path): # Skip directories
                continue

            # Extract the date part from the filename prefix "YYYY-MM-DD--..."
            try:
                if "--" not in filename:
                    print(f"[yellow]Skipping prune check for unexpected filename format: '{filename}'[/yellow]")
                    continue

                date_part = filename.split("--")[0]
                # Parse date string and make it timezone-aware (assume UTC date)
                # Compare only the date part for daily pruning
                file_date = datetime.datetime.strptime(date_part, "%Y-%m-%d").date() # Get date object

                # Compare date part with cutoff date part
                if file_date < cutoff_datetime.date():
                    try:
                        # print(f"Deleting old backup file: '{file_path}' (Date: {date_part})") # Verbose
                        os.remove(file_path)
                        files_deleted += 1
                    except OSError as e:
                        print(f"[red]Error deleting old backup file '{file_path}': {e}[/red]")
            except (IndexError, ValueError):
                print(f"[yellow]Could not parse date from backup filename: '{filename}'. Skipping prune check.[/yellow]")
            except Exception as e:
                print(f"[red]Unexpected error processing backup file '{filename}' for pruning: {e}[/red]")

    except FileNotFoundError:
         print(f"[red]Error listing files in backup directory '{backups_dir}' for pruning.[/red]")
    except Exception as e:
         print(f"[red]Unexpected error during backup pruning phase: {e}[/red]")
         traceback.print_exc()

    if files_deleted > 0:
        print(f"[green]Pruned {files_deleted} daily backup file(s) older than {backup_retention_days} days.[/green]")
    else:
        print("[cyan]No old daily backup files found to prune.[/cyan]")


# <<< connectivity_check remains unchanged >>>
def connectivity_check(host="8.8.4.4", count=1, timeout=1, max_retries=5) -> bool:
    """Checks internet connectivity by pinging a reliable host."""
    print("[cyan]Checking network connectivity...[/cyan]")
    # Platform-specific ping command adjustments
    if platform.system().lower() == "windows":
        command = f"ping -n {count} -w {timeout * 1000} {host}"
    else:
        command = f"ping -c {count} -W {timeout} {host}"

    for attempt in range(max_retries):
        try:
            response = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 1)
            if response.returncode == 0:
                print("[green]Connectivity check successful.[/green]")
                return True
        except subprocess.TimeoutExpired:
             print(f"[yellow]Attempt {attempt + 1}: Ping command timed out.[/yellow]")
        except Exception as e:
             print(f"[red]Attempt {attempt + 1}: Error during connectivity check: {e}[/red]")

        if attempt < max_retries - 1:
            print(f"[yellow]Retrying connectivity check in {attempt + 1} sec...[/yellow]")
            time.sleep(attempt + 1)

    print("[bold red]_____________ CONNECTION FAILED after multiple retries _____________[/bold red]")
    return False