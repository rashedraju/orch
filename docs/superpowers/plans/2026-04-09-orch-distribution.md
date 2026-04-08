# Orch Plugin Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Orch plugin installable via `/plugin marketplace add rashedraju/orch` + `/plugin install orch@orch` by adding a marketplace manifest, updating the plugin manifest, and replacing the manual install instructions in the README.

**Architecture:** The `rashedraju/orch` GitHub repo acts as its own marketplace and plugin source. Adding `.claude-plugin/marketplace.json` enables Claude Code to treat the repo as a marketplace. Updating `plugin.json` with a `skills` array ensures Claude Code registers all three skills on install. The hooks file already uses `${CLAUDE_PLUGIN_ROOT}` and requires no changes.

**Tech Stack:** JSON (manifest files), Markdown (README)

---

## File Map

| File | Action |
|------|--------|
| `.claude-plugin/marketplace.json` | Create — new marketplace manifest |
| `.claude-plugin/plugin.json` | Modify — add skills array, fix URL, add metadata |
| `README.md` | Modify — replace Installation section |

---

### Task 1: Create `.claude-plugin/marketplace.json`

**Files:**
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Create the marketplace manifest**

Create `.claude-plugin/marketplace.json` with this exact content:

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

- [ ] **Step 2: Validate JSON syntax**

```bash
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('valid')"
```

Expected output: `valid`

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat: add marketplace.json for standard plugin distribution"
```

---

### Task 2: Update `.claude-plugin/plugin.json`

**Files:**
- Modify: `.claude-plugin/plugin.json`

Current content:
```json
{
  "name": "orch",
  "version": "1.0.0",
  "description": "Ultimate session coach for AI coding agents. Auto-initializes your setup by scanning installed plugins, MCPs, skills, and project tech stack. Handles fuzzy prompts intelligently, monitors plan state across compactions, and manages full project workflow from first idea to final commit.",
  "license": "MIT",
  "homepage": "https://github.com/rashed/orch",
  "author": {
    "name": "Rashed"
  }
}
```

- [ ] **Step 1: Replace with updated manifest**

Overwrite `.claude-plugin/plugin.json` with:

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

Changes from old version:
- `homepage`: `github.com/rashed/orch` → `github.com/rashedraju/orch` (fix typo)
- Added `repository` (same URL)
- Added `category: "development"`
- `author.name`: `"Rashed"` → `"rashedraju"` (match GitHub handle)
- Added `keywords` array
- Added `skills` array with paths to all three skill directories

- [ ] **Step 2: Validate JSON syntax**

```bash
python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); print('valid')"
```

Expected output: `valid`

- [ ] **Step 3: Verify all three skills directories exist**

```bash
ls skills/orch/SKILL.md skills/orch-planner/SKILL.md skills/orch-monitor/SKILL.md
```

Expected: all three files listed, no errors.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: add skills array and fix metadata in plugin.json"
```

---

### Task 3: Update `README.md` Installation Section

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the Installation section content**

In `README.md`, find and replace this exact block (the Claude Code install instructions — the manual `install_plugin.py` approach):

Old text to find (starting at the `## Installation` heading):
```
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
```

Replace with:
```
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

- [ ] **Step 2: Verify old install instructions are gone**

```bash
grep -c "install_plugin.py" README.md
```

Expected: `0`

- [ ] **Step 3: Verify new install commands are present**

```bash
grep "plugin marketplace add" README.md
```

Expected: `/plugin marketplace add rashedraju/orch`

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update README with standard /plugin install instructions"
```

---

## End-to-End Verification

After all three tasks are complete, verify the full install flow works:

1. Run `/plugin marketplace add rashedraju/orch` in a Claude Code session — should succeed with no errors
2. Run `/plugin install orch@orch` — should install to cache and enable in settings
3. Check `~/.claude/settings.json`: `enabledPlugins` should show `"orch@orch": true`
4. Check `~/.claude/plugins/installed_plugins.json`: entry for `orch@orch` should be present with an `installPath`
5. Start a new Claude Code session — `SessionStart` hook should fire (setup summary injected into context)
6. Invoke the `orch` skill — should load without errors
7. Submit a vague prompt (e.g., `"i want to add something"`) — `UserPromptSubmit` hook should inject the coaching nudge
