#!/usr/bin/env python3
"""
Analyzes the project tech stack and matches it against available marketplace plugins,
returning a ranked JSON list of recommendations.

Usage:
    python scripts/discover_tools.py --project-path /path/to/project
    python scripts/discover_tools.py --project-path /path/to/project --json
"""
import argparse
import json
import sys
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PLUGINS_DIR = CLAUDE_DIR / "plugins"
MARKETPLACE_DIR = PLUGINS_DIR / "marketplaces" / "claude-plugins-official"
MARKETPLACE_JSON = MARKETPLACE_DIR / ".claude-plugin" / "marketplace.json"
INSTALLED_PLUGINS_JSON = PLUGINS_DIR / "installed_plugins.json"
SETTINGS_JSON = CLAUDE_DIR / "settings.json"

# Map of tech detection key → list of (plugin_name, reason, priority)
# priority: "required" | "recommended" | "optional"
TECH_TO_PLUGINS = {
    "typescript": [
        ("typescript-lsp", "TypeScript LSP for diagnostics and type-checking", "recommended"),
        ("context7", "Live TypeScript/framework documentation", "recommended"),
    ],
    "javascript": [
        ("context7", "Live JavaScript/Node.js documentation", "recommended"),
    ],
    "react": [
        ("frontend-design", "React component design patterns and best practices", "recommended"),
        ("ui-ux-pro-max", "UI/UX design workflow for React apps", "optional"),
    ],
    "nextjs": [
        ("frontend-design", "Next.js app design and routing patterns", "recommended"),
        ("context7", "Live Next.js documentation", "recommended"),
    ],
    "vue": [
        ("frontend-design", "Vue component and composables patterns", "recommended"),
    ],
    "tailwind": [
        ("frontend-design", "Tailwind CSS utility-first design workflow", "optional"),
    ],
    "supabase": [
        ("supabase", "Direct Supabase database operations via MCP", "recommended"),
    ],
    "php_laravel": [
        ("php-lsp", "PHP LSP for diagnostics and autocomplete", "recommended"),
        # laravel-boost is known-failed, so not included
    ],
    "php": [
        ("php-lsp", "PHP LSP for diagnostics and autocomplete", "optional"),
    ],
    "python": [
        ("context7", "Live Python library documentation", "optional"),
    ],
    "github_actions": [
        ("github", "GitHub PR management and CI integration via MCP", "recommended"),
    ],
}

# Always required regardless of tech stack
ALWAYS_REQUIRED = [
    ("superpowers", "Core planning, brainstorming, and debugging skills — required for session coach", "required"),
    ("context7", "Live documentation lookup for any framework", "required"),
]


def read_json(path: Path) -> dict | list:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def get_plugin_status(plugin_name: str, installed: dict, enabled: dict) -> str:
    marketplace = "claude-plugins-official"
    plugin_key = f"{plugin_name}@{marketplace}"
    if plugin_key in installed:
        if enabled.get(plugin_key):
            return "installed_enabled"
        return "installed_not_enabled"
    return "not_installed"


def detect_tech_keys(project_path: Path) -> list[str]:
    """Return list of detected tech keys matching TECH_TO_PLUGINS."""
    keys = []
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
            keys.append("typescript")
        else:
            keys.append("javascript")

        if "react" in dep_names or "react-dom" in dep_names:
            keys.append("react")
        if "next" in dep_names:
            keys.append("nextjs")
        if "vue" in dep_names or "@vue/core" in dep_names:
            keys.append("vue")
        if "tailwindcss" in dep_names:
            keys.append("tailwind")
        if "@supabase/supabase-js" in dep_names or "supabase" in dep_names:
            keys.append("supabase")

    if (project_path / "composer.json").exists():
        composer = read_json(project_path / "composer.json")
        requires = {**composer.get("require", {}), **composer.get("require-dev", {})}
        if any("laravel" in k.lower() for k in requires):
            keys.append("php_laravel")
        else:
            keys.append("php")

    for py_indicator in ["pyproject.toml", "requirements.txt", "setup.py"]:
        if (project_path / py_indicator).exists():
            keys.append("python")
            break

    if (project_path / ".github" / "workflows").exists():
        keys.append("github_actions")

    return keys


def build_recommendations(project_path: Path) -> list[dict]:
    installed = read_json(INSTALLED_PLUGINS_JSON).get("plugins", {})
    enabled = read_json(SETTINGS_JSON).get("enabledPlugins", {})

    # Collect recommendations, deduplicating by plugin name
    seen = {}

    def add(plugin_name, reason, priority):
        if plugin_name in seen:
            # Upgrade priority if higher
            rank = {"required": 0, "recommended": 1, "optional": 2}
            if rank[priority] < rank[seen[plugin_name]["priority"]]:
                seen[plugin_name]["priority"] = priority
                seen[plugin_name]["reason"] = reason
        else:
            seen[plugin_name] = {
                "plugin": plugin_name,
                "marketplace": "claude-plugins-official",
                "reason": reason,
                "priority": priority,
                "status": get_plugin_status(plugin_name, installed, enabled),
            }

    # Always-required first
    for plugin_name, reason, priority in ALWAYS_REQUIRED:
        add(plugin_name, reason, priority)

    # Tech-stack-based
    tech_keys = detect_tech_keys(project_path)
    for key in tech_keys:
        for plugin_name, reason, priority in TECH_TO_PLUGINS.get(key, []):
            add(plugin_name, reason, priority)

    # Sort: required first, then recommended, then optional; skip already enabled ones last
    priority_rank = {"required": 0, "recommended": 1, "optional": 2}
    status_rank = {"not_installed": 0, "installed_not_enabled": 1, "installed_enabled": 2}

    recs = list(seen.values())
    recs.sort(key=lambda r: (priority_rank[r["priority"]], status_rank[r["status"]], r["plugin"]))

    return recs


def format_table(recs: list[dict]) -> str:
    lines = [
        "| Plugin | Reason | Priority | Status |",
        "|--------|--------|----------|--------|",
    ]
    status_display = {
        "installed_enabled": "✅ active",
        "installed_not_enabled": "⚠️  installed, not enabled",
        "not_installed": "❌ not installed",
    }
    for r in recs:
        status = status_display.get(r["status"], r["status"])
        lines.append(f"| `{r['plugin']}` | {r['reason']} | {r['priority']} | {status} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Discover recommended Claude Code plugins for a project.")
    parser.add_argument("--project-path", required=True, help="Root of the project to analyze")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of human-readable table")
    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    recs = build_recommendations(project_path)

    if args.json:
        print(json.dumps(recs, indent=2))
    else:
        actionable = [r for r in recs if r["status"] != "installed_enabled"]
        active = [r for r in recs if r["status"] == "installed_enabled"]

        if not actionable:
            print("All recommended plugins are already installed and enabled.")
        else:
            print(f"Found {len(actionable)} plugin(s) to install or enable:\n")
            print(format_table(actionable))

        if active:
            print(f"\nAlready active ({len(active)}):", ", ".join(f"`{r['plugin']}`" for r in active))


if __name__ == "__main__":
    main()
