# GPTodoist

DATETIME of last agent review: 03 Feb 2026 17:50 (Europe/London)

A command-line interface (CLI) tool for fast interaction with your Todoist account: pick and act on an active task, manage long-term tasks, and generate diary and timesheet entries from completed items.

## Stack
- Python 3.10 to 3.11 (see `pyproject.toml`, tested with 3.11)
- Todoist REST via `todoist_api_python`
- Dependencies pinned in `requirements.txt`

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
export TODOIST_API_KEY="YOUR_ACTUAL_API_KEY"
python main.py
```

## Configuration

### Todoist API Key
Set `TODOIST_API_KEY` in your shell environment (Todoist: Settings -> Integrations -> Developer -> API token).

### Active Filters (`j_todoist_filters.json`)
Defines filter views you can cycle using `flip`. The filter with `isActive: 1` is used for fetching and displaying tasks.

- File: `j_todoist_filters.json` (create it in the project root if missing)
- Structure: JSON list containing filter objects
- Fields:
  - `id`: integer identifier (currently unused)
  - `filter`: Todoist filter query string
  - `isActive`: `1` for active, `0` for inactive (only one should be active)
  - `project_id`: optional project ID used by `add task ...`

Example:
```json
[
  { "id": 1, "filter": "(no due date | today | overdue) & #Inbox", "isActive": 1, "project_id": "" },
  { "id": 2, "filter": "(today | overdue | no due date) & #RCP", "isActive": 0, "project_id": "2294289600" }
]
```

## Usage
```bash
python main.py
```

The main loop shows up to two Next Long Tasks automatically (recurring first, then one-shots; only due or overdue). Use `show long` to list all due long tasks.

## Commands Reference
Commands are matched case-insensitively.

### Core Task Actions (Active Task)
- `done`: Complete and log to `j_todays_completed_tasks.json`
- `skip`: Complete without logging
- `delete`: Delete from Todoist
- `time <due_string>`: Set due date/time
- `postpone <due_string>`: Postpone (recurring: complete and recreate)
- `rename <new_name>`: Rename
- `priority <1|2|3|4>`: Set priority (1=P1 High, 4=P4 Low)

### Task Creation
- `add task <content>`: Create task (uses active filter `project_id` if set)
- `xx <task_name>`: Log an ad-hoc completion without creating a Todoist task
- `xx (t) <task_name>`: Log an ad-hoc completion as if completed tomorrow at 09:00

### Fuzzy Matching / Search
- `~~~ <fuzzy_name>`: Fuzzy match and complete from active filter
- `||| <search_term>`: Search Todoist and show results

### Display & View Commands
- `all` / `show all`: Show tasks in active filter plus due long-term tasks
- `completed` / `show completed`: Show today's locally logged completions
- `flip`: Cycle active filter in `j_todoist_filters.json`
- `hide`: Hide the current regular task until tomorrow (stored in `j_regular_hidden.json`)
- `clear`: Clear terminal

### Long-Term Task Management ("Long Term Tasks" project)
- `show long`: Show due long-term tasks (requires `[index]` prefixes)
- `add long <task_name>`: Create long-term task with next `[index]`
- `time long <index> <schedule>`: Reschedule
- `skip long <index>`: Touch without logging completion
- `touch long <index>`: Touch and log completion
- `hide long <index>`: Hide for today only (Europe/London)
- `rename long <index> <new_name>`: Rename (keeps index)
- `delete long <index>`: Delete
- `priority long <index> <1|2|3|4>`: Set priority
- `postpone long <index> <schedule>`: Postpone (recurring: complete and recreate)

### Diary & Timesheets
- `diary`: View diary (prompts for day/week)
- `diary <objective>`: Update today's `overall_objective` in `j_diary.json`
- `timesheet`: Build a timesheet entry from completed tasks

## Todoist SDK Upgrade Note
- Uses Todoist SDK 3.x (`requirements.txt`: `todoist_api_python>=3.1.0,<4`; `pyproject.toml`: `todoist-api-python = "^3.1.0"`)
- Compatibility layer: `todoist_compat.py` smooths SDK method differences and adds retry/backoff
