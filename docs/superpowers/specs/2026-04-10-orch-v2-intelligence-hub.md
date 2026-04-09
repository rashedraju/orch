# Orch v2 — Intelligence Hub + Universal Routing

**Date:** 2026-04-10
**Status:** Approved (rev 2 — 2026-04-10)

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
| `skills/orch/scripts/init_brain.py` | Create — structural codebase scanner, writes brain.md skeleton |
| `hooks/session-start.py` | Modify — brain init, git change detection, LLM analysis trigger, setup gaps |
| `hooks/prompt-submit.py` | Modify — project context injection + complexity gate instruction |
| `skills/orch/SKILL.md` | Modify — LLM analysis phase, interactive setup (plugins + MCPs + auth), tasks.md |
| `skills/orch-planner/SKILL.md` | Modify — brain.md + history.md updates after task steps |

Nothing else changes. The existing `init_setup.py`, `discover_tools.py`, `install_plugin.py`, hooks structure, and skill format are all preserved.

---

## Subsystem A: Intelligence Hub

### File Structure

Four files live at `.claude/orch/` **in the user's project root** (not in the Orch plugin directory):

```
<project-root>/
└── .claude/
    └── orch/
        ├── brain.md          ← Project brain: decisions, patterns, conventions, architecture
        ├── history.md        ← Execution log: one entry per completed task (append-only)
        ├── tasks.md          ← Task registry: active + recently completed tasks
        └── pending_setup.md  ← Deferred setup items (declined plugins/MCPs, pending auth)
```

### `brain.md` — Project Brain

**Created by:** `init_brain.py` (structural skeleton) + `orch` skill (LLM analysis phase, first session only)
**Enriched by:** `orch-planner` skill (appends discoveries after each completed step)
**Read by:** `session-start.py` hook (summary injection), `prompt-submit.py` hook (context + routing), `orch` skill (conventions + prior decisions)

Format:

```markdown
# Project Brain
<!-- git_head: <sha> -->
<!-- last_scan: <ISO date> -->
<!-- llm_analysis: pending | complete -->

## Project Summary
<name, one-line description, primary language>

## Tech Stack
<detected frameworks, languages, tools>

## Key Files
<entry points, config files, key modules — auto-detected>

## Directory Map
<top-2-level structure, auto-generated>

## Architecture
<!-- LLM-populated on first session: component relationships, data flow, key patterns -->

## Conventions
<!-- LLM-populated on first session: naming, file organization, test style, code style -->

## Decisions Log
<!-- Appended by orch-planner: date, decision, rationale -->

## Open Questions
<!-- Added manually or by orch skill when uncertainty is noted -->

## Recommended Skills
<!-- Filled by init_brain.py based on detected stack -->
```

**Key invariants:**
- The `<!-- git_head: ... -->` comment is updated by every structural scan
- The `<!-- llm_analysis: ... -->` flag tracks whether LLM analysis has run (pending → complete, once)
- Structural sections (Project Summary through Directory Map) are overwritten by `init_brain.py` on git changes
- Knowledge sections (Architecture, Conventions, Decisions Log) are **never overwritten** — only appended to
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

### `pending_setup.md` — Deferred Setup Items

**Created/updated by:** `orch` skill when user declines setup or auth is incomplete
**Read by:** `session-start.py` hook + `orch` skill on invocation

Format:

```markdown
# Pending Setup

## Pending Installation
| Item | Type | Priority | Declined At | Notes |
|------|------|----------|-------------|-------|
| context7 | plugin | required | 2026-04-10 | |
| sequential-thinking | mcp | recommended | 2026-04-10 | auth required |

## Auth Incomplete
| Item | Type | Auth Step | Last Attempted |
|------|------|-----------|----------------|
| sequential-thinking | mcp | Run: npx @modelcontextprotocol/... | 2026-04-10 |
```

Items are removed from `pending_setup.md` once successfully installed or explicitly dismissed by the user.

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
- If `brain.md` does not exist: creates full skeleton, fills structural sections, leaves knowledge sections as placeholders, sets `llm_analysis: pending`
- If `brain.md` exists and git HEAD changed: updates only the structural sections (Project Summary, Tech Stack, Key Files, Directory Map, Recommended Skills); all other sections and the `llm_analysis` flag left intact
- If `brain.md` exists and git HEAD unchanged: exits immediately (no-op)
- `--force` flag: always re-runs the structural scan regardless of HEAD state

**Output:** Updates `brain.md` with `git_head` comment set to current HEAD. Does NOT change `llm_analysis` flag.

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

**New step 2: LLM analysis trigger**

Reads `brain.md`. If `llm_analysis: pending`:

Injects: `[Orch] Brain skeleton ready. Before responding to the first task, analyze the project source files listed in Key Files and populate the Architecture and Conventions sections of .claude/orch/brain.md. Mark llm_analysis as complete when done.`

This is injected once (first session) and cleared after the orch skill completes the analysis.

**New step 3: Setup gap detection**

Runs `discover_tools.py --json` to find missing tools. Also reads `pending_setup.md` (if exists) for deferred items.

If any unresolved setup items exist (new gaps OR pending from previous session):

Injects:
```
[Orch] Setup incomplete. Pending: context7 (plugin, required), sequential-thinking (mcp, recommended).
Say "set up tools" to install and configure them now, or "skip setup" to defer.
```

**New step 4: Brain summary injection**

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

Five new behaviors added to the orch skill:

**LLM analysis phase (first session, automatic):**
Triggered when `session-start.py` injects the analysis instruction (i.e., `llm_analysis: pending`). Before responding to any task:
1. Read the Key Files listed in brain.md (entry points, main modules, config)
2. Analyze: component relationships, data flow patterns, naming conventions, test patterns, coding style
3. Write findings to brain.md Architecture and Conventions sections (concise, bullet form)
4. Set `<!-- llm_analysis: complete -->` in brain.md header
This runs once per project and is never triggered again unless `--force`.

**On "set up tools":**
Read setup gap list (from `discover_tools.py --json` + `pending_setup.md`). For each item, in order by priority:

- **Plugin**: call `install_plugin.py --plugin <name> --marketplace claude-plugins-official`. Report success/failure.
- **MCP**: write entry to `.mcp.json` (project-level) or `~/.claude/settings.json` (global). If auth is required, output the exact auth command and prompt the user to run it:
  ```
  [Orch] MCP <name> added to config. Auth required — please run:
  <auth command>
  Then say "auth done" to continue setup.
  ```
  Wait for "auth done" before proceeding to next item.
- **On decline**: write declined items to `pending_setup.md` with current timestamp.

**On "skip setup":**
Write all currently surfaced gaps to `pending_setup.md`. Session continues without installing.

**On next session / orch invocation with pending_setup.md items:**
If `pending_setup.md` is non-empty and session-start injects the pending notice, offer to resume:
`[Orch] You have N deferred setup items. Say "set up tools" to resume, or "dismiss setup" to clear the list.`

**On new Standard/Complex task:**
Before writing `session.md`, read `brain.md` (conventions, decisions log). Check `tasks.md` for active tasks that might conflict or relate. Write new entry to `tasks.md` Active Tasks table.

**On "refresh brain":**
Run `init_brain.py --force`, then trigger LLM analysis phase again (sets `llm_analysis: pending`, re-populates Architecture/Conventions from scratch).

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
3. `init_brain.py` runs (codebase scan → `.claude/orch/brain.md` skeleton, `llm_analysis: pending`) — new
4. Hook injects LLM analysis instruction (because `llm_analysis: pending`)
5. `discover_tools.py` runs → if gaps, injects setup notice — new
6. Hook injects: setup summary + brain summary
7. Claude's first action: LLM analysis of key source files → populates Architecture + Conventions, sets `llm_analysis: complete`
8. User says "set up tools" → orch skill installs plugins + MCPs one-by-one (with auth prompting if needed)
9. All subsequent prompts get full project context + complexity gate from `prompt-submit.py`

On subsequent sessions: steps 3-4 skipped (brain exists, HEAD unchanged); brain summary injected immediately; pending setup items resurfaced if any.

---

## Out of Scope

- Multi-user or team-shared brains (brain.md is local to the developer's project root)
- Cross-project brain sharing or templates
- MCP auth flows that require a browser (OAuth-based MCPs — only CLI-auth MCPs are handled interactively)

---

## Verification

After implementing:

1. Fresh project: start session → `brain.md` created with structural skeleton, `llm_analysis: pending`
2. First session: Claude reads key files → populates Architecture + Conventions → sets `llm_analysis: complete`
3. Session-start injects setup gap list → user says "set up tools" → plugins installed, MCPs configured, auth prompted if needed
4. User declines one MCP → written to `pending_setup.md` → next session resurfaces it
5. Pull new commits: start next session → brain structural sections auto-refreshed, knowledge sections intact
6. Submit any task prompt (no `/orch` invoked): hook injects `[ORCH]` context block + complexity gate
7. Complete a task via `orch-planner`: `history.md` appended, `tasks.md` updated
8. Start new session: brain summary injected immediately, no codebase re-scan, LLM analysis not re-triggered
