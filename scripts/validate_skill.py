#!/usr/bin/env python3
"""Validate a skill folder without relying on local Codex system files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a skill directory.")
    parser.add_argument("skill_dir")
    return parser.parse_args()


def _load_frontmatter(skill_md: Path) -> dict[str, object]:
    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError("SKILL.md frontmatter is incomplete")
    return yaml.safe_load(parts[1]) or {}


def validate_skill(skill_dir: Path) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise ValueError("Missing SKILL.md")

    frontmatter = _load_frontmatter(skill_md)
    name = str(frontmatter.get("name", ""))
    description = str(frontmatter.get("description", ""))

    if not name or not SKILL_NAME_PATTERN.match(name):
        raise ValueError("Frontmatter name must match ^[a-z0-9-]{1,64}$")
    if not description:
        raise ValueError("Frontmatter description is required")

    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if openai_yaml.exists():
        yaml.safe_load(openai_yaml.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    validate_skill(Path(args.skill_dir))
    print("Skill is valid!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
