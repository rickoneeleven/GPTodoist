# GPTodoist - Testing

DATETIME of last agent review: 09 Feb 2026 15:47 (Europe/London)

## Purpose
Fast sanity checks for Python syntax, import wiring, and small unit tests.

## Test Commands
- `python -m py_compile $(git ls-files '*.py')` - syntax check for tracked Python files
- `python -c "import main"` - verifies imports resolve (will require `TODOIST_API_KEY` at runtime)
- `python -m unittest discover -s tests -p 'test_*.py'` - fast unit tests (no network)

## Key Test Files
- `main.py` - imports most modules and is the best smoke entrypoint

## Coverage Scope
- Module import errors
- Syntax errors

## Agent Testing Protocol
MANDATORY: run the relevant command(s) above after any code change.
If `python` is not available on the host, use `python3`.
