# Doc Recreation Process v4.0

## Trigger

README.md, `ops/manifest.yaml`, or any top-level `ops/*.md` file with `DATETIME of last agent review` older than 30 days, or missing entirely.
Also trigger if any nested doc exists under `ops/**` (`*.md` or `*.yaml` below top level).

## Why Rebuild vs Patch

Patching stale docs creates inconsistent Frankenstein files. Rebuilding from scratch using templates ensures docs match current code with no legacy cruft.

## Documentation Philosophy

**README** = HOW to deploy (for humans, NOT ingested by agent)
- First-time setup, installation, configuration
- Troubleshooting procedures
- Can be detailed (~175 lines max with section budgets)

**ops/manifest.yaml** = startup agent map (ingested at startup)
- Runtime topology, entrypoints, services, env file paths, default test commands
- Factual and compact (target ~80 lines)

**top-level ops/*.md** = focused runtime notes (opened on demand)
- Only non-derivable operational knowledge
- Read-only checks, optional operator actions, and gotchas
- Prefer a few merged area docs over many feature docs

## Documentation Structure

```
README.md              <- deployment guide for humans
ops/
  manifest.yaml        <- startup-ingested agent map
  TESTING.md           <- startup-ingested test commands if needed
  runtime.md           <- optional focused runtime note
  integrations.md      <- optional focused runtime note
```

**Rules:**
- ONE README.md at project root only
- NO README.md files in subfolders
- `ops/manifest.yaml` is the only required ops doc
- Keep top-level ops docs lean. Default target is `manifest.yaml`, `TESTING.md`, and 0 to 3 runtime notes
- No nested docs under `ops/**`. Subfolders may exist only for non-doc assets/config/scripts such as `systemd/`, `probes/`, or templates consumed by the app.
- Vendor/node_modules/dist/build/venv excluded from all operations
- If more than 4 top-level ops docs are proposed, justify each extra doc in one sentence before keeping it

## Process

### 1. Context Gathering
- Read existing README.md, `ops/manifest.yaml`, and all top-level ops/*.md files
- Detect and inventory any forbidden nested docs under `ops/**`
- Note what topics they covered
- Identify project-specific terminology

### 2. Codebase Crawl

| Target | What to Extract |
|--------|-----------------|
| `package.json` / `composer.json` | Stack, scripts |
| `.nvmrc` / `.tool-versions` | Runtime versions |
| `.env.example` | Required config vars |
| Service configs (systemd, supervisor) | Service management |
| `src/` or `app/` | Component structure |
| `database/migrations/` | Schema context |
| `tests/` | Test framework, complexity |

### 2.1 Source-of-Truth Cross-Check
- For every named service/timer/entrypoint in the new docs, confirm it exists in repo source or deployment files.
- For every major runtime subsystem visible in the source of truth, decide whether it belongs in:
  - `ops/manifest.yaml`
  - a top-level runtime note
  - README only
  - nowhere (because it is low-value or obvious)
- For every command added to docs, classify it as:
  - read-only check
  - operator action
  - setup/deploy procedure
- Do not place a mutating command under a read-only section.

### 3. Delete and Rebuild Core Documentation
```bash
rm -f README.md
find ops -mindepth 1 -maxdepth 1 -type f \( -name "*.md" -o -name "manifest.yaml" \) -delete
find ops -mindepth 2 -type f \( -name "*.md" -o -name "*.yaml" \) -delete
```

Do not delete `follow_up.md` as part of doc recreation unless the user explicitly asks.

### 4. Recreate README
Use `AGENTS_templates/reed_me.md` template.

Include sections as needed:
- Title + Purpose (required)
- Stack (required)
- Quick Start (required)
- First-Time Server Setup (if applicable)
- Configuration (if applicable)
- Common Operations (if applicable)
- Troubleshooting (if applicable)

**Preserve operational knowledge** from old README - setup procedures, troubleshooting solutions, config examples. This content belongs here, not in ops/.

### 5. Recreate ops/ Docs
Use `AGENTS_templates/ops_manifest.yaml` for the startup manifest.

Populate the manifest from source of truth:
- entrypoints from `package.json`, framework boot files, cron runners, systemd/supervisor configs
- env file paths and secret locations
- default health checks and test commands
- external systems and durable state paths
- high-signal gotchas only
- concrete unit names only, never globs
- read-only checks only in health/post-deploy sections

Create top-level runtime notes only when there is non-derivable operational knowledge worth preserving. Use `AGENTS_templates/ops_runtime_note.md`.

Good candidates:

| If You Find | Create |
|-------------|--------|
| Service management with non-obvious restart/log rules | `ops/runtime.md` or `ops/services.md` |
| External contracts or side effects that are easy to break | `ops/integrations.md` |
| Database/runtime state with operational caveats | `ops/db.md` |
| Complex test setup or area overrides | `ops/TESTING.md` |

Do not create one doc per feature unless the runtime model genuinely requires it.
Do not recreate nested docs under `ops/**`.
Merge overlapping notes aggressively.
Delete any note that cannot justify its existence with a real `Open When` plus a real `Gotcha`.

### 6. Verify
- [ ] README has all operational knowledge from original
- [ ] README respects section budgets
- [ ] `ops/manifest.yaml` is concise and factual
- [ ] Each runtime note is worth its startup/discovery cost
- [ ] All file paths and commands in ops docs exist
- [ ] Every named service/timer/entrypoint was cross-checked against source of truth
- [ ] Every read-only section contains read-only commands only
- [ ] No doc exists only to list file paths
- [ ] No two docs substantially overlap without a clear reason
- [ ] No nested docs remain under `ops/**`
- [ ] All timestamps updated

## Acceptance Rubric

A recreated doc set is acceptable only if all of the following are true:
- An agent can understand the runtime model from `ops/manifest.yaml` in under 60 seconds.
- README contains the human deployment/setup knowledge removed from old ops docs.
- Runtime notes answer distinct questions and prevent likely mistakes.
- Commands in docs are clearly separated into read-only checks versus operator actions.
- The doc set is smaller and clearer than what it replaced, not just different.

## Content Placement Guide

| Content Type | Goes In |
|--------------|---------|
| How to install dependencies | README |
| Service config examples | README |
| Crontab entries | README |
| System tweaks (sysctl, caps) | README |
| Troubleshooting procedures | README |
| Startup runtime map | ops/manifest.yaml |
| Agent commands and gotchas | top-level ops/*.md |
| Design decisions that are easy to misread | top-level ops/*.md |
| Setup, install, deploy, migration procedures | README |

## What NOT to Do

- Don't lose operational knowledge from old README
- Don't put setup procedures in ops/ docs
- Don't split runtime notes by feature when one area doc would do
- Don't create low-value file-inventory docs
- Don't create ops/ docs for components that don't exist
- Don't leave nested docs under `ops/**`
- Don't put mutating commands in read-only sections
- Don't keep a doc that cannot justify why it exists
- Don't include marketing copy or badges
- Don't leave placeholder sections