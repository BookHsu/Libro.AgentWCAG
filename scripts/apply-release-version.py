#!/usr/bin/env python3
"""Apply a tag-derived release version to versioned manifests in the working tree."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a release version to versioned manifests.")
    parser.add_argument("--version", required=True, help="Semantic version without the leading 'v'.")
    return parser.parse_args()


def _replace_single(pattern: str, replacement: str, content: str, path: Path) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Expected exactly one replacement in {path}")
    return updated


def update_pyproject(version: str) -> None:
    path = REPO_ROOT / "pyproject.toml"
    content = path.read_text(encoding="utf-8")
    updated = _replace_single(r'^version = "[^"]+"$', f'version = "{version}"', content, path)
    path.write_text(updated, encoding="utf-8")


def update_package_json(version: str) -> None:
    path = REPO_ROOT / "package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = version
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_claude_plugin(version: str) -> None:
    plugin_path = REPO_ROOT / "packaging" / "templates" / "claude-plugin" / "plugin.json"
    plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    plugin["version"] = version
    plugin_path.write_text(json.dumps(plugin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    marketplace_path = REPO_ROOT / "packaging" / "templates" / "claude-plugin" / "marketplace.json"
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    metadata = marketplace.setdefault("metadata", {})
    metadata["version"] = version
    for plugin_entry in marketplace.get("plugins", []):
        if isinstance(plugin_entry, dict) and plugin_entry.get("name") == "libro-wcag":
            plugin_entry["version"] = version
    marketplace_path.write_text(json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    version = args.version.strip()
    if not SEMVER_PATTERN.fullmatch(version):
        raise RuntimeError(f"Release version must be semantic version X.Y.Z, got: {args.version}")

    update_pyproject(version)
    update_package_json(version)
    update_claude_plugin(version)
    print(json.dumps({"applied_version": version}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
