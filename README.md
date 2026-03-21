# GPTodoist

DATETIME of last agent review: 21 Mar 2026 11:13 (Europe/London)

Interactive Python CLI for Todoist task execution, long-term task handling, and local diary/timesheet tracking.

## Stack
- Python `>=3.10,<3.12` from `pyproject.toml`
- Dependencies from `requirements.txt`: `requests`, `rich`, `python-dateutil`, `pytz`, `fuzzywuzzy`, `levenshtein`, `pyfiglet`, `pyowm`
- Todoist HTTP client in `todoist_api.py` against `https://api.todoist.com/api/v1/*`
- Optional shared-status integration with `https://data.pinescore.com/v1/*`

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
- `TODOIST_API_KEY`: Todoist API token. `main.py` reads this at import time, so startup fails immediately if it is missing.

Optional environment variables:
- `PINESCOREDATA_WRITE_TOKEN`: enables shared status writes to `data.pinescore.com`
- `PINESCOREDATA_BASE_URL`: defaults to `https://data.pinescore.com`
- `PINESCOREDATA_UPDATED_BY`: defaults to `gptodoist`
- `PINESCOREDATA_DEVICE_ID`: overrides the derived device identifier used for ownership gating
- `PINESCOREDATA_DEVICE_LABEL`: overrides the readable device label sent to shared status
- `PINESCOREDATA_BACKGROUND_INTERVAL_SECONDS`: background status push interval in seconds, default `300`
- `TODOIST_FILTER_LANG`: language sent to Todoist filter queries, default `en`

Runtime state lives in JSON files at repo root. Important files include:
- `j_todoist_filters.json`: active filter rotation plus optional `project_id` for `add task`
- `j_active_task.json`: active-task ownership lock
- `j_options.json`: backup timestamp and all-done celebration state
- `j_recurring_anomalies.json`: recurring long-task anomaly log when Todoist does not advance due state

`j_todoist_filters.json` uses this shape:
```json
[
  { "id": 1, "filter": "(no due date | today | overdue) & #Inbox", "isActive": 1, "project_id": "" },
  { "id": 2, "filter": "(today | overdue | no due date) & #RCP", "isActive": 0, "project_id": "2294289600" }
]
```

Long-term commands require a Todoist project named exactly `Long Term Tasks`.

## Common Operations
Start the CLI:
```bash
python3 main.py
```

Default verification after edits:
```bash
python3 -m py_compile $(git ls-files '*.py')
python3 -m unittest discover -s tests -p 'test_*.py'
```

Focused verification for the most sensitive areas:
```bash
python3 -m unittest tests.test_long_term_operations tests.test_helper_pinescore_status -v
python3 -m unittest tests.test_todoist_api_quick_add tests.test_helper_commands_reference -v
```

The startup command reference is printed by `helper_commands.py` and covers regular task, long-task, diary, and timesheet commands.

## Troubleshooting
### Startup fails before the prompt appears
- Check `TODOIST_API_KEY`: `test -n "$TODOIST_API_KEY" && echo "TODOIST_API_KEY is set" || echo "TODOIST_API_KEY is missing"`
- `main.py` constructs `TodoistAPI` during import, so a missing token stops the process before the command loop starts.

### Long-term commands do not work
- Confirm the Todoist project name is exactly `Long Term Tasks`.
- Long-task helpers resolve the project by exact name in `long_term_core.py`.

### Shared status updates are skipped or look stale
- Background pushes run only when `PINESCOREDATA_WRITE_TOKEN` is set and the local device owns `todo.tasks_background_owner_device_id`.
- A manual non-empty command claims ownership for the local device. Another device can block background updates until ownership changes.

### Unexpected Todoist API errors
- This repo is pinned to `/api/v1/*`. Regressing to deprecated `/rest/v2/*` endpoints will break requests.
- Quick-add handling expects Todoist's current `/tasks/quick` response shapes and falls back to `task_id` or `item_id` when needed.

### Backup noise or missing history
- The CLI checks backups once per loop and copies all root `*.json` files into `backups/`.
- Old backups are pruned after 10 days in `helper_general.py`.

## Links
- Agent runtime map: `ops/manifest.yaml`
- Test command map: `ops/TESTING.md`
- Runtime caveats: `ops/runtime.md`
- Pinescore API reference: `ops/api_guide.txt`
