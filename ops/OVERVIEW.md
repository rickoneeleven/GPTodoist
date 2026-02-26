# GPTodoist - Overview
DATETIME of last agent review: 16 Feb 2026 12:27 (Europe/London)

## Purpose
Fast CLI workflow for interacting with Todoist tasks, plus local diary and long-term task handling (shows up to two next due long-term tasks each loop, with absolute due date/time surfaced).

## Key Files
- `main.py` - main loop and orchestration
- `helper_commands.py` - command dispatch (`ifelse_commands`)
- `helper_todoist_part1.py` + `regular_due.py` - active-task actions and `due` command flow
- `helper_todoist_part2.py` - Todoist task operations (part 2)
- `todoist_api.py` - Todoist HTTP client (uses `/api/v1/*`)
- `todoist_errors.py` - user-friendly Todoist HTTP error text
- `pinescore_data_v1.py` - data.pinescore.com state hub client (ETag + If-Match)
- `pinescore_tasks_status.py` - computes `todo.tasks_up_to_date` payload from current loop state
- `helper_pinescore_status.py` - status push helpers + live background push loop
- `state_manager.py` - local state + backup timestamps + device guard
- `todoist_compat.py` - Todoist call compatibility + retries/backoff (429/5xx)
- `long_term_*.py` + `long_term_due.py` + `long_term_complete.py` - long-term task logic, indexing, and long-task completion

## Related
- `requirements.txt` - runtime dependencies
- `ops/TESTING.md` - quick checks
- Shared state hub API shape (canonical): `https://data.pinescore.com/api_guide.txt` (snapshot: `ops/api_guide.txt`)

## Agent Commands
- Setup/run: see `README.md` (venv, `requirements.txt`, `TODOIST_API_KEY`, `python main.py`)

## Notes
- `xx (t) <task>` logs an ad-hoc completion at tomorrow 09:00 (local time).
- Any `data.pinescore.com` integration must follow the API contract at `https://data.pinescore.com/api_guide.txt`.
- Auth tokens for `data.pinescore.com` are secrets and must be provided via env vars only (never committed).
- Todoist `/rest/v2/*` is deprecated and returns HTTP 410; GPTodoist uses `/api/v1/*`.
- Optional: set `PINESCOREDATA_WRITE_TOKEN` to push `todo.tasks_up_to_date` to `data.pinescore.com` on loop refresh and in a background 5-minute loop (loop debug output prints `up_to_date` and `reason`, omitting `etag`; override interval with `PINESCOREDATA_BACKGROUND_INTERVAL_SECONDS`).
- Background status push has device ownership gating: only `todo.tasks_background_owner_device_id` can publish from the 5-minute loop, and manual non-empty user input claims ownership via `todo.tasks_background_owner_*` fields.
- `helper_todoist_part2.fetch_todoist_tasks` supports explicit filter overrides and still uses `SIGALRM` timeout only on main thread.
- `module_call_counter.py` uses thread-safe, atomic JSON writes so background and main loops do not corrupt `j_function_calls.json`.
- At startup, a command quick reference prints before regular/long task output.
- `done long <index>` completes the long-term task; recurring tasks will reappear per schedule.
