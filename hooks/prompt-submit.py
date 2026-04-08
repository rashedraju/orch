#!/usr/bin/env python3
"""
UserPromptSubmit hook for Orch. plugin.

Detects fuzzy/vague prompts and injects a coaching nudge.
Also injects a resume reminder if an active session plan exists.
Always non-blocking (exit 0).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

FUZZY_STARTERS = (
    "i want to", "i'm thinking", "i was thinking", "not sure", "maybe",
    "help me", "i need to", "i'd like to", "i need help", "can you help",
)

FUZZY_KEYWORDS = {"want", "add", "make", "help", "something", "maybe", "sort of", "kind of"}


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


def is_fuzzy(prompt: str) -> bool:
    lower = prompt.lower().strip()
    # Very short and vague
    words = lower.split()
    if len(words) <= 8 and len(FUZZY_KEYWORDS & set(words)) >= 1:
        return True
    # Starts with a fuzzy phrase
    for starter in FUZZY_STARTERS:
        if lower.startswith(starter):
            return True
    return False


def get_active_plan_step(cwd: str) -> str | None:
    """Return the [NEXT] step name from session.md if it exists."""
    session_md = Path(cwd) / ".claude" / "session.md"
    if not session_md.exists():
        return None
    try:
        content = session_md.read_text()
        match = re.search(r"### \[NEXT\] Step \d+ — (.+)", content)
        return match.group(1).strip() if match else None
    except Exception:
        return None


def emit_context(context: str) -> None:
    cursor_root = os.environ.get("CURSOR_PLUGIN_ROOT", "")
    copilot_cli = os.environ.get("COPILOT_CLI", "")
    claude_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")

    if cursor_root:
        print(json.dumps({"additional_context": context}))
    elif claude_root and not copilot_cli:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }))
    else:
        print(json.dumps({"additionalContext": context}))


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
    # When skill config is readable, gap detection supersedes the fuzzy nudge
    if prompt and not active_step:
        enabled_skills = get_enabled_skill_names()
        if enabled_skills is not None:
            notes = [n for n in notes if not n.startswith("[Orch.] This looks like a vague")]
            gaps = detect_skill_gaps(prompt, enabled_skills)
            if gaps:
                notes.append(format_gap_notice(gaps))

    if notes:
        emit_context("\n\n".join(notes))

    sys.exit(0)


if __name__ == "__main__":
    main()
