# GPTodoist - Overview

DATETIME of last agent review: 09 Feb 2026 20:44 (Europe/London)

## Purpose
Fast CLI workflow for interacting with Todoist tasks, plus local diary and long-term task handling (shows up to two next due long-term tasks each loop, with absolute due date/time surfaced).

## Key Files
- `main.py` - main loop and orchestration
- `helper_commands.py` - command dispatch (`ifelse_commands`)
- `helper_todoist_part1.py` - Todoist task operations (part 1)
- `helper_todoist_part2.py` - Todoist task operations (part 2)
- `pinescore_data_v1.py` - data.pinescore.com state hub client (ETag + If-Match)
- `pinescore_tasks_status.py` - computes `todo.tasks_up_to_date` payload from current loop state
- `helper_pinescore_status.py` - status push helpers + live background push loop
- `state_manager.py` - local state + backup timestamps + device guard
- `todoist_compat.py` - Todoist SDK compatibility and retries
- `long_term_*.py` - long-term task logic and indexing

## Related
- `requirements.txt` - runtime dependencies
- `ops/TESTING.md` - quick checks
- Shared state hub API shape (canonical): `https://data.pinescore.com/api_guide.txt` (snapshot: `ops/api_guide.txt`)

## Agent Commands
```bash
python --version
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TODOIST_API_KEY="..."
python main.py
```

## Notes
- `xx (t) <task>` logs an ad-hoc completion at tomorrow 09:00 (local time).
- Any `data.pinescore.com` integration must follow the API contract at `https://data.pinescore.com/api_guide.txt`.
- Auth tokens for `data.pinescore.com` are secrets and must be provided via env vars only (never committed).
- Optional: set `PINESCOREDATA_WRITE_TOKEN` to push `todo.tasks_up_to_date` to `data.pinescore.com` on loop refresh and in a background 5-minute loop (loop debug output prints `up_to_date` and `reason`, omitting `etag`; override interval with `PINESCOREDATA_BACKGROUND_INTERVAL_SECONDS`).
- `helper_todoist_part2.fetch_todoist_tasks` now uses `SIGALRM` timeout only on main thread; background sync path skips signal handlers safely.
- `module_call_counter.py` uses thread-safe, atomic JSON writes so background and main loops do not corrupt `j_function_calls.json`.
