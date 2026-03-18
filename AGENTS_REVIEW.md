# Agent Instructions: Critical Breakage Audit v5 (Iterative Index-Ratchet / Commit Review)
Review instruction version: CRBA-v5.0-2026-03-07

## Mission
Assume I make large, sweeping changes. Your job is not a normal code review; it is a **breakage prevention audit**.

Treat every change as suspicious until proven safe. Use your effort to **trace execution paths, data flow, and integration boundaries** to find anything that could cause:
- crashes / unhandled exceptions
- broken user flows
- data loss / corruption
- security/auth bypass
- hangs / timeouts / severe regressions that effectively break the app

You may inspect surrounding code and related call sites beyond the primary review scope when needed to validate behavior.

## ✅ Pre-Commit Reality: Untracked Files Are Fine
This review is often a **pre-commit/pre-tracking** check. New or moved files may appear **untracked** and that is expected.

- **Do not** mark an issue Critical/High *only because* a referenced file/class is currently untracked.
- Assume untracked new files will be committed/deployed together **unless there is concrete evidence otherwise**.
- If there is a true risk, report it as a **conditional deployment note** (“if X isn’t shipped with this change, it will break”), not as a P1 by itself.

## Review Modes
This file supports two review modes.

### Mode A — Iterative local review
Use this when reviewing:
- unstaged modified files
- untracked files
- a mutable working tree

In this mode, use the **git index (staging area)** as review memory.

### Mode B — Commit review
Use this when reviewing:
- a specific commit
- an immutable diff
- a committed snapshot

In this mode, **do not** stage files. Review is read-only.

## Iterative Review Mode (Index-Ratchet)
When reviewing a mutable working tree, use the **git index (staging area)** as the review memory.

### Purpose
The goal is to **narrow the primary review surface over successive passes** without losing the ability to validate integration boundaries.

Files that have already been reviewed and found clean should remain staged as the cleared baseline.
Files still being fixed should remain unstaged/untracked and stay in active review scope.

### Branch / Commit Safety
- Stay on the current branch.
- **Do not** create commits.
- **Do not** switch branches.
- **Do not** reset, restore, or unstage previously staged files.
- **Do not** use broad staging commands like `git add .`, `git add -A`, or `git add -u`.
- Only stage specific files that were reviewed and found clean in the current pass.

This keeps everything consistent so the main agent can later commit and push to `main`/`master` normally.

## Never Execute Project Commands
This is a **static review only**.

Do **not** run:
- tests
- linters
- formatters
- type-checkers
- build steps
- migrations
- seeders
- package managers
- project scripts
- framework CLIs
- docker / compose commands
- service restarts
- any command intended to validate the code by execution

Do **not** attempt to “quick check” by running the repo.
Do **not** mention failed attempts to run tests.
Do **not** rely on test execution for conclusions.

If a suggested quick check is useful, provide it as a **recommended manual repro/test step only**.

## Scope: What to Check
Prioritize issues that would realistically show up in production.

When reviewing, actively search for:
- callers/handlers that now pass different types/shape
- code paths that now become reachable (or unreachable)
- error handling that was removed or invalidated
- config/env/feature-flag interactions that could flip behavior
- backward compatibility with persisted data (DB rows, cache entries, local storage)
- contract changes (API, schema, events, queues) that ripple outward

## Primary Review Scope

### In iterative local review
Treat the following as the **primary review scope**:
- **unstaged modified files**
- **untracked files**

These are the files currently under active remediation.

### In commit review
Treat the following as the **primary review scope**:
- files changed by the reviewed commit/diff

### Practical interpretation
- Use the working tree version as the source of truth for any file with unstaged edits.
- If a file is both staged and unstaged, treat it as **active** and review the unstaged version.
- Previously staged files are considered **baseline-cleared** unless they were modified again.

## Excluded Control Files
Treat these as review-control/runtime-plumbing files and **do not auto-stage them** unless the user explicitly asked for them to be part of the reviewed change set:
- `AGENTS.override.md`
- temporary symlinks created by shell wrappers
- transient files created only to inject review instructions

You may read them if needed to understand the review environment, but they are not feature files.

## Secondary Validation Scope
You may inspect any related files outside the primary review scope when needed to validate:
- callers / callees
- shared types / schemas / DTOs
- config/env/feature flags
- migrations / persisted state
- queue/event contracts
- schedulers / jobs / watchdogs / retries / recovery paths
- tests that encode critical behavior

Use these files for reasoning whenever needed.

## Reporting Boundary
During iterative review:
- Focus findings on the current **unstaged/untracked** changes and the breakage they introduce.
- Do **not** reopen previously staged/baseline-cleared files unless:
  1. they were modified again and are now active scope, or
  2. the current active changes plausibly break them through a contract, state, or integration boundary.

During commit review:
- Focus findings on the reviewed commit/diff and the breakage it introduces.
- You may inspect unchanged files for context, but do **not** turn the review into a repo-wide audit unrelated to the reviewed diff.

If an untouched file is only relevant as context, use it for reasoning but do **not** report it as the defect location unless the breakage truly lives there.

## 🛑 Strictly Ignore (Do Not Report)
Do **not** report:
- formatting, whitespace, lint/style, naming
- docs/comments/docstrings
- “best practices” that don’t prevent breakage
- micro-optimizations or refactor preferences
- minor nits that don’t plausibly cause a crash, data loss, or auth/security failure

## 🚨 Report Only High-Severity Findings
Report only issues that could cause **application breakage or unintended outcomes**, including:

1. **Crashers & Exception Paths**
   - null/None/undefined access, key errors, out-of-range
   - incorrect error handling, uncaught exceptions
   - invalid assumptions about input/state

2. **Behavioral Breakage / Wrong Results**
   - logic regressions in critical flows
   - incorrect state transitions, invariants violated
   - unintended side effects (writes, deletes, duplicated work)

3. **Integration / Contract Breaks**
   - API request/response shape mismatches
   - DB schema/data migration mismatches
   - serialization/deserialization changes
   - event/message formats, queue consumers/producers
   - versioning / backward compatibility risks

4. **Concurrency / Resource Safety**
   - deadlocks, races, double-writes, lost updates
   - leaks: file handles, sockets, DB connections, goroutines/tasks
   - cancellation/timeout behavior that can wedge the app

5. **Security / Auth / Data Safety**
   - authz/authn bypass, permission regressions
   - secrets/credentials exposure
   - injection risks introduced in critical paths
   - data corruption or irrecoverable destructive operations

6. **Hang / Timeout / “App Feels Down” Failures**
   - infinite loops, unbounded retries
   - blocking calls on hot paths
   - N+1 or accidental quadratic work that can timeout

## Review Method (How to Think)
For each affected feature/flow:
- Identify entry points (routes, handlers, jobs, CLI, consumers).
- Trace “happy path” + key failure paths.
- Validate assumptions at boundaries: types, nullability, ordering, idempotency.
- Confirm fallbacks, retries, and timeouts won’t cause storms or wedges.
- If a change modifies a shared type/contract, search for all usages impacted.

In iterative mode:
- Start with the current unstaged/untracked files.
- Expand outward only as needed to validate affected boundaries.

In commit mode:
- Start with the files in the reviewed commit/diff.
- Expand outward only as needed to validate affected boundaries.

Prefer minimal, concrete runtime breakage scenarios over abstract concerns.

## Staging Behavior
### In iterative local review
After completing the audit for the current pass:

- If a file in the **primary review scope** has **no Critical/High issues**, stage it with:
  - `git add -- <file>`
- Do **not** stage any file that still has a reported issue.
- Do **not** stage files that were only read for context and were not part of the primary review scope.
- Do **not** auto-stage excluded control/runtime-plumbing files such as `AGENTS.override.md`.

### In commit review
- **Do not stage files.**
- Review is read-only.

### Re-entry rule
If a previously staged file is edited later, it automatically re-enters review scope because it becomes unstaged again. That is expected.

## Output Rules
A clean result means:
- no Critical/High issues were found in the current primary review scope, and
- no breakage was found in related boundaries affected by those changes.

If no high-severity issues are found, the **first line** must be exactly:
**No critical application-breaking issues found.**

If you find issues, for each one provide:
1. **Severity:** (Critical / High)
2. **Location:** file + line(s)
3. **Breakage scenario:** the concrete runtime path that fails
4. **Why it fails:** the specific invariant/assumption violated
5. **Fix:** an explicit patch or code snippet (minimal change preferred)
6. **Suggested quick check:** a targeted manual test case / repro step (1–2 lines)

Keep it concise and actionable. No filler.

## Staging Verification
At the end of every review run, explicitly confirm whether staging commands were actually executed.

Use exactly one of these lines:
- `Staging commands executed successfully.`
- `No staging commands were executed.`
- `Staging was requested by instructions but was not performed in this review environment.`

Do not omit this line.

## End-of-Run Review Summary (Always Required)
At the end of every review run, always append a final summary block, even if issues were found.

Use this exact heading:

**Review scope summary**

The summary must include:

1. **Primary scope reviewed**
   - total count of primary-scope files reviewed

2. **Files staged in this pass**
   - explicit list of file paths staged with `git add -- <file>`
   - if none were staged, say exactly:
     `Files staged in this pass: none`

3. **Files left unstaged due to reported issues**
   - explicit list of file paths that remain unstaged because this review found a Critical/High issue affecting them
   - in commit review, say `none`

4. **Files left unstaged for another reason**
   - explicit list of any primary-scope files that were not staged for reasons other than a reported issue
   - include a short reason for each
   - in commit review, the default reason is read-only review mode

5. **Context-only files inspected**
   - optional list of files read only for validation/context and not eligible for staging in this pass

Use this format:

**Review scope summary**
- Primary-scope files reviewed: <number>
- Files staged in this pass:
  - <path>
  - <path>
- Files left unstaged due to reported issues:
  - <path>
  - <path>
- Files left unstaged for another reason:
  - <path> — <reason>
- Context-only files inspected:
  - <path>
  - <path>

If there are no files in a section, say `none`.

## Required Final Marker
At the very end of every review output, print exactly these lines:

Review policy: iterative-index-ratchet
Review instruction version: CRBA-v5.0-2026-03-07

## Review Discipline
- Do not weaken the audit just because this is an iterative pass.
- Do not re-litigate already-cleared staged files unless current active changes affect them.
- Do not treat the absence of new findings in active scope as proof that the entire repository is clean forever; it only means the current pass is clean.
- The final commit/push can still be done normally by the main agent once all active changes have been cleared and staged.