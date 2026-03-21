# Runtime Notes

DATETIME of last agent review: 21 Mar 2026 11:13 (Europe/London)

## Purpose
Operational guardrails for the interactive loop, long-task flows, backup behavior, and optional shared-status publishing.

## Open When
- Touching: `main.py`, `helper_pinescore_status.py`, `state_manager.py`, `long_term_*.py`
- Investigating: blocked commands, missing long-task actions, noisy recurring warnings, or skipped status pushes
- Deploying: Todoist or `PINESCOREDATA_*` environment changes

## Runtime Facts
- `main.py` starts the CLI loop, hourly backup checks, and an optional `pinescore-status-push` background thread.
- `TODOIST_API_KEY` is mandatory at startup; `PINESCOREDATA_WRITE_TOKEN` enables shared-status writes.
- Long-term task commands depend on a Todoist project named exactly `Long Term Tasks`.
- Local runtime state is stored in root JSON files; `backups/` receives daily copies of every root `*.json` file.
- Shared-status writes use `data.pinescore.com/v1/state` with ownership gating and ETag-based concurrency.
- Recurring `due` updates may store local defer-until dates in `j_recurring_due_deferrals.json` when Todoist cannot safely jump a future recurrence.

## Read-Only Checks
```bash
test -n "$TODOIST_API_KEY" && echo "TODOIST_API_KEY is set" || echo "TODOIST_API_KEY is missing"
python3 -m unittest tests.test_helper_pinescore_status tests.test_long_term_operations -v
```

## Operator Actions
```bash
export TODOIST_API_KEY="YOUR_TODOIST_TOKEN"
python3 main.py
```

## Gotchas
- Commands are blocked when `j_active_task.json` points at a different device id than the local machine.
- A manual non-empty command claims shared-status background ownership for the local device.
- Recurring long-task verification tolerates Todoist lag before treating due advancement as anomalous.
- When a recurring touch does not advance, the CLI now prints Todoist validation fields such as `due_key`, `checked`, and `updated_at`.
- `due` and `due long` now prefer a safe recurring rule over re-adding `starting YYYY-MM-DD`, even if Todoist shifts the next occurrence.
- For recurring tasks moved earlier, `due` now updates the existing Todoist task in place with the same recurrence plus an explicit earlier date, instead of re-anchoring the rule or recreating the task.
- When a recurring task is moved later than Todoist can safely advance today, the app defers it locally and catches up skipped overdue occurrences at completion time.
