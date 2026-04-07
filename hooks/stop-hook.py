#!/usr/bin/env python3
"""
Stop hook for session-coach plugin.

Checks if an active session plan has incomplete steps before the session ends.
Injects a warning if stopping mid-plan. Always advisory, never blocks.
"""
import json
import os
import re
import sys
from pathlib import Path


def get_plan_status(cwd: str) -> dict | None:
    """Return plan info if session.md exists with an incomplete [NEXT] step."""
    session_md = Path(cwd) / ".claude" / "session.md"
    if not session_md.exists():
        return None
    try:
        content = session_md.read_text()
        # Look for incomplete [NEXT] step
        next_match = re.search(r"### \[NEXT\] Step \d+ — (.+)", content)
        if not next_match:
            return None
        task_match = re.search(r"^# session: (.+)", content, re.MULTILINE)
        return {
            "task": task_match.group(1).strip() if task_match else "unknown",
            "next_step": next_match.group(1).strip(),
        }
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
                "hookEventName": "Stop",
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
    plan = get_plan_status(cwd)

    if plan:
        context = (
            f"[Session Coach] ⚠️ Active plan has incomplete steps.\n"
            f"Task: {plan['task']}\n"
            f"Next step: {plan['next_step']}\n\n"
            "Before ending, consider:\n"
            "- Noting your progress in `.claude/session.md`\n"
            "- Running the `finishing-a-development-branch` skill if work is complete\n"
            "- Or just end — the plan will resume automatically next session."
        )
        emit_context(context)

    sys.exit(0)


if __name__ == "__main__":
    main()
