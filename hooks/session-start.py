#!/usr/bin/env python3
"""
SessionStart hook for session-coach plugin.

Runs init_setup.py if setup.md is missing or stale, then injects a compact
summary of the user's Claude Code configuration into every session automatically.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

_env_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("CURSOR_PLUGIN_ROOT")
PLUGIN_ROOT = Path(_env_root) if _env_root else Path(__file__).resolve().parent.parent
SKILL_DIR = PLUGIN_ROOT / "skills" / "session-coach"
INIT_SCRIPT = SKILL_DIR / "scripts" / "init_setup.py"
SETUP_MD = SKILL_DIR / "references" / "setup.md"


def escape_for_json(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
    )


def run_init(project_path: str) -> None:
    """Run init_setup.py silently. Never raises — failure is non-blocking."""
    try:
        subprocess.run(
            ["python3", str(INIT_SCRIPT), "--project-path", project_path],
            capture_output=True,
            timeout=15,
        )
    except Exception:
        pass


def read_setup_summary() -> str:
    """Read the key sections from setup.md for context injection."""
    if not SETUP_MD.exists():
        return ""
    try:
        content = SETUP_MD.read_text()
        lines = content.splitlines()
        # Extract up to the first 80 lines (models, plugins, skills, MCPs)
        # Skip the HTML comment header lines
        summary_lines = [
            line for line in lines[:100]
            if not line.startswith("<!--")
        ]
        return "\n".join(summary_lines).strip()
    except Exception:
        return ""


def emit_context(context: str) -> None:
    """Output context in the correct format for the current platform."""
    escaped = escape_for_json(context)
    cursor_root = os.environ.get("CURSOR_PLUGIN_ROOT", "")
    copilot_cli = os.environ.get("COPILOT_CLI", "")
    claude_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")

    if cursor_root:
        print(json.dumps({"additional_context": context}))
    elif claude_root and not copilot_cli:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }))
    else:
        print(json.dumps({"additionalContext": context}))


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        hook_input = {}

    cwd = hook_input.get("cwd") or os.getcwd()

    # Run init if setup.md is missing or stale
    run_init(cwd)

    summary = read_setup_summary()
    if not summary:
        sys.exit(0)

    context = (
        "<session-coach-context>\n"
        "Session Coach is active. Your Claude Code setup:\n\n"
        f"{summary}\n\n"
        "Use the `session-coach` skill when planning tasks. "
        "Use `coach-planner` for living plan management. "
        "Use `coach-monitor` for token/context health guidance.\n"
        "</session-coach-context>"
    )

    emit_context(context)
    sys.exit(0)


if __name__ == "__main__":
    main()
