import pytz
from datetime import datetime
from typing import Set
from rich import print

from helper_general import load_json, save_json


HIDE_STATE_FILENAME = "j_long_hidden.json"


def _today_str_london() -> str:
    london_tz = pytz.timezone("Europe/London")
    return datetime.now(london_tz).strftime("%Y-%m-%d")


def _default_state() -> dict:
    return {"date": _today_str_london(), "indices": []}


def _load_state() -> dict:
    # load_json will create file with default if missing
    state = load_json(HIDE_STATE_FILENAME, default_value=_default_state())
    if not isinstance(state, dict):
        state = _default_state()
    # Normalize keys
    if "date" not in state or "indices" not in state or not isinstance(state.get("indices"), list):
        state = _default_state()
    return state


def _save_state(state: dict) -> bool:
    return save_json(HIDE_STATE_FILENAME, state)


def hide_task_for_today(index: int) -> bool:
    """Hide the given [index] for today, purging old day entries automatically."""
    if not isinstance(index, int):
        print("[red]Invalid index for hide. Must be an integer.[/red]")
        return False

    state = _load_state()
    today = _today_str_london()

    # Auto-purge if file is from a previous day
    if state.get("date") != today:
        state = {"date": today, "indices": []}

    if index not in state["indices"]:
        state["indices"].append(index)
        state["indices"].sort()

    saved = _save_state(state)
    if saved:
        print(f"[cyan]Hidden long task index [{index}] for {today}.[/cyan]")
    else:
        print("[red]Failed to update local hide list file.[/red]")
    return saved


def get_hidden_indices_for_today() -> Set[int]:
    """Return a set of indices hidden for today. Ignores stale days without mutating file."""
    state = _load_state()
    today = _today_str_london()
    if state.get("date") != today:
        return set()
    indices = state.get("indices", [])
    if not isinstance(indices, list):
        return set()
    # Keep only ints
    return {int(i) for i in indices if isinstance(i, int) or (isinstance(i, str) and i.isdigit())}

