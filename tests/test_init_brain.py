#!/usr/bin/env python3
"""Tests for init_brain.py"""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "orch" / "scripts"))
import init_brain


class TestGetProjectName(unittest.TestCase):
    def test_from_package_json(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "package.json").write_text('{"name": "my-app"}')
            assert init_brain.get_project_name(Path(d)) == "my-app"

    def test_falls_back_to_dir_name(self):
        with tempfile.TemporaryDirectory() as d:
            assert init_brain.get_project_name(Path(d)) == Path(d).name


class TestDetectTechStack(unittest.TestCase):
    def test_python_project(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "pyproject.toml").write_text("[tool.poetry]\nname = 'x'")
            stack = init_brain.detect_tech_stack(Path(d))
            assert "Python" in stack

    def test_react_project(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = '{"dependencies": {"react": "18.0.0", "typescript": "5.0.0"}}'
            Path(d, "package.json").write_text(pkg)
            Path(d, "tsconfig.json").write_text("{}")
            stack = init_brain.detect_tech_stack(Path(d))
            assert "TypeScript" in stack
            assert "React" in stack

    def test_empty_project(self):
        with tempfile.TemporaryDirectory() as d:
            stack = init_brain.detect_tech_stack(Path(d))
            assert stack == []


class TestFindKeyFiles(unittest.TestCase):
    def test_finds_existing_files(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "package.json").write_text("{}")
            Path(d, "README.md").write_text("# hi")
            found = init_brain.find_key_files(Path(d))
            assert "package.json" in found
            assert "README.md" in found

    def test_ignores_missing_files(self):
        with tempfile.TemporaryDirectory() as d:
            found = init_brain.find_key_files(Path(d))
            assert "Cargo.toml" not in found


class TestReadBrainHead(unittest.TestCase):
    def test_reads_head(self):
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d, "brain.md")
            brain.write_text("# Project Brain\n<!-- git_head: abc123 -->\n")
            assert init_brain.read_brain_head(brain) == "abc123"

    def test_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d, "brain.md")
            brain.write_text("# Project Brain\n")
            assert init_brain.read_brain_head(brain) is None


class TestReadLlmAnalysisStatus(unittest.TestCase):
    def test_reads_pending(self):
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d, "brain.md")
            brain.write_text("<!-- llm_analysis: pending -->")
            assert init_brain.read_llm_analysis_status(brain) == "pending"

    def test_reads_complete(self):
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d, "brain.md")
            brain.write_text("<!-- llm_analysis: complete -->")
            assert init_brain.read_llm_analysis_status(brain) == "complete"


class TestBuildBrainSkeleton(unittest.TestCase):
    def test_creates_valid_brain_md(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            content = init_brain.build_brain_skeleton(
                project_path=p,
                git_head="abc123",
                tech_stack=["Python"],
                key_files=["main.py"],
                dir_structure="main.py\ntests/",
                file_dist={".py": 5},
                recommended_skills=["superpowers", "context7"],
            )
            assert "<!-- git_head: abc123 -->" in content
            assert "<!-- llm_analysis: pending -->" in content
            assert "Python" in content
            assert "main.py" in content
            assert "## Architecture" in content
            assert "## Conventions" in content
            assert "## Decisions Log" in content


class TestUpdateStructuralSections(unittest.TestCase):
    def test_updates_tech_stack_preserves_decisions(self):
        original = (
            "# Project Brain\n"
            "<!-- git_head: old123 -->\n"
            "<!-- last_scan: 2025-01-01 -->\n"
            "<!-- llm_analysis: complete -->\n\n"
            "## Project Summary\nOld name\n\n"
            "## Tech Stack\nOld stack\n\n"
            "## Key Files\n- old.py\n\n"
            "## File Distribution\n- .py: 1\n\n"
            "## Directory Map\n```\nold/\n```\n\n"
            "## Architecture\nMy architecture notes\n\n"
            "## Conventions\nMy conventions\n\n"
            "## Decisions Log\n- Used JWT\n\n"
            "## Open Questions\n\n"
            "## Recommended Skills\n- `old-skill`\n"
        )
        updated = init_brain.update_structural_sections(
            existing_content=original,
            project_path=Path("/tmp/proj"),
            git_head="new456",
            tech_stack=["Go"],
            key_files=["main.go"],
            dir_structure="main.go",
            file_dist={".go": 3},
            recommended_skills=["superpowers"],
        )
        # Structural sections updated
        assert "<!-- git_head: new456 -->" in updated
        assert "Go" in updated
        assert "main.go" in updated
        # Knowledge sections preserved
        assert "My architecture notes" in updated
        assert "My conventions" in updated
        assert "- Used JWT" in updated
        # llm_analysis flag preserved (not changed by structural scan)
        assert "<!-- llm_analysis: complete -->" in updated


if __name__ == "__main__":
    unittest.main()
