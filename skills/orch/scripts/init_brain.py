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
