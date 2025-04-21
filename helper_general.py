# File: helper_general.py
import datetime, os, pytz, json, shutil, time, traceback # Added traceback
import helper_general # Keep for potential internal use (though less likely now)
from dateutil.parser import parse
from typing import Any, Union, Dict, List # Added Dict, List for more specific typing
from rich import print

# --- Constants ---
OPTIONS_FILENAME = "j_options.json" # Default options file name
DEFAULT_OPTIONS = {"enable_diary_prompts": "yes", "last_backup_timestamp": None} # Example default options

# --- Robust JSON Handling ---

# <<< MODIFIED: Enhanced load_json >>>
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
        # print(f"[yellow]File not found: {file_path}. Returning default.[/yellow]") # Less verbose
        # Optionally create file with default content if needed
        # if default_value is not None:
        #    save_json(file_path, default_value) # Be cautious with auto-creation
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

# <<< MODIFIED: Enhanced save_json >>>
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
        # Ensure data is JSON serializable before opening file (optional early check)
        # json.dumps(data)

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except TypeError as e:
        # Error if data contains non-serializable types
        print(f"[red]Error saving JSON to {file_path}: Data contains non-serializable types. {e}[/red]")
        traceback.print_exc() # Log stack trace for debugging problematic data
        return False
    except IOError as e:
        print(f"[red]Error writing to file {file_path}: {e}[/red]")
        return False
    except Exception as e:
        print(f"[red]An unexpected error occurred saving {file_path}: {e}[/red]")
        traceback.print_exc()
        return False

# --- Other Helper Functions (Unchanged unless dependency needed modification) ---

def convert_to_london_timezone(timestamp: str) -> str:
    """Converts an ISO format timestamp string to London time 'YYYY-MM-DD HH:MM:S'."""
    try:
        utc_datetime = parse(timestamp) # dateutil.parser handles ISO format including Z or offset
        london_tz = pytz.timezone("Europe/London")
        # Ensure parsed datetime is aware before converting
        if utc_datetime.tzinfo is None:
             # Attempt to localize as UTC if naive, though ISO should ideally include timezone
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

# <<< DEPRECATED CANDIDATE: read_file - load_json/standard open preferred >>>
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


# <<< DEPRECATED CANDIDATE: write_to_file - Specific logging handlers preferred >>>
def write_to_file(filename, data):
    """Appends data with a timestamp prefix. Consider structured logging."""
    try:
        with open(filename, "a") as file:
            # Use the updated get_timestamp from this module
            file.write(f"#{get_timestamp()} ---------------------------------\n")
            file.write(str(data)) # Ensure data is string
            file.write("\n\n")
    except IOError as e:
         print(f"[red]Error writing to log file {filename}: {e}[/red]")
    except Exception as e:
         print(f"[red]Unexpected error writing log file {filename}: {e}[/red]")
         traceback.print_exc()


def backup_json_files():
    """Creates dated backups of JSON files and prunes old backups."""
    backups_dir = "backups"
    backup_retention_days = 10
    files_backed_up = 0
    files_deleted = 0

    # Ensure backup directory exists
    try:
        if not os.path.exists(backups_dir):
            print(f"Creating backups directory: '{backups_dir}'")
            os.makedirs(backups_dir)
    except OSError as e:
        print(f"[red]Error creating backup directory '{backups_dir}': {e}. Backup aborted.[/red]")
        return # Cannot proceed without backup dir

    # Generate the current date-time string for backup prefix
    # Use UTC date for consistency regardless of local timezone changes
    current_date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    # --- Create Backups ---
    print("[cyan]Starting JSON backup process...[/cyan]")
    try:
        for filename in os.listdir("."):
            if filename.endswith(".json"):
                source_file = os.path.join(".", filename) # Explicitly join with current dir
                backup_file = os.path.join(backups_dir, f"{current_date_str}--{filename}")

                # Avoid backing up if a backup for today already exists
                if os.path.exists(backup_file):
                    # print(f"[dim]Skipping backup for '{filename}', already exists for today.[/dim]")
                    continue

                try:
                    # print(f"Backing up '{source_file}' to '{backup_file}'") # Verbose
                    shutil.copy2(source_file, backup_file) # copy2 preserves metadata
                    files_backed_up += 1
                except IOError as e:
                    print(f"[red]Error copying '{source_file}' to '{backup_file}': {e}[/red]")
                except Exception as e: # Catch other potential errors like permissions
                    print(f"[red]Unexpected error backing up '{source_file}': {e}[/red]")

    except FileNotFoundError:
         print("[red]Error listing files in current directory '.' for backup.[/red]")
    except Exception as e:
         print(f"[red]Unexpected error during backup creation phase: {e}[/red]")
         traceback.print_exc()

    if files_backed_up > 0:
        print(f"[green]Backed up {files_backed_up} JSON file(s).[/green]")
    else:
        print("[cyan]No new JSON files needed backup today.[/cyan]")

    # --- Prune Old Backups ---
    print("[cyan]Checking for old backups to prune...[/cyan]")
    try:
        cutoff_datetime = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=backup_retention_days)

        for filename in os.listdir(backups_dir):
            file_path = os.path.join(backups_dir, filename)
            if not os.path.isfile(file_path): # Skip directories if any exist
                continue

            # Extract the date from the filename prefix
            try:
                # Regex might be safer if format varies, but split is simpler for fixed format
                date_part = filename.split("--")[0]
                # Parse date string and make it timezone-aware (assume UTC date)
                file_date = datetime.datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)

                # Compare dates (aware vs aware)
                if file_date < cutoff_datetime:
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
        print(f"[green]Pruned {files_deleted} backup file(s) older than {backup_retention_days} days.[/green]")
    else:
        print("[cyan]No old backup files found to prune.[/cyan]")


def connectivity_check(host="8.8.4.4", count=1, timeout=1, max_retries=5) -> bool:
    """
    Checks internet connectivity by pinging a reliable host.

    Args:
        host: The IP address or hostname to ping.
        count: Number of ping packets to send per attempt.
        timeout: Timeout in seconds for each ping command.
        max_retries: Maximum number of ping attempts before declaring failure.

    Returns:
        True if connectivity is established, False otherwise.
    """
    print("[cyan]Checking network connectivity...[/cyan]")
    # Platform-specific ping command adjustments
    if platform.system().lower() == "windows":
        # Windows uses -n for count and -w for timeout (in milliseconds)
        command = f"ping -n {count} -w {timeout * 1000} {host}"
    else:
        # Linux/macOS use -c for count and -W for timeout (in seconds)
        command = f"ping -c {count} -W {timeout} {host}"

    for attempt in range(max_retries):
        try:
            # Redirect output to DEVNULL to keep terminal clean
            response = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 1) # Added timeout to subprocess
            if response.returncode == 0:
                print("[green]Connectivity check successful.[/green]")
                return True
        except subprocess.TimeoutExpired:
             print(f"[yellow]Attempt {attempt + 1}: Ping command timed out.[/yellow]")
        except Exception as e:
             print(f"[red]Attempt {attempt + 1}: Error during connectivity check: {e}[/red]")
             # Don't retry on unexpected errors? Or maybe do? Let's retry for now.

        if attempt < max_retries - 1:
            print(f"[yellow]Retrying connectivity check in {attempt + 1} sec...[/yellow]")
            time.sleep(attempt + 1) # Exponential backoff (simple version)

    print("[bold red]_____________ CONNECTION FAILED after multiple retries _____________[/bold red]")
    return False