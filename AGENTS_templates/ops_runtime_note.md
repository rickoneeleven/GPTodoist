# Runtime Note Template v2.0

## Purpose

Focused runtime notes are opened on demand, not at startup. They should exist only when the repo has operational knowledge that is expensive to rediscover from code.

## Constraints

- Must live at top-level `ops/` only
- Target 20 to 25 lines, hard max 35
- Prefer merged area docs over one doc per feature
- No setup guides or long explanations
- File paths are optional and should appear only when operationally important
- If the doc cannot justify `Open When` and at least one real `Gotcha`, it should not exist

## Template

```markdown
# [Area]

DATETIME of last agent review: DD MMM YYYY HH:MM (Europe/London)

## Purpose
One sentence describing the runtime area.

## Open When
- Touching:
- Investigating:
- Deploying:

## Runtime Facts
- Service / timer / supervisor:
- Env file / secret path:
- External dependency:
- State / log / queue path:

## Read-Only Checks
```bash
exact command
exact command
```

## Operator Actions
```bash
exact command
```
Delete section if empty.

## Gotchas
- Only non-derivable facts that prevent bad decisions
- Delete section if empty
```

## Forbidden Content

- File inventories or code tours
- Setup instructions that belong in README
- Architecture essays
- Commands that mutate state under `Read-Only Checks`
- A note that only repeats the manifest

## Validation Rules

- `Open When` must name real trigger conditions
- `Read-Only Checks` must be read-only
- `Operator Actions` must be clearly mutating and used only when genuinely useful
- Overlapping notes should be merged
- If this note does not save a future agent from a real mistake, delete it

## Good Uses

- systemd or supervisor behavior that is not obvious from code
- external integration contracts with failure modes
- runtime state files, queues, or lock behavior
- DB-backed runtime toggles or caches that are easy to forget

## Bad Uses

- file inventories
- architecture essays
- setup instructions that belong in README