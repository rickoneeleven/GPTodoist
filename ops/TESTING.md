# Testing

DATETIME of last agent review: 18 Mar 2026 09:59 (Europe/London)

## Purpose
Fast verification path for syntax, command dispatch, recurrence behavior, and Todoist client helpers.

## Fast Path
- `python3 -m py_compile $(git ls-files '*.py')` - syntax/import parse check for tracked Python files.
- `python3 -m unittest discover -s tests -p 'test_*.py'` - default unit suite, no live Todoist calls.

## Area Overrides
- `main.py`, `helper_pinescore_status.py`, `pinescore_*.py` -> `python3 -m unittest tests.test_helper_pinescore_status tests.test_pinescore_data_v1 tests.test_pinescore_tasks_status -v` - status push and shared-state contract behavior.
- `long_term_*.py`, `helper_todoist_long.py` -> `python3 -m unittest tests.test_long_term_operations -v` - long-task touch/complete recurrence checks.
- `helper_commands.py` -> `python3 -m unittest tests.test_helper_commands_reference -v` - startup command reference and dispatcher wiring.
- `helper_diary.py` -> `python3 -m unittest tests.test_helper_diary -v` - previous-tagline lookup and display behavior.
- `todoist_api.py` -> `python3 -m unittest tests.test_todoist_api_quick_add -v` - quick-add response-shape handling.

## Read-Only Runtime Checks
- `test -n "$TODOIST_API_KEY" && echo "TODOIST_API_KEY is set" || echo "TODOIST_API_KEY is missing"`
- `ls -1 j_*.json 2>/dev/null || true`

## Key Test Locations
- `tests/` - primary unit tests.
- `tests/test_long_term_operations.py` - recurring long-term behavior.
- `tests/test_helper_pinescore_status.py` - background owner-gate status flow.
- `tests/test_helper_due.py` - due/date normalization and recurrence metadata handling.
- `tests/test_helper_diary.py` - `diary yesterday` objective lookup behavior.

## Known Gaps
- No fully automated live integration test for real Todoist account side effects.
- No fully automated live integration test for background ownership against production `data.pinescore.com`.

## Agent Testing Protocol
**MANDATORY:** Run relevant tests after every feature or behavior change and fix failures immediately.

## Notes
- Prefer `python3`; some hosts in this project do not provide a `python` alias.
