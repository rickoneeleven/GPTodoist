import json
from datetime import datetime
from typing import List

REGULAR_HIDE_STATE_FILENAME = "j_regular_hidden.json"

def _get_current_date_str() -> str:
    """Returns the current date as a string in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")

def _load_regular_hide_state() -> dict:
    """Loads the regular task hide state from the JSON file."""
    try:
        with open(REGULAR_HIDE_STATE_FILENAME, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {} # Return empty if file is corrupt

def _save_regular_hide_state(state: dict):
    """Saves the regular task hide state to the JSON file."""
    with open(REGULAR_HIDE_STATE_FILENAME, 'w') as f:
        json.dump(state, f, indent=4)

def hide_task_for_today(task_id: str):
    """Hides a regular task for the current day."""
    state = _load_regular_hide_state()
    current_date = _get_current_date_str()

    if current_date not in state:
        state[current_date] = []
    
    if task_id not in state[current_date]:
        state[current_date].append(task_id)
        _save_regular_hide_state(state)

def get_hidden_task_ids_for_today() -> List[str]:
    """Returns a list of task IDs hidden for the current day."""
    state = _load_regular_hide_state()
    current_date = _get_current_date_str()
    return state.get(current_date, [])
