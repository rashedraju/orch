#!/usr/bin/env python3
"""
Scans Claude Code configuration and project context, then writes (or refreshes)
references/setup.md in the orch skill directory.

Usage:
    python scripts/init_setup.py --project-path /path/to/project [--force]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PLUGINS_DIR = CLAUDE_DIR / "plugins"
SKILL_DIR = Path(__file__).resolve().parent.parent
SETUP_MD = SKILL_DIR / "references" / "setup.md"
STALENESS_DAYS = 7


def is_stale(force: bool) -> bool:
    if force or not SETUP_MD.exists():
        return True
    age_days = (datetime.now().timestamp() - SETUP_MD.stat().st_mtime) / 86400
    return age_days > STALENESS_DAYS


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def get_enabled_plugins() -> dict[str, bool]:
    settings = read_json(CLAUDE_DIR / "settings.json")
    return settings.get("enabledPlugins", {})


def get_installed_plugins() -> dict:
    data = read_json(PLUGINS_DIR / "installed_plugins.json")
    return data.get("plugins", {})


def scan_plugin_contents(install_path: str) -> dict:
    """Return skills, agents, commands, hooks, and mcp info for a plugin cache dir."""
    root = Path(install_path)
    result = {"skills": [], "agents": [], "commands": [], "hooks": [], "mcp": {}}

    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for skill in sorted(skills_dir.iterdir()):
            if (skill / "SKILL.md").exists():
                result["skills"].append(skill.name)

    agents_dir = root / "agents"
    if agents_dir.is_dir():
        result["agents"] = [
            f.stem for f in sorted(agents_dir.glob("*.md"))
        ]

    commands_dir = root / "commands"
    if commands_dir.is_dir():
        result["commands"] = [
            f.stem for f in sorted(commands_dir.glob("*.md"))
        ]

    hooks_file = root / "hooks" / "hooks.json"
    if hooks_file.exists():
        hooks_data = read_json(hooks_file)
        result["hooks"] = list(hooks_data.get("hooks", {}).keys())

    mcp_file = root / ".mcp.json"
    if mcp_file.exists():
        result["mcp"] = read_json(mcp_file)

    return result


def detect_tech_stack(project_path: Path) -> list[dict]:
    """Return list of {indicator, detected, plugins} dicts."""
    stack = []

    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        pkg = read_json(pkg_json)
        all_deps = {
            **pkg.get("dependencies", {}),
            **pkg.get("devDependencies", {}),
        }
        dep_names = set(all_deps.keys())

        has_ts = (project_path / "tsconfig.json").exists() or "typescript" in dep_names
        if has_ts:
            stack.append({"indicator": "TypeScript", "detected": True,
                          "plugins": ["typescript-lsp", "context7"]})

        if "react" in dep_names or "react-dom" in dep_names:
            stack.append({"indicator": "React", "detected": True,
                          "plugins": ["frontend-design", "ui-ux-pro-max"]})

        if "next" in dep_names:
            stack.append({"indicator": "Next.js", "detected": True,
                          "plugins": ["frontend-design", "context7"]})

        if "vue" in dep_names or "@vue/core" in dep_names:
            stack.append({"indicator": "Vue.js", "detected": True,
                          "plugins": ["frontend-design"]})

        if "@supabase/supabase-js" in dep_names or "supabase" in dep_names:
            stack.append({"indicator": "Supabase", "detected": True,
                          "plugins": ["supabase"]})

        if "tailwindcss" in dep_names:
            stack.append({"indicator": "Tailwind CSS", "detected": True,
                          "plugins": ["frontend-design"]})

        if not has_ts and pkg_json.exists():
            stack.append({"indicator": "JavaScript", "detected": True,
                          "plugins": ["context7"]})

    if (project_path / "composer.json").exists():
        composer = read_json(project_path / "composer.json")
        requires = {**composer.get("require", {}), **composer.get("require-dev", {})}
        if any("laravel" in k.lower() for k in requires):
            stack.append({"indicator": "PHP/Laravel", "detected": True,
                          "plugins": ["php-lsp", "context7"]})
        else:
            stack.append({"indicator": "PHP", "detected": True,
                          "plugins": ["php-lsp"]})

    if (project_path / "pyproject.toml").exists() or (project_path / "requirements.txt").exists():
        stack.append({"indicator": "Python", "detected": True,
                      "plugins": ["context7"]})

    if (project_path / "Cargo.toml").exists():
        stack.append({"indicator": "Rust", "detected": True,
                      "plugins": ["context7"]})

    if (project_path / "go.mod").exists():
        stack.append({"indicator": "Go", "detected": True,
                      "plugins": ["context7"]})

    if (project_path / "pom.xml").exists() or list(project_path.glob("*.java")):
        stack.append({"indicator": "Java", "detected": True,
                      "plugins": ["context7"]})

    # GitHub Actions
    if (project_path / ".github" / "workflows").exists():
        stack.append({"indicator": "GitHub Actions", "detected": True,
                      "plugins": ["github"]})

    return stack


def get_mcp_auth_status() -> dict[str, str]:
    """Read mcp-needs-auth-cache.json, return {server_name: status}."""
    cache = read_json(PLUGINS_DIR / "mcp-needs-auth-cache.json")
    # Keys are MCP server names; presence means auth is needed
    return {k: "needs-auth" for k in cache} if cache else {}


def preserve_maintenance_log(existing_content: str) -> str:
    """Extract the maintenance log section from existing setup.md."""
    match = re.search(r"(## Maintenance Log\n.*)", existing_content, re.DOTALL)
    return match.group(1) if match else "## Maintenance Log\n\n| Date | What changed |\n|------|---------------|\n| " + datetime.now().strftime("%Y-%m-%d") + " | Initial auto-generation |\n"


def build_setup_md(
    project_path: Path,
    enabled_plugins: dict,
    installed_plugins: dict,
    tech_stack: list,
    mcp_auth: dict,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"<!-- AUTO-GENERATED by scripts/init_setup.py — do not edit above the Maintenance Log -->",
        f"<!-- Last generated: {now} | Project: {project_path} -->",
        "",
        "# User Setup Reference",
        "",
        "> Auto-generated. Re-run `python scripts/init_setup.py --project-path <path>` to refresh.",
        "> Edit only the **Maintenance Log** section manually.",
        "",
        "---",
        "",
        "## Models",
        "",
        "| Model | Use For |",
        "|-------|---------|",
        "| Sonnet 4.6 | Default — all implementation |",
        "| Opus 4.6 | Complex architecture, multi-system reasoning |",
        "| Haiku 4.5 | Quick lookups, simple status checks |",
        "",
        "**Usage limit:** 5-hour rolling window (Pro plan, ~44k tokens/window)",
        "",
        "---",
        "",
        "## Installed Plugins",
        "",
        "| Plugin | Scope | Enabled | Skills | Agents |",
        "|--------|-------|---------|--------|--------|",
    ]

    all_skills = []
    all_agents = []
    all_mcps = {}
    all_hooks = []

    for plugin_key, installs in installed_plugins.items():
        plugin_name = plugin_key.split("@")[0]
        enabled = enabled_plugins.get(plugin_key, False)
        for inst in installs:
            install_path = inst.get("installPath", "")
            scope = inst.get("scope", "user")
            contents = scan_plugin_contents(install_path)

            skills_str = ", ".join(contents["skills"]) if contents["skills"] else "—"
            agents_str = ", ".join(contents["agents"]) if contents["agents"] else "—"
            enabled_str = "✅" if enabled else "❌"
            lines.append(f"| `{plugin_name}` | {scope} | {enabled_str} | {skills_str} | {agents_str} |")

            if enabled:
                all_skills.extend(contents["skills"])
                all_agents.extend(contents["agents"])
                all_mcps.update(contents["mcp"])
                all_hooks.extend(
                    f"{plugin_name}: {h}" for h in contents["hooks"]
                )

    lines += [
        "",
        "---",
        "",
        "## Available Skills",
        "",
    ]
    if all_skills:
        for skill in sorted(set(all_skills)):
            lines.append(f"- `{skill}`")
    else:
        lines.append("_No skills discovered._")

    lines += [
        "",
        "---",
        "",
        "## Available Agents",
        "",
    ]
    if all_agents:
        for agent in sorted(set(all_agents)):
            lines.append(f"- `{agent}`")
    else:
        lines.append("_No agents discovered._")

    lines += [
        "",
        "---",
        "",
        "## MCP Servers",
        "",
        "| Server | Command | Auth Status |",
        "|--------|---------|-------------|",
    ]
    for server, config in all_mcps.items():
        if isinstance(config, dict):
            cmd_type = config.get("type", "stdio")
            if cmd_type == "http":
                cmd_display = f"HTTP: {config.get('url', '?')[:50]}"
            else:
                cmd_parts = [config.get("command", "")] + config.get("args", [])
                cmd_display = " ".join(str(p) for p in cmd_parts)[:60]
        else:
            cmd_display = str(config)[:60]
        auth_status = mcp_auth.get(server, "✅ ready")
        lines.append(f"| `{server}` | `{cmd_display}` | {auth_status} |")

    if not all_mcps:
        lines.append("_No MCP servers detected from enabled plugins._")

    lines += [
        "",
        "---",
        "",
        "## Active Hooks",
        "",
    ]
    if all_hooks:
        for hook in sorted(set(all_hooks)):
            lines.append(f"- {hook}")
    else:
        lines.append("_No hooks detected from enabled plugins._")

    lines += [
        "",
        "---",
        "",
        "## Project Tech Stack",
        "",
        f"Scanned from: `{project_path}`",
        "",
        "| Indicator | Detected | Relevant Plugins |",
        "|-----------|----------|-----------------|",
    ]
    if tech_stack:
        for item in tech_stack:
            plugins_str = ", ".join(f"`{p}`" for p in item["plugins"])
            lines.append(f"| {item['indicator']} | {'Yes' if item['detected'] else 'No'} | {plugins_str} |")
    else:
        lines.append("| _No recognizable tech stack detected_ | — | — |")

    lines += [
        "",
        "---",
        "",
    ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate orch setup reference.")
    parser.add_argument("--project-path", required=True, help="Root of the user's project to analyze")
    parser.add_argument("--force", action="store_true", help="Regenerate even if setup.md is fresh")
    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()

    if not is_stale(args.force):
        age_days = (datetime.now().timestamp() - SETUP_MD.stat().st_mtime) / 86400
        print(f"Setup is current ({age_days:.1f} days old). Use --force to regenerate.")
        sys.exit(0)

    print(f"Scanning Claude Code configuration...")

    enabled = get_enabled_plugins()
    installed = get_installed_plugins()
    tech_stack = detect_tech_stack(project_path)
    mcp_auth = get_mcp_auth_status()

    # Preserve maintenance log from existing file
    existing_content = SETUP_MD.read_text() if SETUP_MD.exists() else ""
    maintenance_log = preserve_maintenance_log(existing_content)

    content = build_setup_md(project_path, enabled, installed, tech_stack, mcp_auth)
    content += maintenance_log + "\n"

    SETUP_MD.parent.mkdir(parents=True, exist_ok=True)
    SETUP_MD.write_text(content)

    print(f"✓ setup.md written to {SETUP_MD}")
    print(f"  Plugins scanned: {len(installed)}")
    print(f"  Enabled plugins: {sum(1 for k in installed if enabled.get(k))}")
    print(f"  Tech stack indicators: {len(tech_stack)}")
    if tech_stack:
        print(f"  Detected: {', '.join(s['indicator'] for s in tech_stack)}")


if __name__ == "__main__":
    main()
