#!/usr/bin/env python3
"""
SessionStart hook for Orch. plugin.

Runs init_setup.py if setup.md is missing or stale, then:
1. Creates or refreshes .claude/orch/brain.md via init_brain.py
2. Injects LLM analysis instruction if brain.md has llm_analysis: pending
3. Detects missing plugins (discover_tools.py) + pending setup items
4. Injects brain summary + setup summary + Orch usage guidance
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

_env_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("CURSOR_PLUGIN_ROOT")
PLUGIN_ROOT = Path(_env_root) if _env_root else Path(__file__).resolve().parent.parent
SKILL_DIR = PLUGIN_ROOT / "skills" / "orch"
INIT_SCRIPT = SKILL_DIR / "scripts" / "init_setup.py"
INIT_BRAIN_SCRIPT = SKILL_DIR / "scripts" / "init_brain.py"
DISCOVER_SCRIPT = SKILL_DIR / "scripts" / "discover_tools.py"
SETUP_MD = SKILL_DIR / "references" / "setup.md"


def run_script(script: Path, args: list[str]) -> None:
    """Run a Python script silently. Never raises — failure is non-blocking."""
    try:
        subprocess.run(
            ["python3", str(script)] + args,
            capture_output=True,
            timeout=15,
        )
    except Exception:
        pass


def read_brain_head(brain_md: Path) -> str | None:
    """Read stored git_head from brain.md comments."""
    try:
        match = re.search(r"<!--\s*git_head:\s*([a-f0-9]+)\s*-->", brain_md.read_text(encoding='utf-8'))
        return match.group(1) if match else None
    except Exception:
        return None


def read_llm_analysis_status(brain_md: Path) -> str:
    """Return 'pending', 'complete', or 'unknown'."""
    try:
        match = re.search(r"<!--\s*llm_analysis:\s*(\w+)\s*-->", brain_md.read_text(encoding='utf-8'))
        return match.group(1) if match else "unknown"
    except Exception:
        return "unknown"


def get_missing_tools(project_path: str) -> list[dict]:
    """Run discover_tools.py --json and return not-installed required/recommended items."""
    try:
        result = subprocess.run(
            ["python3", str(DISCOVER_SCRIPT), "--project-path", project_path, "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        items = json.loads(result.stdout)
        return [
            i for i in items
            if i.get("status") == "not_installed"
            and i.get("priority") in ("required", "recommended")
        ]
    except Exception:
        return []


def read_pending_setup(cwd: str) -> list[dict]:
    """Return pending items from .claude/orch/pending_setup.md."""
    pending_md = Path(cwd) / ".claude" / "orch" / "pending_setup.md"
    if not pending_md.exists():
        return []
    try:
        items = []
        in_table = False
        header_skipped = False
        for line in pending_md.read_text(encoding='utf-8').splitlines():
            if "## Pending Installation" in line:
                in_table = True
                continue
            if in_table and line.startswith("## "):
                break
            if in_table and line.startswith("|") and "---" not in line:
                if not header_skipped:
                    header_skipped = True
                    continue
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 2 and parts[0]:
                    items.append({
                        "plugin": parts[0],
                        "type": parts[1] if len(parts) > 1 else "plugin",
                        "priority": parts[2] if len(parts) > 2 else "recommended",
                    })
        return items
    except Exception:
        return []


def read_brain_summary(cwd: str) -> str:
    """Read brain.md and return a compact one-line + bullets summary."""
    brain_md = Path(cwd) / ".claude" / "orch" / "brain.md"
    if not brain_md.exists():
        return ""
    try:
        content = brain_md.read_text(encoding='utf-8')

        name_match = re.search(r"\*\*Name:\*\*\s*(.+)", content)
        project_name = name_match.group(1).strip() if name_match else Path(cwd).name

        stack_match = re.search(r"## Tech Stack\n([^\n#]+)", content)
        tech_str = stack_match.group(1).strip() if stack_match else "unknown"

        # Count active tasks
        active_count = 0
        tasks_md = Path(cwd) / ".claude" / "orch" / "tasks.md"
        if tasks_md.exists():
            in_active = False
            for line in tasks_md.read_text(encoding='utf-8').splitlines():
                if "## Active Tasks" in line:
                    in_active = True
                    continue
                if in_active and line.startswith("## "):
                    break
                if in_active and line.startswith("|") and not line.startswith("| Task") and "---" not in line:
                    active_count += 1

        # Last 3 decision bullets
        decisions_match = re.search(r"## Decisions Log\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        decision_bullets: list[str] = []
        if decisions_match:
            raw = decisions_match.group(1).strip()
            decision_bullets = [
                l.strip() for l in raw.splitlines()
                if l.strip().startswith("-") and "<!--" not in l
            ][-3:]

        parts = [f"Project: **{project_name}** | Stack: {tech_str} | Active tasks: {active_count}"]
        if decision_bullets:
            parts.append("Recent decisions:\n" + "\n".join(decision_bullets))
        return "\n".join(parts)
    except Exception:
        return ""


def read_setup_summary() -> str:
    """Read the key sections from setup.md for context injection."""
    if not SETUP_MD.exists():
        return ""
    try:
        lines = SETUP_MD.read_text(encoding='utf-8').splitlines()
        summary_lines = [l for l in lines[:100] if not l.startswith("<!--")]
        return "\n".join(summary_lines).strip()
    except Exception:
        return ""


def emit_context(context: str) -> None:
    """Output context in the correct format for the current platform."""
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


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        hook_input = {}

    cwd = hook_input.get("cwd") or os.getcwd()

    # Step 1: Run env setup (existing behaviour — init_setup.py)
    run_script(INIT_SCRIPT, ["--project-path", cwd])

    # Step 2: Brain initialization / git change detection
    # init_brain.py handles its own HEAD check and exits quickly if up-to-date
    brain_md = Path(cwd) / ".claude" / "orch" / "brain.md"
    run_script(INIT_BRAIN_SCRIPT, ["--cwd", cwd])

    context_parts: list[str] = []

    # Step 3: LLM analysis trigger (first session only)
    if brain_md.exists() and read_llm_analysis_status(brain_md) == "pending":
        context_parts.append(
            "[Orch] Brain skeleton ready. Before responding to the first task, "
            "read the Key Files listed in .claude/orch/brain.md and populate the "
            "Architecture and Conventions sections with component relationships, "
            "data flow patterns, naming conventions, and code style. "
            "Then change '<!-- llm_analysis: pending -->' to '<!-- llm_analysis: complete -->' "
            "in the brain.md header."
        )

    # Step 4: Setup gap detection (new gaps + previously deferred)
    missing_tools = get_missing_tools(cwd)
    pending_items = read_pending_setup(cwd)
    pending_names = {p["plugin"] for p in pending_items}
    all_setup_items = [t for t in missing_tools if t.get("plugin") not in pending_names] + pending_items

    if all_setup_items:
        items_str = ", ".join(
            f"{item.get('plugin', '?')} "
            f"({item.get('type', 'plugin')}, {item.get('priority', 'recommended')})"
            for item in all_setup_items
        )
        context_parts.append(
            f"[Orch] Setup incomplete. Pending: {items_str}.\n"
            'Say "set up tools" to install and configure them now, or "skip setup" to defer.'
        )

    # Step 5: Brain summary injection
    brain_summary = read_brain_summary(cwd)
    if brain_summary:
        context_parts.append(f"[Orch] {brain_summary}")

    # Build final context block
    setup_summary = read_setup_summary()
    if not context_parts and not setup_summary:
        sys.exit(0)

    sections: list[str] = ["<orch-context>", "Orch. is active.", ""]
    for part in context_parts:
        sections.append(part)
        sections.append("")
    if setup_summary:
        sections += ["Your Claude Code setup:", "", setup_summary, ""]
    sections.append(
        "Use the `orch` skill when planning tasks. "
        "Use `orch-planner` for living plan management. "
        "Use `orch-monitor` for token/context health guidance."
    )
    sections.append("</orch-context>")

    emit_context("\n".join(sections))
    sys.exit(0)


if __name__ == "__main__":
    main()
