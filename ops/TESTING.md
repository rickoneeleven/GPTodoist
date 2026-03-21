# Testing

DATETIME of last agent review: 21 Mar 2026 11:13 (Europe/London)

## Purpose
Fast verification path for syntax, command dispatch, long-task behavior, and shared-status helpers.

## Fast Path
- `python3 -m py_compile $(git ls-files '*.py')` - syntax and import parse check for tracked Python files
- `python3 -m unittest discover -s tests -p 'test_*.py'` - default unit suite, no live Todoist writes

## Area Overrides
- `main.py`, `helper_pinescore_status.py`, `pinescore_*.py` -> `python3 -m unittest tests.test_helper_pinescore_status tests.test_pinescore_data_v1 tests.test_pinescore_tasks_status -v` - shared-status publish and state-hub contract coverage
- `long_term_*.py`, `helper_todoist_long.py` -> `python3 -m unittest tests.test_long_term_operations tests.test_helper_due -v` - recurring completion, deferred due catch-up, and long-task indexing behavior
- `helper_commands.py` -> `python3 -m unittest tests.test_helper_commands_reference -v` - startup command reference and dispatcher wiring
- `helper_diary.py` -> `python3 -m unittest tests.test_helper_diary -v` - diary objective and yesterday-tagline behavior
- `helper_display.py` -> `python3 -m unittest tests.test_helper_display tests.test_helper_display_grouping -v` - task rendering and grouping output
- `todoist_api.py` -> `python3 -m unittest tests.test_todoist_api_quick_add -v` - quick-add response-shape handling
- `state_manager.py`, `j_todoist_filters.json` handling -> `python3 -m unittest tests.test_state_manager_filters -v` - active-filter toggling and persistence assumptions

## Read-Only Runtime Checks
- `test -n "$TODOIST_API_KEY" && echo "TODOIST_API_KEY is set" || echo "TODOIST_API_KEY is missing"` - confirm startup secret presence
- `ls -1 j_*.json 2>/dev/null || true` - inspect local state surface without mutating it

## Key Test Locations
- `tests/` - primary unit test suite
- `tests/test_long_term_operations.py` - recurring long-task verification
- `tests/test_helper_pinescore_status.py` - background owner-gate behavior
- `tests/test_helper_due.py` - due-date normalization, safe recurring deferral, and deferred completion catch-up
- `tests/test_helper_commands_reference.py` - command reference and dispatcher expectations

## Known Gaps
- No automated live integration test for a real Todoist account
- No automated live integration test for production `data.pinescore.com` ownership flows

## Agent Testing Protocol
**MANDATORY:** Run relevant tests after every feature or behavior change and fix failures immediately.

## Notes
- Prefer `python3`; this repo should not assume a `python` alias exists.
