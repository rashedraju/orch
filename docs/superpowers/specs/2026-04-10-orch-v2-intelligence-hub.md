# Orch v2 — Intelligence Hub + Universal Routing

**Date:** 2026-04-10
**Status:** Approved

---

## Context

Orch currently acts as a tactical task coach: single-session complexity classification, step-by-step planning, fuzzy prompt detection, and token health monitoring. It has no memory between sessions — each session starts from scratch, requiring the agent to re-establish project context, re-scan the codebase, and re-discover conventions. This wastes tokens, increases human involvement, and produces lower-quality output because the agent lacks accumulated project knowledge.

This spec adds three coordinated subsystems that give Orch persistent memory and make it the universal intelligence layer for every session:

1. **Intelligence Hub** — Three markdown files in `.claude/orch/` that accumulate project knowledge, execution history, and task state across sessions
2. **Enhanced Initialization** — A new `init_brain.py` script that seeds the brain on first run and auto-refreshes when the codebase changes
3. **Universal Routing** — An enhanced `UserPromptSubmit` hook that injects project context and the Orch complexity gate instruction into every prompt, so users never need to manually invoke `/orch`

---

## What Changes

| File | Action |
|------|--------|
| `skills/orch/scripts/init_brain.py` | Create — codebase scanner, writes brain.md skeleton |
| `hooks/session-start.py` | Modify — add brain init, git change detection, tool recommendation |
| `hooks/prompt-submit.py` | Modify — add project context injection + complexity gate instruction |
| `skills/orch/SKILL.md` | Modify — tasks.md management, install flow, refresh brain command |
| `skills/orch-planner/SKILL.md` | Modify — brain.md + history.md updates after task steps |

Nothing else changes. The existing `init_setup.py`, `discover_tools.py`, `install_plugin.py`, hooks structure, and skill format are all preserved.

---

## Subsystem A: Intelligence Hub

### File Structure

Three files live at `.claude/orch/` **in the user's project root** (not in the Orch plugin directory):

```
<project-root>/
└── .claude/
    └── orch/
        ├── brain.md     ← Project brain: decisions, patterns, conventions, architecture
        ├── history.md   ← Execution log: one entry per completed task (append-only)
        └── tasks.md     ← Task registry: active + recently completed tasks
```

### `brain.md` — Project Brain

**Created by:** `init_brain.py` (skeleton with auto-filled structural sections)
**Enriched by:** `orch-planner` skill (appends discoveries after each completed step)
**Read by:** `session-start.py` hook (summary injection), `prompt-submit.py` hook (context + routing), `orch` skill (conventions + prior decisions)

Format:

```markdown
# Project Brain
<!-- git_head: <sha> -->
<!-- last_scan: <ISO date> -->

## Project Summary
<name, one-line description, primary language>

## Tech Stack
<detected frameworks, languages, tools>

## Key Files
<entry points, config files, key modules — auto-detected>

## Directory Map
<top-2-level structure, auto-generated>

## Architecture
<!-- Filled in by orch-planner as tasks complete -->

## Conventions
<!-- Filled in by orch-planner as patterns are discovered -->

## Decisions Log
<!-- Appended by orch-planner: date, decision, rationale -->

## Open Questions
<!-- Added manually or by orch skill when uncertainty is noted -->

## Recommended Skills
<!-- Filled by init_brain.py based on detected stack -->
```

**Key invariants:**
- The `<!-- git_head: ... -->` comment is updated by every structural scan
- Knowledge sections (Architecture, Conventions, Decisions Log) are **never overwritten** by structural re-scans — only appended to
- `brain.md` is never deleted; it accumulates knowledge indefinitely

### `history.md` — Execution Log

**Created/updated by:** `orch-planner` skill after every task completion
**Append-only** — never overwritten

Format:

```markdown
# Execution History

## 2026-04-10 — Add user authentication
- Steps: 4 completed (schema, model, routes, tests)
- Outcome: Auth system with JWT tokens, bcrypt passwords
- Skills used: superpowers, context7
- Lessons: User table needs soft-delete column; migrations run before seeding

## 2026-04-09 — Fix pagination bug
...
```

### `tasks.md` — Task Registry

**Created/updated by:** `orch` skill (on new task start) + `orch-planner` skill (on task complete)

Format:

```markdown
# Task Registry

## Active Tasks
| Task | Started | Status | Plan | Blockers |
|------|---------|--------|------|----------|
| Add payment integration | 2026-04-10 | In progress | .claude/session.md | Stripe API key needed |

## Recently Completed (last 5)
| Task | Completed | Outcome |
|------|-----------|---------|
| Fix pagination bug | 2026-04-09 | Resolved — off-by-one in cursor calculation |
```

---

## Subsystem B: Enhanced Initialization

### New: `skills/orch/scripts/init_brain.py`

A fast Python script (stdlib only, no external packages, no LLM calls) that creates or updates `brain.md`.

**What it scans:**
- Top-2-level directory structure (excluding `.git`, `node_modules`, `vendor`, `.venv`, `dist`, `build`, `__pycache__`)
- Key files: `package.json`, `composer.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`, `README.md`, common entry points (`main.py`, `index.js`, `app.py`, `server.js`, `cmd/main.go`, `src/main.rs`)
- File type distribution (counts by extension)
- Test directory detection (`test/`, `tests/`, `__tests__/`, `spec/`)
- Config files: `.env.example`, `docker-compose.yml`, `Dockerfile`, `.github/workflows/`
- Tech stack inference (same logic as `init_setup.py`)

**Behavior:**
- If `brain.md` does not exist: creates full skeleton, fills structural sections, leaves knowledge sections as placeholders
- If `brain.md` exists and git HEAD changed: updates only the structural sections (Project Summary, Tech Stack, Key Files, Directory Map, Recommended Skills); all other sections left intact
- If `brain.md` exists and git HEAD unchanged: exits immediately (no-op)
- `--force` flag: always re-runs the structural scan regardless of HEAD state

**Output:** Updates `brain.md` with the stored `git_head` comment set to current HEAD.

**CLI:**
```bash
python3 init_brain.py [--cwd /path/to/project] [--force]
```

### Enhanced: `hooks/session-start.py`

Current behavior (unchanged): runs `init_setup.py` if stale → injects setup summary.

**New step 1: Brain initialization / change detection**

After `init_setup.py`:

```
brain_md = project_root / ".claude/orch/brain.md"

if not brain_md.exists():
    run init_brain.py  # first run — create skeleton
elif git_head_changed(brain_md):
    run init_brain.py  # auto-refresh structural sections
# else: brain is current, skip scan entirely
```

Git HEAD comparison: reads `<!-- git_head: ... -->` from `brain.md`, compares to `git rev-parse HEAD`.

**New step 2: Tool gap recommendation**

Runs `discover_tools.py --json`, filters for status `not_installed` with priority `required` or `recommended`. If any found:

Injects: `[Orch] Recommended tools not installed: superpowers, context7. Say "install recommended tools" to proceed.`

**New step 3: Brain summary injection**

Reads `brain.md` and injects a compact summary into context:
- Project name + one-line description (from Project Summary)
- Tech stack line
- Active task count (from `tasks.md` if exists)
- Up to 3 recent Decisions Log entries

This replaces the need for Claude to scan the project at session start.

---

## Subsystem C: Universal Routing

### Enhanced: `hooks/prompt-submit.py`

Current behavior (unchanged): fuzzy detection, resume reminder, skill gap notice.

**New additions** (only run when `.claude/orch/brain.md` exists):

1. Read `brain.md`: extract project name, stack, up to 3 context bullets from Decisions/Conventions sections
2. Read `tasks.md` (if exists): count active tasks
3. Build and prepend a routing context block:

```
[ORCH] Project: <name> | Stack: <stack> | Active tasks: <N>
Context: <bullet 1> | <bullet 2> | <bullet 3>

For any implementation task, classify before responding:
- Quick (≤2 steps, single file): answer directly
- Standard/Complex: create/update .claude/session.md, route to appropriate skills
Consult .claude/orch/brain.md for project conventions and prior decisions.
```

This block is injected **on every prompt** when the brain exists — making Orch's complexity gate universal without requiring the user to invoke `/orch`.

### Enhanced: `skills/orch/SKILL.md`

Three new behaviors added to the orch skill:

**On new Standard/Complex task:**
Before writing `session.md`, read `brain.md` (conventions, decisions log). Check `tasks.md` for active tasks that might conflict or relate. Write new entry to `tasks.md` Active Tasks table.

**On "install recommended tools":**
Read `discover_tools.py` output (or re-run it). For each missing required/recommended tool, call `install_plugin.py --plugin <name> --marketplace claude-plugins-official`. Report what was installed.

**On "refresh brain":**
Run `init_brain.py --force`. Report which sections were updated.

### Enhanced: `skills/orch-planner/SKILL.md`

Two new behaviors added after the existing replan procedure:

**After each [DONE] step:**
If the step created new files, discovered naming patterns, or made architectural decisions: append 1-3 bullets to the relevant sections of `brain.md` (Conventions, Architecture, or Decisions Log). Keep additions concise.

**After final task step (session end sequence):**
1. Append entry to `history.md`: task name, date, steps completed, outcome, key lessons
2. Update `tasks.md`: move task from Active to Completed (keep last 5 completed)

---

## Install Flow Impact

When a user installs Orch and starts their first session in a project:

1. `SessionStart` hook fires
2. `init_setup.py` runs (env scan → `setup.md`) — existing behavior
3. `init_brain.py` runs (codebase scan → `.claude/orch/brain.md`) — new
4. `discover_tools.py` runs → if gaps, injects recommendation — new
5. Hook injects: setup summary + brain summary
6. First prompt triggers routing context injection from `prompt-submit.py`
7. User gets full Orch intelligence without invoking `/orch`

On subsequent sessions: step 3 is skipped if no git changes; brain summary is injected immediately from existing file.

---

## Out of Scope

- LLM-based codebase analysis (brain.md knowledge sections are filled by Claude via skills, not by scripts)
- Multi-user or team-shared brains (brain.md is local to the developer's project root)
- Automatic MCP installation (MCPs require auth setup — only plugins are auto-installable)
- Cross-project brain sharing or templates

---

## Verification

After implementing:

1. Fresh project: start a Claude Code session → `.claude/orch/brain.md` created with directory map + detected stack
2. Pull new commits: start next session → brain structural sections refreshed automatically, knowledge sections intact
3. Submit any task prompt (no `/orch` invoked): hook injects `[ORCH]` context block + complexity gate instruction
4. Complete a task via `orch-planner`: `history.md` appended, `tasks.md` updated
5. Start new session in same project: brain summary injected at session start, no codebase re-scanning
6. Run `discover_tools.py` in a project missing `superpowers`: session-start injects install recommendation
