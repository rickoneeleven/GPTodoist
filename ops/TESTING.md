# GPTodoist - Testing

DATETIME of last agent review: 16 Feb 2026 10:20 (Europe/London)

## Purpose
Fast sanity checks for Python syntax, import wiring, and small unit tests.

## Test Commands
- `python -m py_compile $(git ls-files '*.py')` - syntax check for tracked Python files
- `python -c "import main"` - verifies imports resolve (will require `TODOIST_API_KEY` at runtime)
- `python -m unittest discover -s tests -p 'test_*.py'` - fast unit tests (no network)

## Key Test Files
- `main.py` - imports most modules and is the best smoke entrypoint
- `tests/test_helper_due.py` - due-date normalization and due-preserving payload behavior
- `tests/test_helper_display.py` - today/overdue view query derivation
- `tests/test_helper_display_grouping.py` - grouped objective view task bucketing and sorting
- `tests/test_helper_pinescore_status.py` - data.pinescore.com status patch, ownership claim, and background ownership gate behavior
- `tests/test_helper_todoist_part2_signal.py` - signal timeout safety and explicit filter-override query behavior
- `tests/test_state_manager_filters.py` - robust `isActive` parsing for filter selection

## Coverage Scope
- Module import errors
- Syntax errors

## Agent Testing Protocol
MANDATORY: run the relevant command(s) above after any code change.
If `python` is not available on the host, use `python3`.
