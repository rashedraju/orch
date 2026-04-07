# Orch.

> Your AI coding session strategist — auto-plans, tracks progress, and keeps context healthy.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-blueviolet)](https://claude.ai/code)

Orch. is a Claude Code plugin that acts as an autonomous session strategist for AI coding agents. It auto-initializes your environment, turns vague ideas into step-by-step execution plans, monitors token health, and survives context compaction — so every session stays focused and on track.

---

## What it does

- **Auto-initializes** your setup at session start: scans installed plugins, MCPs, skills, and tech stack into a live reference file
- **Complexity gate**: classifies tasks as Quick (single prompt), Standard (living plan), or Complex (checkpointed plan with Opus recommendation)
- **Living plan** (`.claude/session.md`): exactly one `[NEXT]` step at all times; never over-plans
- **Fuzzy prompt detection**: catches vague "I want to add something" prompts and routes to brainstorming first
- **Context health monitoring**: advises when to `/compact` or start a new session based on token usage
- **Plan survival**: `PreCompact` hook preserves plan state before context is compressed; you always know where you left off
- **Multi-platform**: works with Claude Code (full automation via hooks), Cursor, and any agent via manual AGENTS.md workflow

---

## Installation

### Claude Code (recommended — full automation)

```bash
# From your Claude Code project directory
python /path/to/orch/skills/orch/scripts/install_plugin.py \
  --plugin orch \
  --source /path/to/orch
```

Or install manually: copy `skills/`, `hooks/`, and `.claude-plugin/` into your `~/.claude/plugins/orch/` directory, then register it in `~/.claude/settings.json`:

```json
{
  "plugins": ["orch"]
}
```

### Cursor

Copy `hooks/hooks-cursor.json` to your project root as `.cursor/hooks.json`. Point the hook commands to the hooks directory:

```json
{
  "sessionStart": "python3 /path/to/orch/hooks/session-start.py",
  "userPromptSubmit": "python3 /path/to/orch/hooks/prompt-submit.py"
}
```

### Other agents (Copilot CLI, Aider, Codex, etc.)

See [AGENTS.md](AGENTS.md) for the manual equivalent workflow. No hooks required — just reference the skill files directly in your prompts.

---

## How it works

### Complexity gate

Every task is classified before any output:

| Tier | Criteria | Output |
|------|----------|--------|
| **Quick** | Single file, obvious fix, ≤2 steps | One copy-paste prompt — no plan file |
| **Standard** | Multi-step, 2+ files or systems | `session.md` living plan |
| **Complex** | Cross-system, architecture decisions, high risk | `session.md` + STOP checkpoints + Opus recommendation |

### Living plan (`session.md`)

The plan file lives at `.claude/session.md` in your project root. It has exactly one `[NEXT]` step at all times. Steps are states: `[DONE]`, `[NEXT]`, `[STUB]`, `[SKIPPED]`. You never see a wall of pre-planned steps — only the immediate next action.

Example lifecycle:
1. You describe a task → coach classifies it, writes `session.md` with Step 1
2. You run Step 1 → say "step done" → coach marks it done, writes Step 2
3. Context gets compacted → `PreCompact` hook saves state → resume picks up at `[NEXT]`

### Hooks (Claude Code)

| Hook | File | What it does |
|------|------|-------------|
| `SessionStart` | `hooks/session-start.py` | Runs `init_setup.py` if stale; injects setup summary as context |
| `UserPromptSubmit` | `hooks/prompt-submit.py` | Detects fuzzy prompts; injects resume reminder if plan is active |
| `Stop` | `hooks/stop-hook.py` | Warns when stopping mid-plan with incomplete steps |
| `PreCompact` | `hooks/pre-compact.py` | Extracts and preserves plan state before context compaction |

---

## Skills reference

| Skill | Purpose |
|-------|---------|
| `orch` | Main orchestrator: complexity gate, phase detection, prompt writing, routing |
| `orch-planner` | `session.md` format, step management, replan logic, token safety |
| `orch-monitor` | Token budget guidelines, when to `/compact`, when to start a new session |

---

## Scripts

Located in `skills/orch/scripts/`:

| Script | Purpose |
|--------|---------|
| `init_setup.py` | Scans `~/.claude/` config + project tech stack → writes `references/setup.md` |
| `discover_tools.py` | Matches project stack to recommended plugins → ranked table |
| `install_plugin.py` | Downloads and registers a plugin (local, URL, or git-subdir sources) |

---

## Requirements

- Python 3.8 or later (standard library only — no external packages)
- Claude Code, Cursor, or any AI coding agent

---

## Project layout

```
orch/
├── skills/
│   ├── orch/               # Main orchestrator skill + scripts
│   ├── orch-planner/       # Living plan management skill
│   └── orch-monitor/       # Token/context health skill
├── hooks/                  # Automation hooks (Python)
│   ├── hooks.json          # Claude Code hook config
│   ├── hooks-cursor.json   # Cursor hook config
│   ├── session-start.py
│   ├── prompt-submit.py
│   ├── stop-hook.py
│   └── pre-compact.py
├── .claude-plugin/
│   └── plugin.json         # Plugin metadata
├── .claude/                # Dev tooling config (skill-creator, commit-commands)
├── AGENTS.md               # Manual workflow for non-Claude-Code agents
└── CLAUDE.md               # Guidance for Claude Code when editing this repo
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, how to test hooks, run evals, and submit pull requests.

---

## License

MIT — see [LICENSE](LICENSE).
