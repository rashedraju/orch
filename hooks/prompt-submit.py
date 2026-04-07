#!/usr/bin/env python3
"""
UserPromptSubmit hook for session-coach plugin.

Detects fuzzy/vague prompts and injects a coaching nudge.
Also injects a resume reminder if an active session plan exists.
Always non-blocking (exit 0).
"""
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
            f"[Session Coach] Active plan detected. Current step: **{active_step}**. "
            "Say 'resume session' to pick up where you left off, or continue with your new prompt."
        )

    # Check for fuzzy prompt
    if prompt and is_fuzzy(prompt) and not active_step:
        notes.append(
            "[Session Coach] This looks like a vague prompt. "
            "For best results, try: \"Use session-coach to plan this: " + prompt + "\""
        )

    if notes:
        emit_context("\n\n".join(notes))

    sys.exit(0)


if __name__ == "__main__":
    main()
