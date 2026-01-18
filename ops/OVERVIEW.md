# GPTodoist - Overview

DATETIME of last agent review: 18 Jan 2026 09:10 (Europe/London)

## Purpose
Fast CLI workflow for interacting with Todoist tasks, plus local diary and long-term task handling.

## Key Files
- `main.py` - main loop and orchestration
- `helper_commands.py` - command dispatch (`ifelse_commands`)
- `helper_todoist_part1.py` - Todoist task operations (part 1)
- `helper_todoist_part2.py` - Todoist task operations (part 2)
- `state_manager.py` - local state + backup timestamps + device guard
- `todoist_compat.py` - Todoist SDK compatibility and retries
- `long_term_*.py` - long-term task logic and indexing

## Related
- `requirements.txt` - runtime dependencies
- `ops/TESTING.md` - quick checks

## Agent Commands
```bash
python --version
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TODOIST_API_KEY="..."
python main.py
```
