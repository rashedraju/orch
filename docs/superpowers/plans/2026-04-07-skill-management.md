# Skill Management: Dynamic Routing, Gap Detection & Integrated Creation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Orch proactively detect missing skills before planning, route dynamically to what's installed, and treat skill creation as a tracked session step.

**Architecture:** The `UserPromptSubmit` hook gets a new skill-gap detection pass that reads enabled plugins from `~/.claude/` and injects a `[ORCH] Skill gap detected` notice into context when needed. The `orch` skill's routing section is updated with a priority-hint table (preferred + fallback columns) and instructions for surfacing gap options when a notice is present. Skill creation is handled by adding it as Step 1 in `session.md`.

**Tech Stack:** Python 3.10+ (hook), Markdown (SKILL.md), pytest (tests)

---

## File Map

| File | Change |
|---|---|
| `hooks/prompt-submit.py` | Add `get_enabled_skill_names()`, `TASK_SKILL_MAP`, `detect_skill_gaps()`, `format_gap_notice()`, wire into `main()` |
| `skills/orch/SKILL.md` | Replace static Skill Usage table; add Skill Gap Handling section |
| `tests/test_prompt_submit.py` | New — unit tests for all new hook functions |

---

## Task 1: Create test file with failing tests for `get_enabled_skill_names()`

**Files:**
- Create: `tests/test_prompt_submit.py`

- [ ] **Step 1: Write the test file**

```python
# tests/test_prompt_submit.py
import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Load hook module (hyphenated filename requires importlib)
_spec = importlib.util.spec_from_file_location(
    "prompt_submit",
    Path(__file__).parent.parent / "hooks" / "prompt-submit.py",
)
prompt_submit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prompt_submit)


# ---------------------------------------------------------------------------
# get_enabled_skill_names
# ---------------------------------------------------------------------------

def _make_claude_dir(tmp_path, enabled_plugins: dict, plugins: dict) -> Path:
    """Helper: write settings.json and installed_plugins.json into tmp_path."""
    (tmp_path / "settings.json").write_text(
        json.dumps({"enabledPlugins": enabled_plugins})
    )
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "installed_plugins.json").write_text(
        json.dumps({"plugins": plugins})
    )
    return tmp_path


def _make_plugin_with_skills(base: Path, plugin_name: str, skills: list[str]) -> Path:
    """Helper: create a fake plugin directory with SKILL.md files."""
    plugin_path = base / plugin_name
    for skill in skills:
        skill_dir = plugin_path / "skills" / skill
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill}")
    return plugin_path


def test_returns_skills_from_enabled_plugin(tmp_path):
    plugin_path = _make_plugin_with_skills(
        tmp_path / "cache", "superpowers", ["brainstorming", "writing-plans"]
    )
    claude_dir = _make_claude_dir(
        tmp_path / "claude",
        enabled_plugins={"superpowers": True},
        plugins={"superpowers@official": {"installPath": str(plugin_path)}},
    )
    skills = prompt_submit.get_enabled_skill_names(claude_dir=claude_dir)
    assert "brainstorming" in skills
    assert "writing-plans" in skills


def test_excludes_skills_from_disabled_plugin(tmp_path):
    plugin_path = _make_plugin_with_skills(
        tmp_path / "cache", "frontend-design", ["frontend-design"]
    )
    claude_dir = _make_claude_dir(
        tmp_path / "claude",
        enabled_plugins={"frontend-design": False},  # disabled
        plugins={"frontend-design@official": {"installPath": str(plugin_path)}},
    )
    skills = prompt_submit.get_enabled_skill_names(claude_dir=claude_dir)
    assert "frontend-design" not in skills


def test_returns_none_when_files_missing(tmp_path):
    # No settings.json or installed_plugins.json — returns None to signal skip
    skills = prompt_submit.get_enabled_skill_names(claude_dir=tmp_path / "nonexistent")
    assert skills is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/rashed/workplace/orch && python -m pytest tests/test_prompt_submit.py::test_returns_skills_from_enabled_plugin tests/test_prompt_submit.py::test_excludes_skills_from_disabled_plugin tests/test_prompt_submit.py::test_returns_none_when_files_missing -v
```

Expected: `AttributeError: module 'prompt_submit' has no attribute 'get_enabled_skill_names'`

---

## Task 2: Write failing tests for `detect_skill_gaps()` and `format_gap_notice()`

**Files:**
- Modify: `tests/test_prompt_submit.py` (append)

- [ ] **Step 1: Append gap detection tests**

```python
# ---------------------------------------------------------------------------
# detect_skill_gaps
# ---------------------------------------------------------------------------

def test_gap_detected_when_skill_missing():
    # frontend-design installed, but ui-ux-pro-max is not
    gaps = prompt_submit.detect_skill_gaps(
        "I need to build a login form component",
        enabled_skills={"frontend-design", "writing-plans"},
    )
    assert len(gaps) == 1
    assert gaps[0]["task_type"] == "ui"
    assert "ui-ux-pro-max" in gaps[0]["missing_skills"]
    assert "frontend-design" not in gaps[0]["missing_skills"]


def test_no_gap_when_all_skills_present():
    gaps = prompt_submit.detect_skill_gaps(
        "build a UI component",
        enabled_skills={"ui-ux-pro-max", "frontend-design"},
    )
    assert gaps == []


def test_no_gap_for_generic_prompt():
    gaps = prompt_submit.detect_skill_gaps(
        "help me understand this code",
        enabled_skills=set(),
    )
    assert gaps == []


def test_multiple_gaps_for_multi_type_prompt():
    gaps = prompt_submit.detect_skill_gaps(
        "fix this typescript bug in the UI",
        enabled_skills=set(),
    )
    task_types = {g["task_type"] for g in gaps}
    assert "ui" in task_types
    assert "typescript" in task_types
    assert "debugging" in task_types


# ---------------------------------------------------------------------------
# format_gap_notice
# ---------------------------------------------------------------------------

def test_format_gap_notice_contains_skill_name():
    gaps = [{"task_type": "ui", "missing_skills": ["ui-ux-pro-max"]}]
    notice = prompt_submit.format_gap_notice(gaps)
    assert "[ORCH] Skill gap detected" in notice
    assert "ui-ux-pro-max" in notice
    assert "install" in notice.lower()
    assert "skill-creator" in notice


def test_format_gap_notice_lists_all_missing():
    gaps = [{"task_type": "laravel", "missing_skills": ["laravel-specialist", "php-pro"]}]
    notice = prompt_submit.format_gap_notice(gaps)
    assert "laravel-specialist" in notice
    assert "php-pro" in notice
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/rashed/workplace/orch && python -m pytest tests/test_prompt_submit.py -k "gap or notice" -v
```

Expected: `AttributeError: module 'prompt_submit' has no attribute 'detect_skill_gaps'`

---

## Task 3: Write failing integration test for `main()` gap injection

**Files:**
- Modify: `tests/test_prompt_submit.py` (append)

- [ ] **Step 1: Append integration test**

```python
# ---------------------------------------------------------------------------
# main() integration — gap notice wired through
# ---------------------------------------------------------------------------

import io
from unittest.mock import patch


def test_main_injects_gap_notice_for_ui_prompt(tmp_path):
    hook_input = json.dumps({
        "user_prompt": "I need to build a settings page with a form",
        "cwd": str(tmp_path),
    })
    # Patch get_enabled_skill_names to return skills without ui-ux-pro-max
    with patch.object(
        prompt_submit, "get_enabled_skill_names",
        return_value={"frontend-design", "writing-plans"},
    ):
        with patch("sys.stdin", io.StringIO(hook_input)):
            captured = []
            with patch("builtins.print", side_effect=lambda x: captured.append(x)):
                with pytest.raises(SystemExit):
                    prompt_submit.main()

    assert len(captured) == 1
    output = json.loads(captured[0])
    # Normalise across platform output formats
    context = (
        output.get("hookSpecificOutput", {}).get("additionalContext")
        or output.get("additionalContext")
        or output.get("additional_context")
        or ""
    )
    assert "[ORCH] Skill gap detected" in context
    assert "ui-ux-pro-max" in context


def test_main_no_gap_notice_when_all_skills_present(tmp_path):
    hook_input = json.dumps({
        "user_prompt": "I need to build a settings page with a form",
        "cwd": str(tmp_path),
    })
    with patch.object(
        prompt_submit, "get_enabled_skill_names",
        return_value={"ui-ux-pro-max", "frontend-design", "writing-plans"},
    ):
        with patch("sys.stdin", io.StringIO(hook_input)):
            captured = []
            with patch("builtins.print", side_effect=lambda x: captured.append(x)):
                with pytest.raises(SystemExit):
                    prompt_submit.main()

    # No output printed when no gaps and no active plan
    assert len(captured) == 0
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /home/rashed/workplace/orch && python -m pytest tests/test_prompt_submit.py::test_main_injects_gap_notice_for_ui_prompt tests/test_prompt_submit.py::test_main_no_gap_notice_when_all_skills_present -v
```

Expected: `AttributeError` or `AssertionError`

---

## Task 4: Implement `get_enabled_skill_names()` in `prompt-submit.py`

**Files:**
- Modify: `hooks/prompt-submit.py`

- [ ] **Step 1: Add the function after the existing imports/constants block (after line 21)**

Add after the `FUZZY_KEYWORDS` line:

```python
def get_enabled_skill_names(claude_dir: Path | None = None) -> set[str] | None:
    """Return skill names available from all currently-enabled plugins.

    Returns None if config files cannot be read (caller should skip gap detection).
    Returns an empty set if files are readable but no skills are found.
    """
    if claude_dir is None:
        claude_dir = Path.home() / ".claude"

    try:
        settings = json.loads((claude_dir / "settings.json").read_text())
        enabled = {k for k, v in settings.get("enabledPlugins", {}).items() if v}
    except Exception:
        return None  # Can't read config — skip gap detection to avoid false positives

    try:
        installed_data = json.loads(
            (claude_dir / "plugins" / "installed_plugins.json").read_text()
        )
        plugins = installed_data.get("plugins", {})
    except Exception:
        return None  # Can't read install registry — skip gap detection

    skills: set[str] = set()
    for plugin_key, plugin_data in plugins.items():
        plugin_name = plugin_key.split("@")[0]
        if plugin_name not in enabled:
            continue
        install_path = plugin_data.get("installPath", "")
        if not install_path:
            continue
        skills_dir = Path(install_path) / "skills"
        if skills_dir.is_dir():
            for skill_dir in skills_dir.iterdir():
                if (skill_dir / "SKILL.md").exists():
                    skills.add(skill_dir.name)

    return skills
```

- [ ] **Step 2: Run the `get_enabled_skill_names` tests**

```bash
cd /home/rashed/workplace/orch && python -m pytest tests/test_prompt_submit.py::test_returns_skills_from_enabled_plugin tests/test_prompt_submit.py::test_excludes_skills_from_disabled_plugin tests/test_prompt_submit.py::test_returns_none_when_files_missing -v
```

Expected: all 3 PASS

---

## Task 5: Implement `TASK_SKILL_MAP`, `detect_skill_gaps()`, and `format_gap_notice()`

**Files:**
- Modify: `hooks/prompt-submit.py`

- [ ] **Step 1: Add constants and functions after `get_enabled_skill_names()`**

```python
TASK_SKILL_MAP: dict[str, dict] = {
    "ui": {
        "keywords": {
            "ui", "component", "layout", "design", "frontend",
            "button", "modal", "form", "page", "view", "interface",
        },
        "skills": ["ui-ux-pro-max", "frontend-design"],
    },
    "laravel": {
        "keywords": {
            "laravel", "php", "blade", "eloquent", "artisan",
            "migration", "controller",
        },
        "skills": ["laravel-specialist", "php-pro"],
    },
    "typescript": {
        "keywords": {"typescript", "tsc", "type error", "generic", "interface"},
        "skills": ["ts-check"],
    },
    "debugging": {
        "keywords": {
            "bug", "error", "failing", "broken", "crash",
            "exception", "traceback", "debug",
        },
        "skills": ["systematic-debugging"],
    },
    "refactor": {
        "keywords": {
            "refactor", "extract", "clean up", "cleanup",
            "restructure", "rename",
        },
        "skills": ["using-git-worktrees"],
    },
}


def detect_skill_gaps(prompt: str, enabled_skills: set[str]) -> list[dict]:
    """Return [{task_type, missing_skills}] for each detected gap."""
    lower = prompt.lower()
    gaps = []
    for task_type, config in TASK_SKILL_MAP.items():
        if not any(kw in lower for kw in config["keywords"]):
            continue
        missing = [s for s in config["skills"] if s not in enabled_skills]
        if missing:
            gaps.append({"task_type": task_type, "missing_skills": missing})
    return gaps


def format_gap_notice(gaps: list[dict]) -> str:
    """Format gap list into a context notice for Orch."""
    lines = []
    for gap in gaps:
        missing_str = ", ".join(f"`{s}`" for s in gap["missing_skills"])
        lines.append(
            f"[ORCH] Skill gap detected: task looks like {gap['task_type']} work "
            f"but {missing_str} is not installed.\n"
            f"Options: install → `python scripts/install_plugin.py --plugin <name> "
            f"--marketplace claude-plugins-official` | proceed with fallback | "
            f"create new skill → invoke `skill-creator`"
        )
    return "\n\n".join(lines)
```

- [ ] **Step 2: Run the gap detection and notice tests**

```bash
cd /home/rashed/workplace/orch && python -m pytest tests/test_prompt_submit.py -k "gap or notice" -v
```

Expected: all 6 PASS

---

## Task 6: Wire gap detection into `main()`

**Files:**
- Modify: `hooks/prompt-submit.py`

- [ ] **Step 1: Add gap detection call in `main()`, after the fuzzy-prompt check**

Replace the existing `main()` function body with:

```python
def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    prompt = hook_input.get("user_prompt", "").strip()
    cwd = hook_input.get("cwd") or os.getcwd()

    notes = []

    # Check for active plan
    active_step = get_active_plan_step(cwd)
    if active_step:
        notes.append(
            f"[Orch.] Active plan detected. Current step: **{active_step}**. "
            "Say 'resume session' to pick up where you left off, or continue with your new prompt."
        )

    # Check for fuzzy prompt
    if prompt and is_fuzzy(prompt) and not active_step:
        notes.append(
            "[Orch.] This looks like a vague prompt. "
            "For best results, try: \"Use orch to plan this: " + prompt + "\""
        )

    # Check for skill gaps (skip if config unreadable — avoids false positives)
    if prompt and not active_step:
        enabled_skills = get_enabled_skill_names()
        if enabled_skills is not None:
            gaps = detect_skill_gaps(prompt, enabled_skills)
            if gaps:
                notes.append(format_gap_notice(gaps))

    if notes:
        emit_context("\n\n".join(notes))

    sys.exit(0)
```

- [ ] **Step 2: Run all tests**

```bash
cd /home/rashed/workplace/orch && python -m pytest tests/test_prompt_submit.py -v
```

Expected: all tests PASS

- [ ] **Step 3: Smoke-test the hook manually**

```bash
echo '{"cwd": "/tmp", "user_prompt": "I need to build a settings page with a form"}' | python3 /home/rashed/workplace/orch/hooks/prompt-submit.py
```

Expected: JSON output with `[ORCH] Skill gap detected` in the context string (assuming `ui-ux-pro-max` is not installed).

```bash
echo '{"cwd": "/tmp", "user_prompt": "fix this small typo"}' | python3 /home/rashed/workplace/orch/hooks/prompt-submit.py
```

Expected: no output (empty stdout, exit 0).

- [ ] **Step 4: Commit**

```bash
cd /home/rashed/workplace/orch && git add hooks/prompt-submit.py tests/test_prompt_submit.py && git commit -m "feat: add skill gap detection to UserPromptSubmit hook"
```

---

## Task 7: Update `skills/orch/SKILL.md` — routing section

**Files:**
- Modify: `skills/orch/SKILL.md`

- [ ] **Step 1: Replace the static `### Skill Usage` table (lines 116–129) with the new dynamic section**

Find and replace this exact block:

```markdown
### Skill Usage

| Situation | Skills |
|---|---|
| Session start (fresh) | `smart-explore` |
| All planning phases | `writing-plans` |
| UI work | `ui-ux-pro-max` + `frontend-design` |
| Laravel/PHP work | `laravel-specialist` + `php-pro` |
| TypeScript work | end phase with `ts-check` |
| After implementation | `verification-before-completion` → `requesting-code-review` |
| Session end | `timeline-report` → `finishing-a-development-branch` |
| Token/context health | `orch-monitor` |
| Plan management | `orch-planner` |
| Needed skill doesn't exist | `skill-creator` |
```

Replace with:

```markdown
### Skill Gap Handling

If the context contains a `[ORCH] Skill gap detected` notice, **surface it before routing**:

```
⚠️ Skill gap: `<skill>` is not installed.
A) Install now: `python scripts/install_plugin.py --plugin <name> --marketplace claude-plugins-official`
B) Proceed with fallback skill (see table below)
C) Create a new skill: I'll add "Create <skill> using skill-creator" as Step 1 in session.md
```

If the user picks **C**: add `Step 1: Create [skill-name] using skill-creator` to `session.md`. After skill-creator completes, include `python scripts/init_setup.py --force` in the step's done-prompt to refresh `references/setup.md`.

### Skill Usage

Before routing, read the `## Available Skills` list from `references/setup.md` (injected at session start). Route to the **Preferred** skill if it appears in that list; otherwise use **Fallback**. If no fallback exists, note the gap in the session.md header and proceed.

> **If `references/setup.md` is missing or the Available Skills section is absent**, fall back to the Preferred column of the table below without checking availability, and log a warning: `⚠️ setup.md unavailable — using static routing. Run \`python scripts/init_setup.py --force\` to regenerate.`

| Situation | Preferred | Fallback |
|---|---|---|
| Session start (fresh) | `smart-explore` | explore manually |
| All planning phases | `writing-plans` | — (required) |
| UI work | `ui-ux-pro-max` + `frontend-design` | `frontend-design` alone |
| Laravel/PHP work | `laravel-specialist` + `php-pro` | `php-pro` alone |
| TypeScript work | `ts-check` | note gap, proceed |
| After implementation | `verification-before-completion` → `requesting-code-review` | — (required) |
| Session end | `timeline-report` → `finishing-a-development-branch` | skip `timeline-report` |
| Token/context health | `orch-monitor` | — (required) |
| Plan management | `orch-planner` | — (required) |
| Needed skill doesn't exist | `skill-creator` | — |
```

- [ ] **Step 2: Verify the skill file looks correct**

```bash
grep -n "Skill Gap\|Preferred\|Fallback\|Available Skills" /home/rashed/workplace/orch/skills/orch/SKILL.md
```

Expected output includes lines with "Skill Gap Handling", "Preferred", "Fallback", and "Available Skills".

- [ ] **Step 3: Also update the hooks description line at the top of the file (line 10)**

Find:
```
**Hooks active:** The `SessionStart` hook auto-runs initialization and injects your setup knowledge base at the start of every session. `UserPromptSubmit` detects fuzzy prompts. `Stop` and `PreCompact` protect plan state automatically.
```

Replace with:
```
**Hooks active:** The `SessionStart` hook auto-runs initialization and injects your setup knowledge base at the start of every session. `UserPromptSubmit` detects fuzzy prompts and skill gaps. `Stop` and `PreCompact` protect plan state automatically.
```

- [ ] **Step 4: Commit**

```bash
cd /home/rashed/workplace/orch && git add skills/orch/SKILL.md && git commit -m "feat: dynamic skill routing with gap handling in orch skill"
```

---

## Task 8: Sync `.claude/skills/orch/` (local dev copy)

The CLAUDE.md notes that `.claude/skills/orch/` is a local dev copy kept in sync with `skills/orch/`.

**Files:**
- Modify: `.claude/skills/orch/SKILL.md`

- [ ] **Step 1: Check if the local copy exists and needs updating**

```bash
diff /home/rashed/workplace/orch/skills/orch/SKILL.md /home/rashed/workplace/orch/.claude/skills/orch/SKILL.md
```

- [ ] **Step 2: If different, copy the canonical version over**

```bash
cp /home/rashed/workplace/orch/skills/orch/SKILL.md /home/rashed/workplace/orch/.claude/skills/orch/SKILL.md
```

- [ ] **Step 3: Commit if changed**

```bash
cd /home/rashed/workplace/orch && git add .claude/skills/orch/SKILL.md && git diff --cached --quiet || git commit -m "chore: sync .claude/skills/orch with canonical source"
```

---

## Verification Checklist

- [ ] `python -m pytest tests/test_prompt_submit.py -v` — all tests green
- [ ] `echo '{"cwd": "/tmp", "user_prompt": "build a UI form"}' | python3 hooks/prompt-submit.py` — outputs `[ORCH] Skill gap detected` if `ui-ux-pro-max` not enabled
- [ ] `echo '{"cwd": "/tmp", "user_prompt": "fix small typo"}' | python3 hooks/prompt-submit.py` — silent (no output)
- [ ] `grep "Skill Gap Handling" skills/orch/SKILL.md` — confirms section exists
- [ ] `grep "Preferred.*Fallback" skills/orch/SKILL.md` — confirms new table
- [ ] Start a new Claude Code session, give a UI prompt — verify gap notice appears in context before Orch responds
