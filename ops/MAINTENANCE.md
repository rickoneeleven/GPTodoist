# Maintenance Notes

DATETIME of last agent review: 17 Feb 2026 08:36 (Europe/London)

## Purpose
Quick log of recent dead-code audits to avoid redoing the same work.

## Key Files
- `helper_todoist_part1.py` - dead code removal applied (96 lines removed, 2025-06-22)
- `helper_todoist_part2.py` - high-quality, minimal dead code (2025-06-22)
- `helper_timesheets.py` - high-quality, minimal dead code (2025-06-22)
- `helper_due.py` - fixed `due_date`/`due_datetime` payload types for Todoist SDK (`date`/`datetime`, not strings)
- `helper_display.py` - normalize `due.date` datetimes to pure dates before objective bucket comparisons, preventing `datetime` vs `date` TypeError after timesheet refresh

## Agent Commands
```bash
python -m py_compile $(git ls-files '*.py')
```
