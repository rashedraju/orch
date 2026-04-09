# Orch v2 Intelligence Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent project memory (brain.md, history.md, tasks.md, pending_setup.md), one-time LLM codebase analysis, and universal prompt routing to the Orch plugin.

**Architecture:** A new `init_brain.py` Python script creates and refreshes a structural brain skeleton per project. The SessionStart hook runs it, detects setup gaps, and injects rich project context on every session. The UserPromptSubmit hook injects the Orch complexity gate instruction on every prompt when brain.md exists. The `orch` and `orch-planner` skill definitions are updated to maintain the hub files across task lifecycles.

**Tech Stack:** Python 3.8+ (stdlib only), Markdown

---

## File Map

| File | Action |
|------|--------|
| `skills/orch/scripts/init_brain.py` | Create — structural codebase scanner |
| `tests/test_init_brain.py` | Create — unit tests for init_brain.py |
| `hooks/session-start.py` | Modify — add brain init, change detection, LLM trigger, setup gaps |
| `hooks/prompt-submit.py` | Modify — add project context + routing instruction |
| `skills/orch/SKILL.md` | Modify — LLM analysis phase, interactive setup, tasks.md management |
| `skills/orch-planner/SKILL.md` | Modify — brain.md + history.md + tasks.md updates |

---

### Task 1: Create `skills/orch/scripts/init_brain.py`

**Files:**
- Create: `skills/orch/scripts/init_brain.py`
- Create: `tests/test_init_brain.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_init_brain.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/orch
python3 -m pytest tests/test_init_brain.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'init_brain'`

- [ ] **Step 3: Create `skills/orch/scripts/init_brain.py`**

```python
#!/usr/bin/env python3
"""
Scans the project codebase and writes (or refreshes) .claude/orch/brain.md.

Creates a structural brain skeleton on first run. On subsequent runs, only
updates the structural sections if the git HEAD has changed. Non-destructive:
knowledge sections (Architecture, Conventions, Decisions Log, Open Questions)
are never overwritten.

Usage:
    python3 init_brain.py [--cwd /path/to/project] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BRAIN_RELATIVE_PATH = ".claude/orch/brain.md"

EXCLUDED_DIRS = {
    ".git", "node_modules", "vendor", ".venv", "venv", "env",
    "dist", "build", "__pycache__", ".next", ".nuxt", "coverage",
    ".cache", "tmp", "temp", "logs",
}

KEY_FILE_CANDIDATES = [
    "package.json", "composer.json", "pyproject.toml", "requirements.txt",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "README.md",
    "main.py", "app.py", "server.py", "wsgi.py", "manage.py",
    "index.js", "index.ts", "app.js", "app.ts", "server.js", "server.ts",
    "main.go", "cmd/main.go", "src/main.rs",
    "Dockerfile", "docker-compose.yml", ".env.example",
]

TECH_TO_SKILLS: dict[str, list[str]] = {
    "TypeScript": ["ts-check", "context7"],
    "React": ["ui-ux-pro-max", "frontend-design", "context7"],
    "Next.js": ["frontend-design", "context7"],
    "Vue.js": ["frontend-design", "context7"],
    "PHP/Laravel": ["laravel-specialist", "php-pro", "context7"],
    "PHP": ["php-pro", "context7"],
    "Python": ["context7"],
    "Rust": ["context7"],
    "Go": ["context7"],
    "Java": ["context7"],
    "JavaScript": ["context7"],
    "GitHub Actions": [],
}

ALWAYS_RECOMMENDED = ["superpowers", "context7"]


def get_git_head(project_path: Path) -> str | None:
    """Return current git HEAD SHA, or None if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def read_brain_head(brain_md: Path) -> str | None:
    """Read the stored git_head value from brain.md comments."""
    try:
        content = brain_md.read_text()
        match = re.search(r"<!--\s*git_head:\s*([a-f0-9]+)\s*-->", content)
        return match.group(1) if match else None
    except Exception:
        return None


def read_llm_analysis_status(brain_md: Path) -> str:
    """Return 'pending', 'complete', or 'unknown'."""
    try:
        content = brain_md.read_text()
        match = re.search(r"<!--\s*llm_analysis:\s*(\w+)\s*-->", content)
        return match.group(1) if match else "unknown"
    except Exception:
        return "unknown"


def git_head_changed(brain_md: Path, project_path: Path) -> bool:
    """Return True if git HEAD differs from what's stored in brain.md."""
    stored = read_brain_head(brain_md)
    current = get_git_head(project_path)
    if stored is None or current is None:
        return True
    return stored != current


def get_project_name(project_path: Path) -> str:
    """Return project name from manifest files, falling back to directory name."""
    for manifest, pattern in [
        ("package.json", None),
        ("pyproject.toml", r'name\s*=\s*["\']([^"\']+)["\']'),
        ("Cargo.toml", r'name\s*=\s*["\']([^"\']+)["\']'),
    ]:
        f = project_path / manifest
        if not f.exists():
            continue
        try:
            if manifest == "package.json":
                data = json.loads(f.read_text())
                if data.get("name"):
                    return data["name"]
            else:
                m = re.search(pattern, f.read_text())
                if m:
                    return m.group(1)
        except Exception:
            pass
    return project_path.name


def detect_tech_stack(project_path: Path) -> list[str]:
    """Return list of detected technology names."""
    stack: list[str] = []

    pkg = project_path / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            dep_names = set(all_deps.keys())

            has_ts = (project_path / "tsconfig.json").exists() or "typescript" in dep_names
            if has_ts:
                stack.append("TypeScript")
            else:
                stack.append("JavaScript")
            if "react" in dep_names or "react-dom" in dep_names:
                stack.append("React")
            if "next" in dep_names:
                stack.append("Next.js")
            if "vue" in dep_names or "@vue/core" in dep_names:
                stack.append("Vue.js")
        except Exception:
            pass

    if (project_path / "composer.json").exists():
        try:
            data = json.loads((project_path / "composer.json").read_text())
            requires = {**data.get("require", {}), **data.get("require-dev", {})}
            if any("laravel" in k.lower() for k in requires):
                stack.append("PHP/Laravel")
            else:
                stack.append("PHP")
        except Exception:
            stack.append("PHP")

    if (project_path / "pyproject.toml").exists() or (project_path / "requirements.txt").exists():
        stack.append("Python")
    if (project_path / "Cargo.toml").exists():
        stack.append("Rust")
    if (project_path / "go.mod").exists():
        stack.append("Go")
    if (project_path / "pom.xml").exists():
        stack.append("Java")
    if (project_path / ".github" / "workflows").exists():
        stack.append("GitHub Actions")

    return stack


def find_key_files(project_path: Path) -> list[str]:
    """Return list of key file candidates that exist in the project."""
    return [f for f in KEY_FILE_CANDIDATES if (project_path / f).exists()]


def count_files_by_extension(project_path: Path) -> dict[str, int]:
    """Count source files by extension, top 10, ignoring noise dirs."""
    counts: Counter = Counter()
    try:
        for root, dirs, files in os.walk(str(project_path)):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            for f in files:
                ext = Path(f).suffix.lower()
                if ext:
                    counts[ext] += 1
    except Exception:
        pass
    return dict(counts.most_common(10))


def scan_directory_structure(project_path: Path) -> str:
    """Return formatted top-2-level directory tree."""
    lines: list[str] = []
    try:
        for item in sorted(project_path.iterdir()):
            if item.name.startswith(".") and item.name not in {".github", ".claude"}:
                continue
            if item.name in EXCLUDED_DIRS:
                continue
            if item.is_dir():
                lines.append(f"{item.name}/")
                try:
                    for sub in sorted(item.iterdir()):
                        if sub.name in EXCLUDED_DIRS or sub.name.startswith("."):
                            continue
                        suffix = "/" if sub.is_dir() else ""
                        lines.append(f"  {sub.name}{suffix}")
                except PermissionError:
                    pass
            else:
                lines.append(item.name)
    except Exception:
        pass
    return "\n".join(lines) if lines else "_no files detected_"


def get_recommended_skills(tech_stack: list[str]) -> list[str]:
    """Return deduplicated list of recommended skills for the detected tech."""
    skills = list(ALWAYS_RECOMMENDED)
    for tech in tech_stack:
        for skill in TECH_TO_SKILLS.get(tech, []):
            if skill not in skills:
                skills.append(skill)
    return skills


def build_brain_skeleton(
    project_path: Path,
    git_head: str | None,
    tech_stack: list[str],
    key_files: list[str],
    dir_structure: str,
    file_dist: dict[str, int],
    recommended_skills: list[str],
) -> str:
    """Build a full brain.md skeleton for a project being scanned for the first time."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    head_str = git_head or "unknown"
    project_name = get_project_name(project_path)
    tech_str = ", ".join(tech_stack) if tech_stack else "Not detected"
    primary_lang = tech_stack[0] if tech_stack else "Unknown"
    key_files_str = "\n".join(f"- `{f}`" for f in key_files) if key_files else "- _none detected_"
    file_dist_str = "\n".join(f"- `{ext}`: {count} files" for ext, count in file_dist.items()) or "- _not scanned_"
    skills_str = "\n".join(f"- `{s}`" for s in recommended_skills)

    return f"""# Project Brain
<!-- git_head: {head_str} -->
<!-- last_scan: {now} -->
<!-- llm_analysis: pending -->

## Project Summary
**Name:** {project_name}
**Description:** <!-- Fill in: one-line description of what this project does -->
**Primary Language:** {primary_lang}

## Tech Stack
{tech_str}

## Key Files
{key_files_str}

## File Distribution
{file_dist_str}

## Directory Map
```
{dir_structure}
```

## Architecture
<!-- LLM-populated on first session: component relationships, data flow, key patterns -->

## Conventions
<!-- LLM-populated on first session: naming, file organization, test style, code style -->

## Decisions Log
<!-- Appended by orch-planner: date, decision, rationale -->

## Open Questions
<!-- Added manually or by orch skill when uncertainty is noted -->

## Recommended Skills
{skills_str}
"""


def update_structural_sections(
    existing_content: str,
    project_path: Path,
    git_head: str | None,
    tech_stack: list[str],
    key_files: list[str],
    dir_structure: str,
    file_dist: dict[str, int],
    recommended_skills: list[str],
) -> str:
    """Update only structural sections in existing brain.md. Knowledge sections are untouched."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    head_str = git_head or "unknown"
    project_name = get_project_name(project_path)
    tech_str = ", ".join(tech_stack) if tech_stack else "Not detected"
    primary_lang = tech_stack[0] if tech_stack else "Unknown"
    key_files_str = "\n".join(f"- `{f}`" for f in key_files) if key_files else "- _none detected_"
    file_dist_str = "\n".join(f"- `{ext}`: {count} files" for ext, count in file_dist.items()) or "- _not scanned_"
    skills_str = "\n".join(f"- `{s}`" for s in recommended_skills)

    content = existing_content

    # Update metadata comments (do NOT touch llm_analysis)
    content = re.sub(r"<!--\s*git_head:[^-]*-->", f"<!-- git_head: {head_str} -->", content)
    content = re.sub(r"<!--\s*last_scan:[^-]*-->", f"<!-- last_scan: {now} -->", content)

    def replace_section(name: str, new_body: str) -> None:
        nonlocal content
        pattern = rf"(## {re.escape(name)}\n).*?(?=\n## |\Z)"
        content = re.sub(
            pattern,
            lambda m: m.group(1) + new_body + "\n",
            content,
            flags=re.DOTALL,
        )

    replace_section(
        "Project Summary",
        f"**Name:** {project_name}\n"
        f"**Description:** <!-- Fill in: one-line description of what this project does -->\n"
        f"**Primary Language:** {primary_lang}",
    )
    replace_section("Tech Stack", tech_str)
    replace_section("Key Files", key_files_str)
    replace_section("File Distribution", file_dist_str)
    replace_section("Directory Map", f"```\n{dir_structure}\n```")
    replace_section("Recommended Skills", skills_str)

    return content


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or refresh .claude/orch/brain.md")
    parser.add_argument("--cwd", default=None, help="Project root (default: current directory)")
    parser.add_argument("--force", action="store_true", help="Force structural re-scan even if HEAD unchanged")
    args = parser.parse_args()

    project_path = Path(args.cwd).resolve() if args.cwd else Path.cwd().resolve()
    brain_md = project_path / BRAIN_RELATIVE_PATH

    # Determine action
    if not brain_md.exists():
        action = "create"
    elif args.force or git_head_changed(brain_md, project_path):
        action = "update"
    else:
        print("Brain is current (git HEAD unchanged). Use --force to re-scan.")
        sys.exit(0)

    git_head = get_git_head(project_path)
    tech_stack = detect_tech_stack(project_path)
    key_files = find_key_files(project_path)
    dir_structure = scan_directory_structure(project_path)
    file_dist = count_files_by_extension(project_path)
    recommended_skills = get_recommended_skills(tech_stack)

    brain_md.parent.mkdir(parents=True, exist_ok=True)

    if action == "create":
        brain_md.write_text(
            build_brain_skeleton(project_path, git_head, tech_stack, key_files,
                                 dir_structure, file_dist, recommended_skills)
        )
        print(f"✓ brain.md created at {brain_md}")
        print(f"  Tech stack: {', '.join(tech_stack) if tech_stack else 'none detected'}")
        print(f"  Key files: {len(key_files)}")
        print(f"  llm_analysis: pending")
    else:
        brain_md.write_text(
            update_structural_sections(brain_md.read_text(), project_path, git_head,
                                       tech_stack, key_files, dir_structure,
                                       file_dist, recommended_skills)
        )
        print(f"✓ brain.md structural sections refreshed at {brain_md}")
        print(f"  Tech stack: {', '.join(tech_stack) if tech_stack else 'none detected'}")
        print(f"  Knowledge sections preserved")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_init_brain.py -v
```

Expected: all tests pass, no failures.

- [ ] **Step 5: Smoke-test the script on this repo**

```bash
cd /path/to/orch
python3 skills/orch/scripts/init_brain.py --cwd .
```

Expected output:
```
✓ brain.md created at /path/to/orch/.claude/orch/brain.md
  Tech stack: Python
  Key files: 3
  llm_analysis: pending
```

Then verify the file:
```bash
cat .claude/orch/brain.md | head -20
```

Expected: `<!-- git_head: <sha> -->`, `<!-- llm_analysis: pending -->`, Python in Tech Stack.

- [ ] **Step 6: Test --force flag**

```bash
python3 skills/orch/scripts/init_brain.py --cwd . --force
```

Expected: `✓ brain.md structural sections refreshed`

- [ ] **Step 7: Test no-op when HEAD unchanged**

```bash
python3 skills/orch/scripts/init_brain.py --cwd .
```

Expected: `Brain is current (git HEAD unchanged). Use --force to re-scan.`

- [ ] **Step 8: Commit**

```bash
git add skills/orch/scripts/init_brain.py tests/test_init_brain.py
git commit -m "feat: add init_brain.py — structural codebase scanner for intelligence hub"
```

---

### Task 2: Enhance `hooks/session-start.py`

**Files:**
- Modify: `hooks/session-start.py`

- [ ] **Step 1: Write the complete new session-start.py**

Replace the entire contents of `hooks/session-start.py` with:

```python
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


def escape_for_json(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
    )


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


def get_git_head(project_path: str) -> str | None:
    """Return current git HEAD SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def read_brain_head(brain_md: Path) -> str | None:
    """Read stored git_head from brain.md comments."""
    try:
        match = re.search(r"<!--\s*git_head:\s*([a-f0-9]+)\s*-->", brain_md.read_text())
        return match.group(1) if match else None
    except Exception:
        return None


def read_llm_analysis_status(brain_md: Path) -> str:
    """Return 'pending', 'complete', or 'unknown'."""
    try:
        match = re.search(r"<!--\s*llm_analysis:\s*(\w+)\s*-->", brain_md.read_text())
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
            timeout=10,
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
        for line in pending_md.read_text().splitlines():
            if "## Pending Installation" in line:
                in_table = True
                continue
            if in_table and line.startswith("## "):
                break
            if in_table and line.startswith("|") and not line.startswith("| Item") and "---" not in line:
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
        content = brain_md.read_text()

        name_match = re.search(r"\*\*Name:\*\*\s*(.+)", content)
        project_name = name_match.group(1).strip() if name_match else Path(cwd).name

        stack_match = re.search(r"## Tech Stack\n([^\n#]+)", content)
        tech_str = stack_match.group(1).strip() if stack_match else "unknown"

        # Count active tasks
        active_count = 0
        tasks_md = Path(cwd) / ".claude" / "orch" / "tasks.md"
        if tasks_md.exists():
            in_active = False
            for line in tasks_md.read_text().splitlines():
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
            if raw and "<!--" not in raw:
                decision_bullets = [l.strip() for l in raw.splitlines() if l.strip().startswith("-")][-3:]

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
        lines = SETUP_MD.read_text().splitlines()
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
    brain_md = Path(cwd) / ".claude" / "orch" / "brain.md"
    if not brain_md.exists():
        run_script(INIT_BRAIN_SCRIPT, ["--cwd", cwd])
    else:
        stored = read_brain_head(brain_md)
        current = get_git_head(cwd)
        if stored and current and stored != current:
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
            f"{item.get('plugin', item.get('name', '?'))} "
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
```

- [ ] **Step 2: Test — no brain.md, fresh project**

```bash
mkdir -p /tmp/test-orch-project
echo '{"cwd": "/tmp/test-orch-project"}' | python3 hooks/session-start.py
```

Expected: JSON output containing `[Orch] Brain skeleton ready` (LLM analysis trigger) and/or `[Orch] Setup incomplete`.

- [ ] **Step 3: Test — brain.md exists, HEAD unchanged**

```bash
python3 skills/orch/scripts/init_brain.py --cwd /tmp/test-orch-project
echo '{"cwd": "/tmp/test-orch-project"}' | python3 hooks/session-start.py
```

Expected: JSON output does NOT contain `Brain skeleton ready` (llm_analysis pending was just set... wait, it IS pending on fresh create). To test the "no re-trigger" path, manually edit brain.md to set `llm_analysis: complete`, then re-run:

```bash
sed -i 's/llm_analysis: pending/llm_analysis: complete/' /tmp/test-orch-project/.claude/orch/brain.md
echo '{"cwd": "/tmp/test-orch-project"}' | python3 hooks/session-start.py
```

Expected: Output does NOT contain `[Orch] Brain skeleton ready`.

- [ ] **Step 4: Commit**

```bash
git add hooks/session-start.py
git commit -m "feat: enhance session-start hook with brain init, LLM trigger, setup gaps"
```

---

### Task 3: Enhance `hooks/prompt-submit.py`

**Files:**
- Modify: `hooks/prompt-submit.py`

- [ ] **Step 1: Add brain context functions to prompt-submit.py**

Insert these two functions BEFORE the `is_fuzzy` function (after line 126, before `def is_fuzzy`):

```python
def read_brain_context(cwd: str) -> dict | None:
    """Read brain.md and return project context dict, or None if brain doesn't exist."""
    brain_md = Path(cwd) / ".claude" / "orch" / "brain.md"
    if not brain_md.exists():
        return None
    try:
        import re as _re
        content = brain_md.read_text()

        name_match = _re.search(r"\*\*Name:\*\*\s*(.+)", content)
        project_name = name_match.group(1).strip() if name_match else Path(cwd).name

        stack_match = _re.search(r"## Tech Stack\n([^\n#]+)", content)
        tech_str = stack_match.group(1).strip() if stack_match else "unknown"

        # Up to 3 context bullets from Decisions Log or Conventions
        bullets: list[str] = []
        for section in ("Decisions Log", "Conventions"):
            sec_match = _re.search(rf"## {section}\n(.*?)(?=\n## |\Z)", content, _re.DOTALL)
            if sec_match:
                raw = sec_match.group(1).strip()
                if raw and "<!--" not in raw:
                    for line in raw.splitlines():
                        if line.strip().startswith("-") and len(bullets) < 3:
                            bullets.append(line.strip())

        return {"name": project_name, "stack": tech_str, "bullets": bullets}
    except Exception:
        return None


def get_active_task_count(cwd: str) -> int:
    """Count active tasks from .claude/orch/tasks.md."""
    tasks_md = Path(cwd) / ".claude" / "orch" / "tasks.md"
    if not tasks_md.exists():
        return 0
    try:
        count = 0
        in_active = False
        for line in tasks_md.read_text().splitlines():
            if "## Active Tasks" in line:
                in_active = True
                continue
            if in_active and line.startswith("## "):
                break
            if in_active and line.startswith("|") and not line.startswith("| Task") and "---" not in line:
                count += 1
        return count
    except Exception:
        return 0
```

- [ ] **Step 2: Update the `main()` function in prompt-submit.py**

Replace the existing `main()` function (lines 172–215) with:

```python
def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    prompt = hook_input.get("user_prompt", "").strip()
    cwd = hook_input.get("cwd") or os.getcwd()

    notes = []

    # Inject project context + complexity gate routing (when brain exists)
    brain_ctx = read_brain_context(cwd)
    if brain_ctx:
        active_tasks = get_active_task_count(cwd)
        header = (
            f"[ORCH] Project: {brain_ctx['name']} | "
            f"Stack: {brain_ctx['stack']} | "
            f"Active tasks: {active_tasks}"
        )
        bullets_str = ""
        if brain_ctx["bullets"]:
            bullets_str = "\nContext: " + " | ".join(brain_ctx["bullets"])

        routing = (
            "\n\nFor any implementation task, classify before responding:\n"
            "- Quick (≤2 steps, single file): answer directly\n"
            "- Standard/Complex: create/update .claude/session.md, route to appropriate skills\n"
            "Consult .claude/orch/brain.md for project conventions and prior decisions."
        )
        notes.append(header + bullets_str + routing)

    # Check for active plan (existing behaviour)
    active_step = get_active_plan_step(cwd)
    if active_step:
        notes.append(
            f"[Orch.] Active plan detected. Current step: **{active_step}**. "
            "Say 'resume session' to pick up where you left off, or continue with your new prompt."
        )

    # Check for fuzzy prompt (existing behaviour)
    if prompt and is_fuzzy(prompt) and not active_step:
        notes.append(
            "[Orch.] This looks like a vague prompt. "
            'For best results, try: "Use orch to plan this: ' + prompt + '"'
        )

    # Check for skill gaps (existing behaviour)
    if prompt and not active_step:
        enabled_skills = get_enabled_skill_names()
        if enabled_skills is not None:
            gaps = detect_skill_gaps(prompt, enabled_skills)
            if gaps:
                notes = [n for n in notes if not n.startswith("[Orch.] This looks like a vague")]
                notes.append(format_gap_notice(gaps))

    if notes:
        emit_context("\n\n".join(notes))

    sys.exit(0)
```

- [ ] **Step 3: Test — no brain.md (existing behaviour unchanged)**

```bash
echo '{"cwd": "/tmp/no-brain", "user_prompt": "i want to add something"}' | python3 hooks/prompt-submit.py
```

Expected: JSON with fuzzy nudge, no `[ORCH]` routing block.

- [ ] **Step 4: Test — brain.md exists**

```bash
echo '{"cwd": "/tmp/test-orch-project", "user_prompt": "add a login page"}' | python3 hooks/prompt-submit.py
```

Expected: JSON output contains `[ORCH] Project:` header and the routing instruction.

- [ ] **Step 5: Test — brain.md exists, active plan in session.md**

```bash
mkdir -p /tmp/test-orch-project/.claude
cat > /tmp/test-orch-project/.claude/session.md << 'EOF'
# session: Add login
status: in-progress
## steps
### [NEXT] Step 1 — Create login form
EOF
echo '{"cwd": "/tmp/test-orch-project", "user_prompt": "now add logout"}' | python3 hooks/prompt-submit.py
```

Expected: Both `[ORCH]` routing block AND `[Orch.] Active plan detected` appear in output.

- [ ] **Step 6: Commit**

```bash
git add hooks/prompt-submit.py
git commit -m "feat: inject project context and complexity gate routing in prompt-submit hook"
```

---

### Task 4: Update `skills/orch/SKILL.md`

**Files:**
- Modify: `skills/orch/SKILL.md`

- [ ] **Step 1: Add Intelligence Hub section after the Setup Reference section**

Insert the following block AFTER the `## Setup Reference` section (after line 17, before `## Tool Discovery & Installation`):

```markdown
## Intelligence Hub

The project brain lives at `.claude/orch/` in the user's project root:
- `brain.md` — project architecture, conventions, decisions, recommended skills
- `history.md` — append-only task execution log
- `tasks.md` — active and recently completed task registry
- `pending_setup.md` — deferred setup items (declined plugins/MCPs)

**Read brain.md at the start of every Standard/Complex task** to check existing conventions and prior decisions before planning.

---
```

- [ ] **Step 2: Add LLM analysis phase instructions**

Insert the following block AFTER the `## Intelligence Hub` section (before `## Tool Discovery & Installation`):

```markdown
## Brain Analysis Phase (first session only)

**Triggered automatically** when `session-start.py` injects the `[Orch] Brain skeleton ready` notice (i.e., `brain.md` has `llm_analysis: pending`).

Before responding to any task in that session:

1. Read the Key Files listed in `.claude/orch/brain.md`
2. For each key file, briefly scan: component purpose, how it connects to others, naming patterns, test approach
3. Write concise findings to brain.md:
   - **Architecture section**: bullet-form component relationships and data flow
   - **Conventions section**: naming style, file organisation, test patterns, code style
4. Update the header: change `<!-- llm_analysis: pending -->` to `<!-- llm_analysis: complete -->`
5. Confirm to the user: "Brain analysis complete. Project context saved to .claude/orch/brain.md."

This phase runs **once per project**. On subsequent sessions, `llm_analysis: complete` means skip this phase entirely.

To re-run: say "refresh brain" → runs `init_brain.py --force` and resets `llm_analysis: pending`.

---
```

- [ ] **Step 3: Replace the existing Tool Discovery & Installation section**

Replace the existing `## Tool Discovery & Installation` section (lines 28–40 of original SKILL.md) with:

```markdown
## Tool Setup ("set up tools")

**Triggered when** the user says "set up tools" (after `session-start.py` injects the setup gap notice).

Read setup gap list:
```bash
python scripts/discover_tools.py --project-path <cwd> --json
```
Also read `.claude/orch/pending_setup.md` if it exists (previously deferred items).

For each item **in order by priority** (required first, then recommended):

**Plugin installation:**
```bash
python scripts/install_plugin.py --plugin <name> --marketplace claude-plugins-official
```
Report: "`<name>` installed ✓" or "`<name>` failed: <reason>".

**MCP configuration:**
1. Add the MCP entry to the project's `.mcp.json` (create if missing):
   ```json
   { "mcpServers": { "<name>": { "command": "<cmd>", "args": [...] } } }
   ```
2. If auth is required, output the exact command and pause:
   ```
   [Orch] MCP <name> added to config. Auth required — please run:
   <exact auth command>
   Then say "auth done" to continue setup.
   ```
   Wait for "auth done" before moving to the next item.

**On decline** (user says "skip" or "not now" for a specific item):
Append to `.claude/orch/pending_setup.md`:
```markdown
| <name> | <type> | <priority> | <today's date> | |
```

After all items processed (or skipped), confirm: "Setup complete. N tools installed."

---

## Deferred Setup ("skip setup" / resume)

**"skip setup"** — Write all currently surfaced gaps to `.claude/orch/pending_setup.md`. Session continues without installing.

**On next session** — `session-start.py` re-surfaces pending items via the setup gap notice. When the user says "set up tools", run the setup flow above starting from `pending_setup.md` items.

**"dismiss setup"** — Remove all items from `pending_setup.md`. No further reminders until `discover_tools.py` surfaces new gaps.

---
```

- [ ] **Step 4: Add tasks.md management to the Fresh Start section**

In the `## Output Behaviour` → `### Fresh start (no session.md)` section, update step 2 to:

```markdown
### Fresh start (no session.md)

1. State phase detection — one line (fuzzy or concrete)
2. Read `.claude/orch/brain.md` (if exists): note relevant conventions and prior decisions
3. Check `.claude/orch/tasks.md` (if exists): note any active tasks that might conflict
4. Invoke `orch-planner` to write `.claude/session.md`; add entry to `tasks.md` Active Tasks table
5. Output the **Step 1 prompt** — copy-paste ready
6. End with: *"When Step 1 is done, say 'step done' and I'll write Step 2."*
```

- [ ] **Step 5: Add "refresh brain" command**

Append the following to the `## References` section at the bottom of SKILL.md:

```markdown

### Commands

| Command | What it does |
|---------|-------------|
| `set up tools` | Install missing plugins + configure MCPs interactively |
| `skip setup` | Defer all setup items to pending_setup.md |
| `dismiss setup` | Clear pending_setup.md permanently |
| `refresh brain` | Force re-scan of project structure + reset llm_analysis to pending |
| `resume session` | Load existing session.md and continue from [NEXT] step |
```

- [ ] **Step 6: Verify SKILL.md reads correctly**

```bash
grep -n "Brain Analysis Phase\|set up tools\|refresh brain\|Intelligence Hub\|tasks\.md" skills/orch/SKILL.md
```

Expected: Lines found for each of the new sections.

- [ ] **Step 7: Commit**

```bash
git add skills/orch/SKILL.md
git commit -m "feat: add intelligence hub, brain analysis phase, and interactive setup to orch skill"
```

---

### Task 5: Update `skills/orch-planner/SKILL.md`

**Files:**
- Modify: `skills/orch-planner/SKILL.md`

- [ ] **Step 1: Add brain.md update step to the Replan Procedure**

In the `## Replan Procedure` section, after step 7 (`Update last-updated date`), add step 8:

```markdown
8. **Update brain.md** (if `.claude/orch/brain.md` exists): if the completed step created new files, discovered naming patterns, or made an architectural decision, append 1–3 concise bullets to the relevant section:
   - New file or module → append to **Architecture**: `- [filename]: [one-line purpose]`
   - Naming/style pattern found → append to **Conventions**: `- [pattern description]`
   - Technical decision made → append to **Decisions Log**: `- [date] [decision]: [rationale]`
   Keep each bullet under 80 characters. Skip this step if the completed step produced no new project-level insights.
```

- [ ] **Step 2: Replace the Session End Sequence**

Replace the existing `## Session End Sequence` section with:

```markdown
## Session End Sequence

Every plan's final step:
1. `timeline-report` skill → session summary
2. `finishing-a-development-branch` skill → cleanup, PR prep
3. Commit via `commit-commands`
4. Mark session.md `status: complete`
5. **Update `.claude/orch/history.md`** (if it exists): append one entry:
   ```markdown
   ## <today's date> — <task name>
   - Steps: <N> completed (<step names, comma-separated>)
   - Outcome: <1–2 sentence summary of what was built/fixed>
   - Skills used: <list>
   - Lessons: <key discoveries or gotchas for future sessions>
   ```
6. **Update `.claude/orch/tasks.md`** (if it exists): move the task row from Active Tasks to Recently Completed. Keep only the 5 most recent completed entries (delete older ones).
```

- [ ] **Step 3: Verify SKILL.md reads correctly**

```bash
grep -n "Update brain\.md\|history\.md\|tasks\.md\|Session End" skills/orch-planner/SKILL.md
```

Expected: Lines found for each new section.

- [ ] **Step 4: Commit**

```bash
git add skills/orch-planner/SKILL.md
git commit -m "feat: add brain.md and history.md updates to orch-planner session lifecycle"
```

---

## End-to-End Verification

After all 5 tasks, run the full install flow in a test project:

```bash
# 1. Create a test Python project
mkdir -p /tmp/verify-orch/src && cd /tmp/verify-orch
echo "from flask import Flask" > src/app.py
echo "flask==3.0.0" > requirements.txt
git init && git add . && git commit -m "init"

# 2. Run session-start hook as if starting a Claude Code session
CLAUDE_PLUGIN_ROOT=/path/to/orch \
  echo '{"cwd": "/tmp/verify-orch"}' | python3 /path/to/orch/hooks/session-start.py
```

Expected output: JSON with `[Orch] Brain skeleton ready` (pending analysis) + possibly setup gap notice.

```bash
# 3. Verify brain.md was created
cat /tmp/verify-orch/.claude/orch/brain.md | head -10
```

Expected: `<!-- git_head: <sha> -->`, `<!-- llm_analysis: pending -->`, Python in Tech Stack.

```bash
# 4. Simulate git pull (new commit changes HEAD)
echo "# added" >> /tmp/verify-orch/requirements.txt
git -C /tmp/verify-orch add . && git -C /tmp/verify-orch commit -m "add comment"
echo '{"cwd": "/tmp/verify-orch"}' | CLAUDE_PLUGIN_ROOT=/path/to/orch python3 /path/to/orch/hooks/session-start.py
```

Expected: Brain structural sections refreshed (no error), knowledge sections untouched.

```bash
# 5. Test routing injection in prompt hook
echo '{"cwd": "/tmp/verify-orch", "user_prompt": "add a database model"}' | \
  CLAUDE_PLUGIN_ROOT=/path/to/orch python3 /path/to/orch/hooks/prompt-submit.py
```

Expected: JSON output contains `[ORCH] Project:` header and complexity gate routing instruction.

```bash
# 6. Run all unit tests
python3 -m pytest tests/test_init_brain.py -v
```

Expected: All tests pass.
