#!/usr/bin/env python3
"""Policy control helpers for accessibility audit orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

POLICY_PRESETS: dict[str, dict[str, Any]] = {
    "strict": {
        "fail_on": "moderate",
        "include_rules": [],
        "ignore_rules": [],
        "description": "Fail on moderate+ unresolved findings with full rule coverage.",
    },
    "balanced": {
        "fail_on": "serious",
        "include_rules": [],
        "ignore_rules": [],
        "description": "Default CI balance for most repositories.",
    },
    "legacy": {
        "fail_on": "serious",
        "include_rules": [],
        "ignore_rules": ["meta-viewport"],
        "description": "Back-compat profile that ignores noisy viewport policy findings.",
    },
}

POLICY_BUNDLES: dict[str, dict[str, Any]] = {
    "strict-web-app": {
        "fail_on": "moderate",
        "include_rules": [],
        "ignore_rules": [],
        "description": "Strict default for modern web apps with full rule coverage.",
    },
    "legacy-content": {
        "fail_on": "serious",
        "include_rules": [],
        "ignore_rules": ["meta-viewport", "color-contrast"],
        "description": "Legacy content profile with deterministic ignore defaults for noisy debt.",
    },
    "marketing-site": {
        "fail_on": "serious",
        "include_rules": ["image-alt", "heading-order", "link-name", "button-name"],
        "ignore_rules": ["meta-viewport"],
        "description": "Marketing funnel profile focused on core content and navigation accessibility rules.",
    },
}

ALLOWED_POLICY_CONFIG_KEYS = {"report_format", "fail_on", "include_rules", "ignore_rules"}

POLICY_CONFIG_KEY_SPECS: dict[str, dict[str, Any]] = {
    "report_format": {
        "type": "string",
        "allowed_values": ["json", "sarif"],
        "description": "Primary machine-readable output format.",
    },
    "fail_on": {
        "type": "string",
        "allowed_values": ["critical", "serious", "moderate"],
        "description": "Policy gate threshold for unresolved findings.",
    },
    "include_rules": {
        "type": "list[string]",
        "allowed_values": "normalized rule ids",
        "description": "Allow-list for findings by normalized rule id.",
    },
    "ignore_rules": {
        "type": "list[string]",
        "allowed_values": "normalized rule ids",
        "description": "Ignore-list for findings by normalized rule id.",
    },
}


def _load_policy_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        raise ValueError(f"policy config file does not exist: {path}")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--policy-config must point to a JSON object")
    unknown_keys = sorted(set(payload) - ALLOWED_POLICY_CONFIG_KEYS)
    if unknown_keys:
        allowed = ", ".join(sorted(ALLOWED_POLICY_CONFIG_KEYS))
        raise ValueError(
            f'--policy-config contains unsupported keys: {", ".join(unknown_keys)} (allowed: {allowed})'
        )
    return payload


def _normalize_rule_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of rule ids")
    return [item.strip() for item in value if item.strip()]


def _resolve_policy_preset(name: str | None) -> dict[str, Any]:
    if not name:
        return {}
    preset = POLICY_PRESETS.get(name)
    if not preset:
        raise ValueError(f"unknown policy preset: {name}")
    return {
        "name": name,
        "fail_on": preset["fail_on"],
        "include_rules": list(preset["include_rules"]),
        "ignore_rules": list(preset["ignore_rules"]),
        "description": preset["description"],
    }


def _resolve_policy_bundle(name: str | None) -> dict[str, Any]:
    if not name:
        return {}
    bundle = POLICY_BUNDLES.get(name)
    if not bundle:
        raise ValueError(f"unknown policy bundle: {name}")
    return {
        "name": name,
        "fail_on": bundle["fail_on"],
        "include_rules": list(bundle["include_rules"]),
        "ignore_rules": list(bundle["ignore_rules"]),
        "description": bundle["description"],
    }


def _policy_presets_payload() -> dict[str, Any]:
    presets: list[dict[str, Any]] = []
    for name in sorted(POLICY_PRESETS):
        resolved = _resolve_policy_preset(name)
        presets.append(
            {
                "name": resolved["name"],
                "description": resolved["description"],
                "fail_on": resolved["fail_on"],
                "include_rules": resolved["include_rules"],
                "ignore_rules": resolved["ignore_rules"],
            }
        )
    return {"presets": presets}


def _policy_config_keys_payload() -> dict[str, Any]:
    keys: list[dict[str, Any]] = []
    for name in sorted(ALLOWED_POLICY_CONFIG_KEYS):
        details = POLICY_CONFIG_KEY_SPECS.get(name, {})
        keys.append(
            {
                "name": name,
                "type": details.get("type", "unknown"),
                "allowed_values": details.get("allowed_values", []),
                "description": details.get("description", ""),
            }
        )
    return {"keys": keys}


def _build_effective_policy(
    *,
    report_format: str,
    fail_on: str | None,
    include_rules: list[str],
    ignore_rules: list[str],
    policy_bundle: dict[str, Any],
    policy_preset: dict[str, Any],
    policy_config_path: str | None,
    policy_sources: dict[str, Any],
    fail_on_new_only: bool,
    baseline_report_path: str | None,
    baseline_signature_config: dict[str, Any],
    baseline_evidence_mode: str,
    waiver_expiry_mode: str,
    risk_calibration_mode: str,
    risk_calibration_source: str | None,
    stability_mode: str,
    stability_baseline: str | None,
    overlapping_rules: list[str],
) -> dict[str, Any]:
    return {
        "report_format": report_format,
        "fail_on": fail_on,
        "include_rules": include_rules,
        "ignore_rules": ignore_rules,
        "bundle": policy_bundle.get("name"),
        "preset": policy_preset.get("name"),
        "policy_config_path": policy_config_path,
        "sources": policy_sources,
        "fail_on_new_only": fail_on_new_only,
        "baseline_report_path": baseline_report_path,
        "baseline_signature": baseline_signature_config,
        "baseline_evidence_mode": baseline_evidence_mode,
        "waiver_expiry_mode": waiver_expiry_mode,
        "risk_calibration_mode": risk_calibration_mode,
        "risk_calibration_source": risk_calibration_source,
        "stability_mode": stability_mode,
        "stability_baseline": stability_baseline,
        "overlapping_rules": overlapping_rules,
        "rule_overlap_resolution": "ignore-rules-win",
    }


def _policy_value_source(
    cli_value: Any,
    config_value: Any,
    preset_value: Any,
    bundle_value: Any,
    default_label: str,
) -> str:
    if cli_value is not None:
        return "cli"
    if config_value is not None:
        return "policy-config"
    if preset_value is not None:
        return "policy-preset"
    if bundle_value is not None:
        return "policy-bundle"
    return default_label


def _build_rule_sources(
    bundle_rules: list[str],
    preset_rules: list[str],
    config_rules: list[str],
    cli_rules: list[str],
) -> dict[str, str]:
    sources: dict[str, str] = {}
    for rule in bundle_rules:
        if rule not in sources:
            sources[rule] = "policy-bundle"
    for rule in preset_rules:
        if rule not in sources:
            sources[rule] = "policy-preset"
    for rule in config_rules:
        if rule not in sources:
            sources[rule] = "policy-config"
    for rule in cli_rules:
        if rule not in sources:
            sources[rule] = "cli"
    return sources


def _resolve_effective_policy_path(path_value: str | None, output_dir: Path) -> Path | None:
    if path_value is None:
        return None
    if path_value == "AUTO":
        return output_dir / "wcag-effective-policy.json"
    return Path(path_value)


def _find_rule_policy_overlaps(include_rules: list[str], ignore_rules: list[str]) -> list[str]:
    include_set = {item for item in include_rules if item}
    ignore_set = {item for item in ignore_rules if item}
    return sorted(include_set & ignore_set)


def _merge_rule_list(*groups: list[str]) -> list[str]:
    ordered: list[str] = []
    for group in groups:
        for item in group:
            value = item.strip()
            if value and value not in ordered:
                ordered.append(value)
    return ordered


__all__ = [
    "ALLOWED_POLICY_CONFIG_KEYS",
    "POLICY_BUNDLES",
    "POLICY_CONFIG_KEY_SPECS",
    "POLICY_PRESETS",
    "_build_effective_policy",
    "_build_rule_sources",
    "_find_rule_policy_overlaps",
    "_load_policy_config",
    "_merge_rule_list",
    "_normalize_rule_list",
    "_policy_config_keys_payload",
    "_policy_presets_payload",
    "_policy_value_source",
    "_resolve_effective_policy_path",
    "_resolve_policy_bundle",
    "_resolve_policy_preset",
]
