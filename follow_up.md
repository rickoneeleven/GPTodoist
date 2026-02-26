# Follow Up

## Feature: Recurring completion verifier delay
Status: Validating
Target env: local
Owner: agent
Created: 26 Feb 2026
Deployed:
Last touched: 26 Feb 2026

### Problem
- Completing a recurring long-term task can immediately re-fetch the same task with the same due key.
- This is usually Todoist eventual consistency. It looks like a bug and causes noisy logging and confusion.

### Proposal
- Wait up to ~8 seconds when verifying if a recurring task advanced.
- Show a “Todoist has not reflected the next recurrence yet” note instead of a hard warning.
- Only write `j_recurring_anomalies.json` when the recurrence string includes `starting YYYY-MM-DD` (known Todoist issue).

Pointers
- Main logic: `long_term_operations.py` `_verify_recurring_due_advanced` and `_get_due_key`
- Output and logging: `long_term_operations.py` `handle_recurring_task`, `long_term_complete.py` `complete_task`
- If you want to revisit “why the delay exists”, start by checking whether Todoist is still eventually consistent after close and how long it takes for `get_task(id)` to show the next due key.

### Acceptance Criteria
- [ ] Touching/completing a recurring long task does not print “recurrence due did not advance” for normal Todoist lag.
- [ ] `j_recurring_anomalies.json` is not created just because it is missing.
- [ ] If a task has a `starting YYYY-MM-DD` recurrence and fails to advance, it is logged.

### Validation Checklist (post-deploy)
- [ ] Verify no noisy warning on recurring touch
  - Command: run `python main.py`, then `touch long <index>` on a recurring long task
  - Expect: message says Todoist may be lagging, then task shows next occurrence later
  - Evidence:

- [ ] Verify anomalies only for `starting` rules
  - Command: inspect a recurring long task in Todoist that includes `starting YYYY-MM-DD`, then `touch long <index>`
  - Expect: anomaly entry written to `j_recurring_anomalies.json` if due key does not change after verifier wait
  - Evidence:
