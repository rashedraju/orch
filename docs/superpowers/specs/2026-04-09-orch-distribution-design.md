# Orch Plugin — Standard Distribution Design

**Date:** 2026-04-09  
**Status:** Approved  
**Approach:** Self-contained marketplace (Approach A)

---

## Context

Orch is currently installed by manually running `install_plugin.py`, which requires the user to have a local clone and run a Python script with a path argument. This is a friction-heavy, non-standard experience that doesn't match how other Claude Code plugins work.

The goal is to make Orch installable with the two-command standard pattern:

```
/plugin marketplace add rashedraju/orch
/plugin install orch@orch
```

The `rashedraju/orch` GitHub repo (already public) will serve as both the marketplace source and the plugin source — the same dual role that `nextlevelbuilder/ui-ux-pro-max-skill` plays for the ui-ux-pro-max plugin.

---

## What Changes

**Three files. Nothing else.**

| File | Action | Reason |
|------|--------|--------|
| `.claude-plugin/marketplace.json` | Create | Claude Code reads this when the repo is added as a marketplace; without it, `/plugin marketplace add` has nothing to read |
| `.claude-plugin/plugin.json` | Update | Add `skills` array, fix homepage URL, add `repository`, `category`, `keywords` |
| `README.md` | Update | Replace manual `install_plugin.py` instructions with the two-command block |

**Nothing else changes.** Hooks (`hooks/hooks.json`) are already correctly formatted with `${CLAUDE_PLUGIN_ROOT}` references and will auto-register when the plugin is enabled. All skills, Python hook scripts, CLAUDE.md, AGENTS.md — untouched.

---

## File Specs

### 1. `.claude-plugin/marketplace.json` (new file)

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "orch",
  "description": "Orch. plugin marketplace — autonomous session coach for AI coding agents",
  "owner": {
    "name": "rashedraju"
  },
  "plugins": [
    {
      "name": "orch",
      "description": "Autonomous session coach for AI coding agents. Auto-initializes setup, detects skill gaps, handles fuzzy prompts intelligently, preserves plan state across compactions, and manages full project workflow from first idea to final commit.",
      "version": "1.0.0",
      "category": "development",
      "author": {
        "name": "rashedraju"
      },
      "source": {
        "source": "github",
        "repo": "rashedraju/orch"
      },
      "homepage": "https://github.com/rashedraju/orch",
      "repository": "https://github.com/rashedraju/orch",
      "license": "MIT",
      "keywords": ["session-coach", "planning", "orchestration", "workflow", "productivity"]
    }
  ]
}
```

### 2. `.claude-plugin/plugin.json` (updated)

Changes from current:
- Fix `homepage` URL: `github.com/rashed/orch` → `github.com/rashedraju/orch`
- Add `repository` field
- Add `category`
- Add `keywords`
- Add `skills` array pointing to all three skill directories

```json
{
  "name": "orch",
  "version": "1.0.0",
  "description": "Ultimate session coach for AI coding agents. Auto-initializes your setup by scanning installed plugins, MCPs, skills, and project tech stack. Handles fuzzy prompts intelligently, monitors plan state across compactions, and manages full project workflow from first idea to final commit.",
  "license": "MIT",
  "homepage": "https://github.com/rashedraju/orch",
  "repository": "https://github.com/rashedraju/orch",
  "category": "development",
  "author": {
    "name": "rashedraju"
  },
  "keywords": ["session-coach", "planning", "orchestration", "workflow", "productivity"],
  "skills": [
    "./skills/orch",
    "./skills/orch-planner",
    "./skills/orch-monitor"
  ]
}
```

### 3. `README.md` — Installation Section (updated)

Replace the entire `## Installation` section (from `## Installation` heading through the end of the Cursor block, stopping before `## How it works`) with:

```markdown
## Installation

### Claude Code (recommended — full automation)

Install directly in Claude Code with two commands:

```
/plugin marketplace add rashedraju/orch
/plugin install orch@orch
```

Hooks register automatically. Skills (`orch`, `orch-planner`, `orch-monitor`) are immediately available.

### Cursor

Copy `hooks/hooks-cursor.json` to your project root as `.cursor/hooks.json`. Point the hook commands to the hooks directory:

```json
{
  "sessionStart": "python3 /path/to/orch/hooks/session-start.py",
  "userPromptSubmit": "python3 /path/to/orch/hooks/prompt-submit.py"
}
```

### Other agents (Copilot CLI, Aider, Codex, etc.)

See [AGENTS.md](AGENTS.md) for the manual equivalent workflow. No hooks required — reference the skill files directly in your prompts.
```

---

## Install Flow (What Happens Under the Hood)

1. `/plugin marketplace add rashedraju/orch` — Claude Code clones `rashedraju/orch` to `~/.claude/plugins/marketplaces/orch/`
2. `/plugin install orch@orch` — Claude Code reads `~/.claude/plugins/marketplaces/orch/.claude-plugin/marketplace.json`
3. Finds the `orch` plugin entry with `source: {source: "github", repo: "rashedraju/orch"}`
4. Clones/copies to `~/.claude/plugins/cache/orch/orch/1.0.0/`
5. Registers entry in `~/.claude/plugins/installed_plugins.json`
6. Enables under `enabledPlugins.orch@orch: true` in `~/.claude/settings.json`
7. Hooks from `hooks/hooks.json` auto-register (SessionStart, UserPromptSubmit, Stop, PreCompact)
8. Skills (`./skills/orch`, `./skills/orch-planner`, `./skills/orch-monitor`) become available via the Skill tool

---

## Prerequisites

The `feature/skill-management` branch (skill gap detection in `prompt-submit.py` + dynamic routing in `SKILL.md`) should be merged to `main` before this distribution work is done, so the published version is complete.

---

## Verification

After implementing, verify end-to-end on a clean config:

1. In a Claude Code session, run `/plugin marketplace add rashedraju/orch` — should succeed with no errors
2. Run `/plugin install orch@orch` — should install to cache and enable in settings
3. Check `~/.claude/settings.json` — `enabledPlugins` should show `"orch@orch": true`
4. Check `~/.claude/plugins/installed_plugins.json` — entry for `orch@orch` should be present
5. Start a new Claude Code session — `SessionStart` hook should fire (setup summary injected)
6. Run `/orch` or invoke the `orch` skill — should load correctly
7. Submit a vague prompt — `UserPromptSubmit` hook should detect it and inject the nudge

---

## Out of Scope

- Version pinning / GitHub releases (Approach B enhancement — can be added later)
- Submission to `claude-plugins-official` (Approach C — pursue after the plugin is stable)
- CLI tool (`orch-cli` npm package)
- Cursor marketplace distribution (separate effort)
