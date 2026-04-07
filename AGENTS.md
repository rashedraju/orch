# Session Coach — Universal Agent Instructions

This file is for AI coding agents that don't have the Claude Code plugin/hook system (e.g., Copilot CLI, Codex CLI, Aider). It documents the equivalent manual workflow.

---

## What the hooks do automatically (Claude Code only)

In Claude Code, four hooks run automatically:
- **SessionStart**: Scans your setup and injects your config into every session
- **UserPromptSubmit**: Detects vague prompts and suggests the session-coach skill
- **Stop**: Warns if you're ending a session with incomplete plan steps
- **PreCompact**: Preserves your plan state before context compaction

**If your agent doesn't have hooks**, follow the manual steps below.

---

## Manual Initialization (do once per project or when setup changes)

Run from the session-coach skill directory:

```bash
python skills/session-coach/scripts/init_setup.py --project-path /path/to/your/project
```

This generates `skills/session-coach/references/setup.md` with your current config. Read it at the start of any session to understand available tools.

---

## Manual Tool Discovery (do when starting on a new project type)

```bash
python skills/session-coach/scripts/discover_tools.py --project-path /path/to/your/project
```

Review the recommendations and install approved tools:

```bash
python skills/session-coach/scripts/install_plugin.py --plugin <name> --marketplace claude-plugins-official
```

---

## Session Coach Workflow

### Starting a new task

Tell your agent:
> "Read `skills/session-coach/SKILL.md` and act as a session coach for this task: [your task]"

The agent will classify complexity, detect fuzzy vs concrete start, and create `.claude/session.md`.

### Managing the living plan

Tell your agent:
> "Read `skills/coach-planner/SKILL.md` and [create/update/advance] the session plan."

### Monitoring token usage

Tell your agent:
> "Read `skills/coach-monitor/SKILL.md`. Should I compact or start a new session?"

### Resuming after context compaction

Tell your agent:
> "Read `.claude/session.md` and resume the session from the current [NEXT] step."

---

## Skill Files

| Skill | Path | Purpose |
|-------|------|---------|
| session-coach | `skills/session-coach/SKILL.md` | Main orchestrator |
| coach-planner | `skills/coach-planner/SKILL.md` | Living plan management |
| coach-monitor | `skills/coach-monitor/SKILL.md` | Token/context health |
