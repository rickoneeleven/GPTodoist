# GPTodoist

DATETIME of last agent review: 18 Mar 2026 09:59 (Europe/London)

Interactive CLI for Todoist task execution, long-term task handling, and local diary/timesheet tracking.

## Stack
- Python `>=3.10,<3.12` (from `pyproject.toml`; tested with `python3`)
- Todoist API client in `todoist_api.py` using `https://api.todoist.com/api/v1/*`
- Optional shared status integration with `https://data.pinescore.com/v1/*`
- Dependencies in `requirements.txt` (`requests`, `rich`, `python-dateutil`, `pytz`, `fuzzywuzzy`, etc.)

## Quick Start
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
export TODOIST_API_KEY="YOUR_TODOIST_TOKEN"
python3 main.py
```

## Configuration
Required environment variable:
- `TODOIST_API_KEY`: Todoist API token (Settings -> Integrations -> Developer).

Optional environment variables:
- `PINESCOREDATA_WRITE_TOKEN`: enables status pushes to `data.pinescore.com`.
- `PINESCOREDATA_BASE_URL`: override base URL (default `https://data.pinescore.com`).
- `PINESCOREDATA_UPDATED_BY`: source tag for state updates (default `gptodoist`).
- `PINESCOREDATA_DEVICE_ID`: stable device ID override for background ownership.
- `PINESCOREDATA_DEVICE_LABEL`: readable device label override.
- `PINESCOREDATA_BACKGROUND_INTERVAL_SECONDS`: background push interval (default `300`).
- `TODOIST_FILTER_LANG`: language sent to Todoist task filter API (default `en`).

`j_todoist_filters.json` controls active filter selection (`flip`) and optional `project_id` for `add task`:
```json
[
  { "id": 1, "filter": "(no due date | today | overdue) & #Inbox", "isActive": 1, "project_id": "" },
  { "id": 2, "filter": "(today | overdue | no due date) & #RCP", "isActive": 0, "project_id": "2294289600" }
]
```

Long-term commands require a Todoist project named exactly `Long Term Tasks`.

## Common Operations
Start the app:
```bash
python3 main.py
```

Quick verification after edits:
```bash
python3 -m py_compile $(git ls-files '*.py')
python3 -m unittest discover -s tests -p 'test_*.py'
```

In-app command help is printed at startup (`helper_commands.print_startup_command_reference()`), including:
- regular task actions (`done`, `due`, `postpone`, `add task`, `hide`)
- long-task actions (`show long`, `add long`, `done long`, `touch long`, `due long`)
- diary/timesheet actions (`diary`, `timesheet`)

Operational behavior:
- Backup runs hourly from `main.py` and copies all root `*.json` files into `backups/`.
- Backup pruning keeps the latest 10 days (`helper_general.backup_retention_days`).
- Optional pinescore status push runs each loop and in an owned background thread.

## Troubleshooting
### `python: command not found`
Use `python3` for all commands on hosts where `python` is not linked.

### Todoist auth/startup failures
- `TODOIST_API_KEY` is required at import time in `main.py`.
- If missing, startup fails before command loop begins.
- If wrong, Todoist API calls return `401 Unauthorized`.

### Long-term commands unavailable
Create a Todoist project named `Long Term Tasks`; long-task helpers resolve project ID by exact name.

### Unexpected Todoist endpoint errors
This repo is pinned to `/api/v1/*`. Avoid switching back to deprecated `/rest/v2/*` endpoints.

### Background status updates not publishing
Background pushes are owner-gated by `todo.tasks_background_owner_device_id`.
Manual non-empty input claims ownership; stale devices are intentionally blocked.

## Links
- Agent runtime map: `ops/manifest.yaml`
- Test command map: `ops/TESTING.md`
- Pinescore API snapshot: `ops/api_guide.txt`
