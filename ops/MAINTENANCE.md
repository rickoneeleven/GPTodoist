# Maintenance Notes

DATETIME of last agent review: 18 Jan 2026 09:10 (Europe/London)

## Purpose
Quick log of recent dead-code audits to avoid redoing the same work.

## Key Files
- `helper_todoist_part1.py` - dead code removal applied (96 lines removed, 2025-06-22)
- `helper_todoist_part2.py` - high-quality, minimal dead code (2025-06-22)
- `helper_timesheets.py` - high-quality, minimal dead code (2025-06-22)

## Agent Commands
```bash
python -m py_compile $(git ls-files '*.py')
```
