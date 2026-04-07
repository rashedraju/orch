#!/usr/bin/env python3
"""
PreCompact hook for session-coach plugin.

Extracts the current plan state from session.md and injects a compact
summary that will survive context compaction, ensuring the session can
resume seamlessly after /compact.
"""
import json
import os
import re
import sys
from pathlib import Path


def extract_compact_state(cwd: str) -> str | None:
    """Extract a compact summary of the active plan state."""
    session_md = Path(cwd) / ".claude" / "session.md"
    if not session_md.exists():
        return None
    try:
        content = session_md.read_text()

        task_match = re.search(r"^# session: (.+)", content, re.MULTILINE)
        status_match = re.search(r"^status: (.+)", content, re.MULTILINE)
        next_match = re.search(
            r"### \[NEXT\] Step (\d+) — (.+?)\n(.*?)(?=###|\Z)",
            content,
            re.DOTALL,
        )
        snapshot_match = re.search(
            r"## context snapshot\n(.*?)(?=##|\Z)",
            content,
            re.DOTALL,
        )

        if not (task_match and next_match):
            return None

        task = task_match.group(1).strip()
        status = status_match.group(1).strip() if status_match else "in-progress"
        step_num = next_match.group(1)
        step_name = next_match.group(2).strip()

        # Extract the prompt from the [NEXT] step block
        step_body = next_match.group(3)
        prompt_match = re.search(r"prompt:\n-{20,}\n(.*?)\n-{20,}", step_body, re.DOTALL)
        step_prompt = prompt_match.group(1).strip()[:300] if prompt_match else ""

        # Extract last 3 context snapshot bullets
        snapshot_bullets = []
        if snapshot_match:
            bullets = re.findall(r"^[-•]\s+(.+)", snapshot_match.group(1), re.MULTILINE)
            snapshot_bullets = bullets[-3:]

        parts = [
            f"SESSION COACH STATE (preserved across compaction)",
            f"Task: {task} | Status: {status}",
            f"Next: Step {step_num} — {step_name}",
        ]
        if snapshot_bullets:
            parts.append("Context: " + " · ".join(snapshot_bullets))
        if step_prompt:
            parts.append(f"Current prompt:\n{step_prompt}")
        parts.append(
            f"Plan file: .claude/session.md — read it to resume. "
            "Say 'resume session' to continue from the current step."
        )

        return "\n".join(parts)

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
                "hookEventName": "PreCompact",
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
    compact_state = extract_compact_state(cwd)

    if compact_state:
        emit_context(compact_state)

    sys.exit(0)


if __name__ == "__main__":
    main()
