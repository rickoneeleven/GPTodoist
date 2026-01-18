# GPTodoist - Testing

DATETIME of last agent review: 18 Jan 2026 09:10 (Europe/London)

## Purpose
Fast sanity checks for Python syntax and import wiring (no test suite currently).

## Test Commands
- `python -m py_compile $(git ls-files '*.py')` - syntax check for tracked Python files
- `python -c "import main"` - verifies imports resolve (will require `TODOIST_API_KEY` at runtime)

## Key Test Files
- `main.py` - imports most modules and is the best smoke entrypoint

## Coverage Scope
- Module import errors
- Syntax errors

## Agent Testing Protocol
MANDATORY: run the relevant command(s) above after any code change.
