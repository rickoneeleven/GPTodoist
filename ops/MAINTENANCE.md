# Maintenance Notes

DATETIME of last agent review: 26 Feb 2026 13:24 (Europe/London)

## Purpose
Quick log of recent dead-code audits to avoid redoing the same work.

## Key Files
- `helper_todoist_part1.py` - dead code removal applied (96 lines removed, 2025-06-22)
- `helper_todoist_part2.py` - high-quality, minimal dead code (2025-06-22)
- `helper_timesheets.py` - high-quality, minimal dead code (2025-06-22)
- `done long <index>` now truly completes long tasks; `touch long <index>` keeps the "push non-recurring to tomorrow" behavior and logs touches distinctly
- `helper_due.py` - fixed `due_date`/`due_datetime` payload types for Todoist SDK (`date`/`datetime`, not strings)
- `helper_due.py` - recurrence recovery: strip `starting YYYY-MM-DD` anchors entirely (Todoist bug: `starting` anchors can stop recurrence from advancing on completion)
- `helper_display.py` - normalize `due.date` datetimes to pure dates before objective bucket comparisons, preventing `datetime` vs `date` TypeError after timesheet refresh
- Recurring long-task completion now verifies due advancement and suppresses stale "still due" reads for ~20s (Todoist eventual consistency)
- Long task scheduling now refuses user schedules containing `starting YYYY-MM-DD` and logs recurrence non-advancement events to `j_recurring_anomalies.json`

## Agent Commands
```bash
python -m py_compile $(git ls-files '*.py')
```
