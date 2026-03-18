# Ops Doc Testing Template v3.0

## Why This Matters

`ops/TESTING.md` is one of the default startup-ingested docs. It should tell the agent the fastest safe verification path for the repo, plus any area-specific overrides that are worth knowing before editing.

**Critical Rule:** Tests are run at the end of every new feature. This rule persists through all ops/ audits and recreations.

## Template

```markdown
# Testing

DATETIME of last agent review: DD MMM YYYY HH:MM (Europe/London)

## Purpose
One sentence describing the repo's testing surface.

## Fast Path
Agent-runnable commands. Keep execution time minimal (<30s preferred).
- `npm test` - default quick verification
- `npm run build` - compile/type smoke

## Area Overrides
- `path/or/area` -> `exact command` - when to use this instead of the fast path
- `path/or/area` -> `exact command` - what it validates

## Read-Only Runtime Checks
- `exact command` - prod-safe smoke or health query
- Delete section if empty

## Key Test Locations
- `tests/` - primary suite
- `path/to/special-tests` - optional area-specific tests
- Delete lines that do not apply

## Known Gaps
- Only real gaps or caveats
- Delete section if empty

## Agent Testing Protocol
**MANDATORY:** Run relevant tests after every new feature or change; fix failures immediately.

## Notes
- Optional critical context only
- Delete if empty
```

## Forbidden Content

- Deploy or restart procedures
- DB migrations or other write-heavy operator actions
- Vague commands such as `run relevant tests`
- Test lists with no guidance on when to use them

## Validation Rules

- `Fast Path` should be enough for most code changes
- Every override must map a path or subsystem to an exact command
- `Read-Only Runtime Checks` must be safe on production hosts
- Keep this doc lean enough to scan in under 60 seconds

---

## Principles

1. **Startup useful** - this doc is ingested early, so keep it high-signal
2. **Speed over completeness** - tests must run fast enough for agent iteration
3. **Explicit commands** - no guessing what to run
4. **Mandatory post-feature testing** - non-negotiable, persists through recreation
5. **60 lines max** - `ops/TESTING.md` should be lean