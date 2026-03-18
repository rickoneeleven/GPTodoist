# Runtime Notes

DATETIME of last agent review: 18 Mar 2026 09:59 (Europe/London)

## Purpose
Operational guardrails for the interactive loop, long-task behavior, and optional pinescore status publishing.

## Open When
- Touching: `main.py`, `helper_pinescore_status.py`, `todoist_api.py`, `long_term_*.py`.
- Investigating: missing long-task actions, ownership-gated status push skips, or recurring non-advancement logs.
- Deploying: environment variable changes for Todoist or pinescore integration.

## Runtime Facts
- Entrypoint is `main.py`; this starts the CLI loop and optional background status thread.
- `TODOIST_API_KEY` is mandatory at startup; `main.py` reads it immediately.
- Long-task helpers require Todoist project name `Long Term Tasks` (exact match).
- Local state is JSON in repo root; hourly backup copies root JSON files into `backups/`.
- Todoist client is pinned to `/api/v1/*`; do not regress to deprecated `/rest/v2/*`.
- Shared status integration follows `ops/api_guide.txt` and uses ETag/If-Match semantics.

## Read-Only Checks
```bash
python3 -m py_compile $(git ls-files '*.py')
python3 -m unittest tests.test_helper_pinescore_status tests.test_pinescore_data_v1 tests.test_long_term_operations -v
```

## Operator Actions
```bash
export TODOIST_API_KEY="YOUR_TODOIST_TOKEN"
python3 main.py
```

## Gotchas
- Background pinescore updates publish only from the current owner device id.
- Manual non-empty input claims ownership; idle devices are intentionally blocked.
