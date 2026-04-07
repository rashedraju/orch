# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository is the **session-coach plugin** — a multi-platform Claude Code plugin that acts as an autonomous session coach for AI coding agents. It auto-initializes setup, handles fuzzy prompts, preserves plan state across compactions, and manages full project workflow.

## Plugin Architecture

The repo root is the plugin root. Key directories:

```
skills/session-coach/   — Main orchestrator skill (complexity gate, planning, routing)
skills/coach-planner/   — Living plan management (session.md format, replan logic)
skills/coach-monitor/   — Token/context health monitoring
hooks/                  — Automation layer (4 hooks, Python)
.claude-plugin/         — Plugin metadata
```

The `.claude/skills/session-coach/` directory is an older copy kept for local dev testing. The canonical source is `skills/`.

## Skill Responsibilities

**`session-coach`** — Orchestrator. Complexity gate, phase detection, fuzzy vs concrete routing, special case routing, prompt writing. Delegates plan work to `coach-planner` and health monitoring to `coach-monitor`.

**`coach-planner`** — Everything about `session.md`: format, step states, replan procedure, token safety, mode rules, session end sequence.

**`coach-monitor`** — Token budget guidelines, when to run `/compact`, when to start a new session, context health signals, transition checklist.

## Hook Architecture

Four hooks run automatically in Claude Code (no user action needed):

| Hook | File | What it does |
|------|------|-------------|
| `SessionStart` | `hooks/session-start.py` | Runs `init_setup.py` if stale, injects setup summary as context |
| `UserPromptSubmit` | `hooks/prompt-submit.py` | Detects fuzzy prompts, injects resume reminder if plan active |
| `Stop` | `hooks/stop-hook.py` | Warns if stopping mid-plan |
| `PreCompact` | `hooks/pre-compact.py` | Preserves plan state before compaction |

Hooks use platform detection to output the correct JSON format for Claude Code, Cursor, and Copilot CLI.

## Scripts (in `skills/session-coach/scripts/`)

- **`init_setup.py`** — Scans `~/.claude/` config + project tech stack → writes `references/setup.md`. Respects 7-day staleness, `--force` to override.
- **`discover_tools.py`** — Matches project stack to marketplace plugins → ranked recommendations table.
- **`install_plugin.py`** — Downloads + registers a plugin (handles local/url/git-subdir source types).

## Key Design Concepts

**Complexity Gate** — Quick tasks (≤2 steps) get a single prompt, no session.md. Standard/Complex get the living plan.

**Living Plan** (`.claude/session.md`) — Written to the user's project root. Exactly one `[NEXT]` step at all times. Never plan more than 2 steps ahead.

**Hooks as the automation layer** — hooks handle what can be automated (init, fuzzy detection, plan protection); the skills handle intelligent reasoning when invoked.

**Multi-platform** — `hooks/hooks.json` for Claude Code, `hooks/hooks-cursor.json` for Cursor, `AGENTS.md` for Copilot CLI and others.

## Editing

When editing skills: the complexity gate table and Quick-tier output in `session-coach/SKILL.md` must stay in sync. Plan format lives in `coach-planner/SKILL.md` — update it there, not in the main skill.

When editing hooks: test each hook by piping sample JSON via stdin, e.g.:
```bash
echo '{"cwd": "/tmp", "user_prompt": "i want to add something"}' | python3 hooks/prompt-submit.py
```

## Evals

`skills/session-coach/evals.json` has 10 test cases (7 original + 3 new for init/install phases). Run manually with the skill-creator eval workflow.
