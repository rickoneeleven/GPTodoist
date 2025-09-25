# AGENTS.md v1

The following guidelines govern how agents work in this repository. They apply to all code and documentation within this directory tree.

## First Response Protocol (Mandatory)

- On the very first interaction of every session, do these in order before addressing the user request:
  - Fetch the canonical AGENTS.md from the remote RAW URL and overwrite the local AGENTS.md.
  - Announce exactly: "Bootstrapping: fetched latest AGENTS.md and scanning README.md files. I will provide a project overview and any README updates before proceeding with your request."
  - Mandatory documentation integrity check: enumerate project README files only (exclude vendor and third-party directories such as .git, node_modules, vendor, third_party, venv, env, dist, build, __pycache__). Use `rg --files` with include/exclude globs to list README.md/readme.md, and flag any file missing the required header or older than 31 days.
  - For every README flagged as missing a header or older than one month, you will run the README Validation Procedure before touching the primary task. Do not skip. Do not timestamp without validation.
  - After validation, post a concise project overview and list of README files updated, then proceed with the initial user task.

## README Validation Procedure (Mandatory)

- Ingest the README fully. Scanning is unacceptable. You are responsible for understanding all claims.
- Identify concrete claims: functions, classes, modules, commands, endpoints, config files, environment variables, paths, and build or run steps.
- Validate each claim against the live codebase: open the referenced files, locate the named symbols with `rg`, confirm signatures, parameters and behaviour. If the README describes commands or scripts, confirm paths and entry points exist in this repository.
- Correct the README: update inaccurate or stale statements, fix renamed symbols, remove references to deleted or deprecated components. Keep descriptions concise and technically precise.
- Only after the README is correct, set the header `DATETIME of last agent review: <UK formatted datetime>`. The timestamp is your attestation that the documentation is true and current.

## Auto-Update From Remote

- At session start, always fetch the canonical instructions from this RAW URL and replace the local file:
  - https://notes.pinescore.com/note/note_683df4954cc0f4.04393849.raw

## Required bootstrap snippet (self-contained)

Run these commands to announce bootstrap, enumerate READMEs with `rg`, and handle header updates without external scripts.

```
# 1) Announce exactly as required
printf 'Bootstrapping: fetched latest AGENTS.md and scanning README.md files. I will provide a project overview and any README updates before proceeding with your request.\n'

# 2) Detect project README files needing validation (prints paths)
#    - Finds README.md or readme.md, excluding vendor/third-party dirs
rg --files \
  -g '!**/.git/**' -g '!**/node_modules/**' -g '!**/vendor/**' -g '!**/third_party/**' \
  -g '!**/venv/**' -g '!**/env/**' -g '!**/dist/**' -g '!**/build/**' -g '!**/__pycache__/**' \
  -g 'README.md' -g 'readme.md' | while read -r f; do \
    header_missing=1; rg -q '^DATETIME of last agent review:' "$f" && header_missing=0; \
    cutoff=$(date -u -d '31 days ago' +%s); mtime=$(stat -c %Y "$f"); \
    if [ $header_missing -eq 1 ] || [ "$mtime" -lt "$cutoff" ]; then echo "$f"; fi; \
  done

# 3) After validation, set or update the header to current UK datetime
#    Example for a single file $f after you have validated its content:
UKDT=$(date -u '+%d/%m/%Y %H:%M GMT'); \
if rg -q '^DATETIME of last agent review:' "$f"; then \
  sed -i "s/^DATETIME of last agent review:.*/DATETIME of last agent review: ${UKDT}/" "$f"; \
else \
  printf 'DATETIME of last agent review: %s\n\n' "$UKDT" | cat - "$f" > "$f.tmp" && mv "$f.tmp" "$f"; \
fi
```

## Core Development Principles

Adherence to these principles is mandatory for all code modifications:

- Simplicity, Clarity and Conciseness: Write only necessary code.
- Self-Documenting Code: Use clear, descriptive naming and structure so intent is obvious without comments.
- Minimal Comments: Avoid comments. If you see them, remove them. The code itself must be the single source of truth.
- Modularity and Cohesion: Prefer highly cohesive components with clear responsibilities and loose coupling.
- DRY (Do not Repeat Yourself): Extract and reuse common logic patterns.
- Dependency Management: Prefer constructor injection. Avoid direct creation of complex services within consumers.
- Maximum 400 lines per file: Keep files modular and focused. If a file exceeds 400 lines during your work, refactor it by breaking down the logic accordingly. Do not append to a file over 400 lines without the user's express permission.
- Verify Line Counts: After completing your tasks, run a command like `find . -name "*.py" -type f -print0 | xargs -0 wc -l` to check the line counts of files you modified. If any exceed 400 lines, refactor them.
- Troubleshooting: you can either ask the user to check console debug messages, guide them, or use playwright mcp to browse the site yourself. If playwright mcp server is not installed and you feel that is the best way to proceed, advise the user and focus on working with the user to get playwright mcp server setup. They have instructions.

## Shell and File IO Norms

- Search code quickly and accurately; prefer `rg` for search and `rg --files` for discovery. If `rg` is unavailable, use an equivalent.
- Read files in chunks with a maximum of 250 lines per chunk.
- Use `apply_patch` semantics when editing files. Keep changes minimal, focused, and consistent with the existing codebase.

## Communication Protocol

- Be direct and fact based: do not be agreeable by default; push back and help correct the user when appropriate.
- Right over right now: do not rush or blindly follow instructions. Aim to get it right rather than forcing completion. Pause, prompt, discuss, then execute when the approach is correct.
- Keep preamble messages concise and grouped when running tools.

## Plain ASCII Output

- Use ASCII-only punctuation in all user-visible text.
- Avoid non-breaking hyphens, en/em dashes, and curly quotes.
- Prefer simple quotes (" ") and hyphens (-); avoid typographic variants.
