#!/usr/bin/env python3
"""
Downloads and registers a Claude Code plugin from a marketplace.

Usage:
    python scripts/install_plugin.py --plugin <name> --marketplace claude-plugins-official
    python scripts/install_plugin.py --plugin <name> --marketplace claude-plugins-official --scope project --project-path /path/to/project
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PLUGINS_DIR = CLAUDE_DIR / "plugins"


def read_json(path: Path) -> dict | list:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def find_plugin_in_marketplace(plugin_name: str, marketplace: str) -> dict | None:
    marketplace_dir = PLUGINS_DIR / "marketplaces" / marketplace
    marketplace_json = marketplace_dir / ".claude-plugin" / "marketplace.json"
    if not marketplace_json.exists():
        print(f"ERROR: Marketplace '{marketplace}' not found at {marketplace_dir}", file=sys.stderr)
        return None
    data = read_json(marketplace_json)
    for p in data.get("plugins", []):
        if p.get("name") == plugin_name:
            return p
    return None


def resolve_source(plugin_entry: dict, marketplace: str) -> dict:
    """Return normalized source info: {type, path_or_url, subdir}."""
    source = plugin_entry.get("source", "")
    marketplace_dir = PLUGINS_DIR / "marketplaces" / marketplace

    if isinstance(source, str):
        if source.startswith("./"):
            # Relative path within the marketplace directory
            local_path = marketplace_dir / source.lstrip("./")
            return {"type": "local", "local_path": local_path}
        elif source.startswith("http"):
            return {"type": "url", "url": source}
        else:
            return {"type": "unknown", "raw": source}
    elif isinstance(source, dict):
        src_type = source.get("source")
        if src_type == "url":
            return {"type": "url", "url": source.get("url", "")}
        elif src_type == "git-subdir":
            return {
                "type": "git-subdir",
                "url": source.get("url", ""),
                "subdir": source.get("path", ""),
            }
        elif src_type == "github":
            repo = source.get("repo", "")
            return {"type": "github", "repo": repo}

    return {"type": "unknown", "raw": str(source)}


def get_git_sha(repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def clone_url(url: str, dest: Path) -> bool:
    """Git clone a URL to dest. Returns True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git clone failed: {e}", file=sys.stderr)
        return False


def clone_subdir(url: str, subdir: str, dest: Path) -> bool:
    """Sparse-clone a specific subdirectory from a git repo."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = dest.parent / f"_tmp_{dest.name}"
    try:
        subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none",
                        "--sparse", url, str(tmp_dir)], check=True)
        subprocess.run(["git", "sparse-checkout", "set", subdir],
                       cwd=tmp_dir, check=True)
        # Move the subdirectory to dest
        subdir_path = tmp_dir / subdir
        if subdir_path.exists():
            shutil.copytree(str(subdir_path), str(dest))
        else:
            print(f"ERROR: Subdirectory '{subdir}' not found in cloned repo", file=sys.stderr)
            return False
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: sparse clone failed: {e}", file=sys.stderr)
        return False
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


def register_plugin(plugin_name: str, marketplace: str, install_path: Path,
                    scope: str, project_path: Path | None) -> None:
    """Add the plugin to installed_plugins.json and settings.json."""
    installed_path = PLUGINS_DIR / "installed_plugins.json"
    installed_data = read_json(installed_path)
    if not isinstance(installed_data, dict):
        installed_data = {"version": 2, "plugins": {}}
    installed_data.setdefault("version", 2)
    installed_data.setdefault("plugins", {})

    plugin_key = f"{plugin_name}@{marketplace}"
    git_sha = get_git_sha(install_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    entry = {
        "scope": scope,
        "installPath": str(install_path),
        "version": "unknown",
        "installedAt": now_iso,
        "lastUpdated": now_iso,
        "gitCommitSha": git_sha,
    }
    if scope == "project" and project_path:
        entry["projectPath"] = str(project_path)

    installed_data["plugins"].setdefault(plugin_key, [])
    # Avoid duplicate entries for same install path
    existing_paths = [e.get("installPath") for e in installed_data["plugins"][plugin_key]]
    if str(install_path) not in existing_paths:
        installed_data["plugins"][plugin_key].append(entry)

    write_json(installed_path, installed_data)

    # Enable in settings.json
    settings_path = CLAUDE_DIR / "settings.json"
    settings = read_json(settings_path)
    if not isinstance(settings, dict):
        settings = {}
    settings.setdefault("enabledPlugins", {})
    settings["enabledPlugins"][plugin_key] = True
    write_json(settings_path, settings)


def main():
    parser = argparse.ArgumentParser(description="Install a Claude Code plugin from a marketplace.")
    parser.add_argument("--plugin", required=True, help="Plugin name (e.g. typescript-lsp)")
    parser.add_argument("--marketplace", default="claude-plugins-official",
                        help="Marketplace name (default: claude-plugins-official)")
    parser.add_argument("--scope", choices=["user", "project"], default="user",
                        help="Installation scope (default: user)")
    parser.add_argument("--project-path", help="Required when scope=project")
    args = parser.parse_args()

    plugin_name = args.plugin
    marketplace = args.marketplace
    scope = args.scope
    project_path = Path(args.project_path).resolve() if args.project_path else None

    if scope == "project" and not project_path:
        print("ERROR: --project-path is required when --scope=project", file=sys.stderr)
        sys.exit(1)

    # Check if already installed
    installed_data = read_json(PLUGINS_DIR / "installed_plugins.json")
    plugin_key = f"{plugin_name}@{marketplace}"
    if plugin_key in installed_data.get("plugins", {}):
        settings = read_json(CLAUDE_DIR / "settings.json")
        if settings.get("enabledPlugins", {}).get(plugin_key):
            print(f"'{plugin_name}' is already installed and enabled. Nothing to do.")
        else:
            # Already installed, just enable it
            settings.setdefault("enabledPlugins", {})[plugin_key] = True
            write_json(CLAUDE_DIR / "settings.json", settings)
            print(f"'{plugin_name}' was installed but not enabled. Enabled it now.")
        sys.exit(0)

    # Find plugin in marketplace
    plugin_entry = find_plugin_in_marketplace(plugin_name, marketplace)
    if not plugin_entry:
        print(f"ERROR: Plugin '{plugin_name}' not found in marketplace '{marketplace}'", file=sys.stderr)
        sys.exit(1)

    source = resolve_source(plugin_entry, marketplace)
    cache_dir = PLUGINS_DIR / "cache" / marketplace / plugin_name / "latest"

    print(f"Installing '{plugin_name}' from {marketplace}...")
    print(f"  Source type: {source['type']}")

    success = False

    if source["type"] == "local":
        local_path = source["local_path"]
        if not local_path.exists():
            print(f"ERROR: Local path does not exist: {local_path}", file=sys.stderr)
            sys.exit(1)
        # Copy local plugin to cache
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        shutil.copytree(str(local_path), str(cache_dir))
        success = True

    elif source["type"] == "url":
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        success = clone_url(source["url"], cache_dir)

    elif source["type"] == "git-subdir":
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        success = clone_subdir(source["url"], source["subdir"], cache_dir)

    elif source["type"] == "github":
        # GitHub repo reference — construct URL
        repo = source.get("repo", "")
        url = f"https://github.com/{repo}.git"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        success = clone_url(url, cache_dir)

    else:
        print(f"ERROR: Unsupported source type '{source['type']}' for plugin '{plugin_name}'", file=sys.stderr)
        sys.exit(1)

    if not success:
        print(f"ERROR: Failed to install '{plugin_name}'", file=sys.stderr)
        sys.exit(1)

    register_plugin(plugin_name, marketplace, cache_dir, scope, project_path)

    print(f"✓ '{plugin_name}' installed to {cache_dir}")
    print(f"  Scope: {scope}")
    print(f"  Enabled in settings.json")
    print(f"\nRestart Claude Code or run a new session to activate the plugin.")


if __name__ == "__main__":
    main()
