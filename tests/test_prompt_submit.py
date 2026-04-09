# tests/test_prompt_submit.py
import importlib.util
import json
import sys
import tempfile
import unittest
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
    tmp_path.mkdir(parents=True, exist_ok=True)
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
        "user_prompt": "Build a settings page with a form",
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

    # No output printed when no gaps and prompt is not fuzzy
    assert len(captured) == 0


def test_main_preserves_fuzzy_notice_when_no_gaps(tmp_path):
    """Fuzzy nudge should survive when skill config is readable but no gaps found."""
    hook_input = json.dumps({
        "user_prompt": "i want to add something",
        "cwd": str(tmp_path),
    })
    # Patch get_enabled_skill_names to return a full set (no gaps for this generic prompt)
    with patch.object(
        prompt_submit, "get_enabled_skill_names",
        return_value={"ui-ux-pro-max", "frontend-design", "writing-plans"},
    ):
        with patch("sys.stdin", io.StringIO(hook_input)):
            captured = []
            with patch("builtins.print", side_effect=lambda x: captured.append(x)):
                with pytest.raises(SystemExit):
                    prompt_submit.main()

    # Fuzzy note should still appear — no gaps were found to supersede it
    assert len(captured) == 1
    output = json.loads(captured[0])
    context = (
        output.get("hookSpecificOutput", {}).get("additionalContext")
        or output.get("additionalContext")
        or output.get("additional_context")
        or ""
    )
    assert "[Orch.] This looks like a vague prompt" in context


# ---------------------------------------------------------------------------
# read_brain_context
# ---------------------------------------------------------------------------

read_brain_context = prompt_submit.read_brain_context


class TestReadBrainContext(unittest.TestCase):
    def test_returns_none_when_no_brain(self):
        with tempfile.TemporaryDirectory() as d:
            result = read_brain_context(d)
            assert result is None

    def test_returns_context_with_bullets(self):
        with tempfile.TemporaryDirectory() as d:
            brain_dir = Path(d) / ".claude" / "orch"
            brain_dir.mkdir(parents=True)
            brain_content = (
                "# Project Brain\n"
                "<!-- git_head: abc123 -->\n"
                "<!-- llm_analysis: complete -->\n\n"
                "## Project Summary\n"
                "**Name:** my-app\n\n"
                "## Tech Stack\nPython, Flask\n\n"
                "## Decisions Log\n"
                "- Used JWT for auth\n"
                "<!-- add more decisions here -->\n"
                "- Postgres for storage\n"
            )
            (brain_dir / "brain.md").write_text(brain_content)
            result = read_brain_context(d)
            assert result is not None
            assert result["name"] == "my-app"
            assert result["stack"] == "Python, Flask"
            # Real bullets should be present
            assert any("JWT" in b for b in result["bullets"])
            assert any("Postgres" in b for b in result["bullets"])
            # The comment line should NOT appear as a bullet
            assert not any("add more decisions" in b for b in result["bullets"])


if __name__ == "__main__":
    unittest.main()
