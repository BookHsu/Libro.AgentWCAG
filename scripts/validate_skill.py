#!/usr/bin/env python3
"""Validate a skill folder without relying on local Codex system files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")
RULE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
POLICY_BUNDLE_REQUIRED_KEYS = [
    "name",
    "description",
    "bundle_version",
    "updated_at",
    "fail_on",
    "include_rules",
    "ignore_rules",
    "bundle_hash",
]
POLICY_BUNDLE_REQUIRED_KEY_SET = set(POLICY_BUNDLE_REQUIRED_KEYS)
POLICY_BUNDLE_ALLOWED_FAIL_ON = {"critical", "serious", "moderate"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a skill directory.")
    parser.add_argument("skill_dir")
    parser.add_argument(
        "--validate-policy-bundles",
        action="store_true",
        help="Validate docs/policy-bundles metadata lock, schema, and explain-policy compatibility.",
    )
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


def _parse_updated_at(value: str, file_path: Path) -> None:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as err:
        raise ValueError(f"{file_path}: updated_at must be ISO8601 with timezone") from err
    if parsed.tzinfo is None:
        raise ValueError(f"{file_path}: updated_at must include timezone offset")
    parsed.astimezone(timezone.utc)


def _normalize_rule_list(value: Any, field_name: str, file_path: Path) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{file_path}: {field_name} must be a JSON array")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"{file_path}: {field_name}[{index}] must be a string")
        rule = item.strip().lower()
        if not rule:
            raise ValueError(f"{file_path}: {field_name}[{index}] must not be empty")
        if not RULE_ID_PATTERN.match(rule):
            raise ValueError(f"{file_path}: {field_name}[{index}] has invalid rule id: {item!r}")
        normalized.append(rule)
    return normalized


def _compute_bundle_hash(payload: dict[str, Any]) -> str:
    hash_material = {key: payload[key] for key in POLICY_BUNDLE_REQUIRED_KEYS if key != "bundle_hash"}
    canonical = json.dumps(hash_material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_single_policy_bundle(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    keys = list(payload.keys())
    if keys != POLICY_BUNDLE_REQUIRED_KEYS:
        raise ValueError(
            f"{file_path}: key order must be {POLICY_BUNDLE_REQUIRED_KEYS}; got {keys}"
        )

    key_set = set(payload)
    missing = sorted(POLICY_BUNDLE_REQUIRED_KEY_SET - key_set)
    unexpected = sorted(key_set - POLICY_BUNDLE_REQUIRED_KEY_SET)
    if missing or unexpected:
        raise ValueError(
            f"{file_path}: missing keys={missing or '[]'}, unexpected keys={unexpected or '[]'}"
        )

    name = payload["name"]
    description = payload["description"]
    bundle_version = payload["bundle_version"]
    updated_at = payload["updated_at"]
    fail_on = payload["fail_on"]
    include_rules = payload["include_rules"]
    ignore_rules = payload["ignore_rules"]
    bundle_hash = payload["bundle_hash"]

    if not isinstance(name, str) or not name:
        raise ValueError(f"{file_path}: name must be a non-empty string")
    if file_path.stem != name:
        raise ValueError(f"{file_path}: filename must match bundle name ({name}.json)")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"{file_path}: description must be a non-empty string")
    if not isinstance(bundle_version, str) or not re.match(r"^\d+\.\d+\.\d+$", bundle_version):
        raise ValueError(f"{file_path}: bundle_version must match semantic format X.Y.Z")
    if not isinstance(updated_at, str) or not updated_at.strip():
        raise ValueError(f"{file_path}: updated_at must be a non-empty string")
    _parse_updated_at(updated_at, file_path)

    if not isinstance(fail_on, str) or fail_on not in POLICY_BUNDLE_ALLOWED_FAIL_ON:
        raise ValueError(
            f"{file_path}: fail_on must be one of {sorted(POLICY_BUNDLE_ALLOWED_FAIL_ON)}"
        )

    payload["include_rules"] = _normalize_rule_list(include_rules, "include_rules", file_path)
    payload["ignore_rules"] = _normalize_rule_list(ignore_rules, "ignore_rules", file_path)

    if not isinstance(bundle_hash, str) or not re.match(r"^[0-9a-f]{64}$", bundle_hash):
        raise ValueError(f"{file_path}: bundle_hash must be a 64-char lowercase hex sha256")
    expected_hash = _compute_bundle_hash(payload)
    if bundle_hash != expected_hash:
        raise ValueError(
            f"{file_path}: bundle_hash is stale or invalid (expected {expected_hash}, got {bundle_hash})"
        )


def _validate_bundle_explain_policy_compatibility(repo_root: Path, payload: dict[str, Any]) -> None:
    bundle_name = str(payload["name"])
    script = repo_root / "skills" / "libro-wcag" / "scripts" / "run_accessibility_audit.py"
    workspace = repo_root / ".tmp-test" / "validate-policy-bundles" / bundle_name
    output_dir = workspace / "out"
    workspace.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = workspace / "bundle-compatibility.html"
    target.write_text("<!doctype html><html><head><title>x</title></head><body></body></html>", encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--target",
            str(target),
            "--output-dir",
            str(output_dir),
            "--summary-only",
            "--explain-policy",
            "--policy-bundle",
            bundle_name,
            "--skip-axe",
            "--skip-lighthouse",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(
            f"policy bundle explain-policy compatibility failed for {bundle_name}: "
            f"{completed.stdout}{completed.stderr}"
        )
    try:
        compact = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as err:
        raise ValueError(
            f"policy bundle explain-policy output is not valid JSON for {bundle_name}"
        ) from err

    policy_effective = compact.get("policy_effective")
    if not isinstance(policy_effective, dict):
        raise ValueError(f"policy bundle explain-policy output missing policy_effective for {bundle_name}")
    if policy_effective.get("bundle") != bundle_name:
        raise ValueError(f"policy bundle mismatch in policy_effective.bundle for {bundle_name}")
    if policy_effective.get("fail_on") != payload["fail_on"]:
        raise ValueError(
            f"policy bundle fail_on mismatch for {bundle_name}: "
            f"expected {payload['fail_on']}, got {policy_effective.get('fail_on')}"
        )
    if sorted(policy_effective.get("include_rules", [])) != sorted(payload["include_rules"]):
        raise ValueError(f"policy bundle include_rules mismatch for {bundle_name}")
    if sorted(policy_effective.get("ignore_rules", [])) != sorted(payload["ignore_rules"]):
        raise ValueError(f"policy bundle ignore_rules mismatch for {bundle_name}")


def validate_policy_bundles(repo_root: Path) -> None:
    bundles_dir = repo_root / "docs" / "policy-bundles"
    if not bundles_dir.exists():
        raise ValueError(f"Missing policy bundles directory: {bundles_dir}")
    bundle_files = sorted(bundles_dir.glob("*.json"))
    if not bundle_files:
        raise ValueError(f"No policy bundle artifacts found in {bundles_dir}")

    for file_path in bundle_files:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{file_path}: payload must be a JSON object")
        _validate_single_policy_bundle(file_path, payload)
        _validate_bundle_explain_policy_compatibility(repo_root, payload)


def main() -> int:
    args = parse_args()
    validate_skill(Path(args.skill_dir))
    print("Skill is valid!")
    if args.validate_policy_bundles:
        repo_root = Path(__file__).resolve().parents[1]
        validate_policy_bundles(repo_root)
        print("Policy bundles are valid!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
