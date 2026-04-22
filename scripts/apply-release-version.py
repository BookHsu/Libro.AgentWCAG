#!/usr/bin/env python3
"""Apply a tag-derived release version to versioned manifests in the working tree."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION_PATTERN = re.compile(
    r"^(?P<core>\d+\.\d+\.\d+)(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a release version to versioned manifests.")
    parser.add_argument(
        "--version",
        required=True,
        help="Semantic version without the leading 'v' (X.Y.Z or X.Y.Z-<channel>.<n>).",
    )
    return parser.parse_args()


def _parse_release_version(version: str) -> dict[str, str | bool | None]:
    candidate = version.strip()
    match = RELEASE_VERSION_PATTERN.fullmatch(candidate)
    if not match:
        raise RuntimeError(
            "Release version must be semantic version X.Y.Z or prerelease X.Y.Z-<channel>.<n>, "
            f"got: {version}"
        )

    prerelease = match.group("prerelease")
    channel = None
    npm_dist_tag = "latest"
    if prerelease:
        leading_identifier = prerelease.split(".", 1)[0].lower()
        channel = leading_identifier if leading_identifier and not leading_identifier.isdigit() else "next"
        npm_dist_tag = channel

    return {
        "version": candidate,
        "is_prerelease": bool(prerelease),
        "prerelease_channel": channel,
        "npm_dist_tag": npm_dist_tag,
    }


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
    release_meta = _parse_release_version(args.version)
    version = str(release_meta["version"])

    update_pyproject(version)
    update_package_json(version)
    update_claude_plugin(version)
    print(json.dumps({"applied_version": version, **release_meta}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
