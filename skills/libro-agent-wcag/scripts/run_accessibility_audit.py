#!/usr/bin/env python3
"""Run axe and Lighthouse scans, then emit normalized WCAG outputs."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import url2pathname

from auto_fix import (
    apply_report_fixes,
    supports_apply_fixes_target,
    target_to_local_path,
    write_diff,
    write_snapshot,
)
from wcag_workflow import normalize_report, resolve_contract, to_markdown_table, write_report_files

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_SCANNER_RETRY_ATTEMPTS = 1
DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS = 0.5
MAX_SCANNER_RETRY_BACKOFF_SECONDS = 5.0
ALLOWED_URL_SCHEMES = {"http", "https", "file"}
def _resolve_npx_executable() -> str:
    candidates = ["npx"]
    if os.name == "nt":
        # subprocess on Windows should prefer cmd shim to avoid shell resolution mismatches.
        candidates = ["npx.cmd", "npx.exe", "npx"]
    for candidate in candidates:
        if shutil.which(candidate):
            return candidate
    return "npx"


NPX_EXECUTABLE = _resolve_npx_executable()
PREFLIGHT_TOOL_CHECKS = (
    ("npx", [NPX_EXECUTABLE, "--version"]),
    ("@axe-core/cli", [NPX_EXECUTABLE, "--no-install", "@axe-core/cli", "--version"]),
    ("lighthouse", [NPX_EXECUTABLE, "--no-install", "lighthouse", "--version"]),
)
SEVERITY_RANK = {"critical": 4, "serious": 3, "moderate": 2, "minor": 1, "info": 0}
FAIL_ON_EXIT_CODES = {"critical": 42, "serious": 43, "moderate": 44}
FINDING_SORT_MODES = {"severity", "rule", "target"}
BASELINE_TARGET_NORMALIZATION_MODES = {"none", "host-path", "path-only"}
BASELINE_SELECTOR_CANONICALIZATION_MODES = {"none", "basic"}
DEBT_STATE_NEW = "new"
DEBT_STATE_ACCEPTED = "accepted"
DEBT_STATE_RETIRED = "retired"
REPORT_SCHEMA_NAME = "libro-agent-wcag-report"
REPORT_SCHEMA_VERSION = "1.0.0"
REPORT_SCHEMA_FILENAME = f"wcag-report-{REPORT_SCHEMA_VERSION}.schema.json"
REPORT_SCHEMA_SOURCE_PATH = Path(__file__).resolve().parents[1] / "schemas" / REPORT_SCHEMA_FILENAME
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


def _extract_version_line(output: str) -> str | None:
    for line in output.splitlines():
        value = line.strip()
        if value:
            return value
    return None


def _build_version_provenance(
    *,
    source: str,
    command: str,
    resolved_command: str,
    version: str,
) -> dict[str, str]:
    return {
        "source": source,
        "command": command,
        "resolved_command": resolved_command,
        "version": version,
    }


def _run_command(command: list[str], timeout_seconds: int) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"command timed out after {timeout_seconds} seconds"
    except FileNotFoundError as err:
        return False, f"command not found: {err.filename or command[0]}"
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if completed.returncode == 0:
        return True, stdout
    error = stderr.strip() or stdout.strip() or "unknown error"
    return False, error


def _is_transient_scanner_error(error_message: str | None) -> bool:
    text = (error_message or "").lower()
    return any(
        token in text
        for token in (
            "timed out",
            "econnreset",
            "econnrefused",
            "eai_again",
            "temporarily unavailable",
            "temporary failure",
            "network",
        )
    )


def _run_scanner_with_retry(
    scanner: str,
    runner: Callable[[], tuple[dict[str, Any] | None, str | None]],
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    attempts = max(1, retry_attempts)
    initial_backoff = max(0.0, retry_backoff_seconds)
    transient_error = False
    data: dict[str, Any] | None = None
    error: str | None = None

    for attempt in range(1, attempts + 1):
        data, error = runner()
        if data is not None and not error:
            return data, None, {
                "tool": scanner,
                "attempts": attempt,
                "retry_count": attempt - 1,
                "succeeded": True,
                "last_error": "",
                "transient_error": False,
            }

        transient_error = _is_transient_scanner_error(error)
        should_retry = attempt < attempts and transient_error
        if not should_retry:
            break

        if initial_backoff > 0:
            delay = min(
                initial_backoff * (2 ** (attempt - 1)),
                MAX_SCANNER_RETRY_BACKOFF_SECONDS,
            )
            time.sleep(delay)

    return data, error, {
        "tool": scanner,
        "attempts": attempt,
        "retry_count": attempt - 1,
        "succeeded": False,
        "last_error": error or "unknown error",
        "transient_error": transient_error,
    }


def _try_run_axe(
    target: str,
    output_dir: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, str | None]:
    axe_json = output_dir / "axe.raw.json"
    command = [NPX_EXECUTABLE, "@axe-core/cli", target, "--save", str(axe_json)]
    ok, result = _run_command(command, timeout_seconds)
    if not ok:
        return None, result
    if not axe_json.exists():
        return None, "axe did not generate output json"
    with axe_json.open("r", encoding="utf-8") as handle:
        return json.load(handle), None


def _try_run_lighthouse(
    target: str,
    output_dir: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, str | None]:
    lighthouse_json = output_dir / "lighthouse.raw.json"
    command = [
        NPX_EXECUTABLE,
        "lighthouse",
        target,
        "--only-categories=accessibility",
        "--output=json",
        f"--output-path={lighthouse_json}",
        "--chrome-flags=--headless=new",
    ]
    ok, result = _run_command(command, timeout_seconds)
    if not ok:
        return None, result
    if not lighthouse_json.exists():
        return None, "lighthouse did not generate output json"
    with lighthouse_json.open("r", encoding="utf-8") as handle:
        return json.load(handle), None


def _resolve_target_for_scanners(target: str) -> str:
    local_path = Path(target)
    if local_path.exists():
        return local_path.resolve().as_uri()
    parsed = urlparse(target)
    if parsed.scheme:
        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            raise ValueError(f"Unsupported target scheme: {parsed.scheme}")
        if parsed.scheme == "file":
            if parsed.netloc not in {"", "localhost"}:
                raise ValueError(f"Unsupported file target host: {parsed.netloc}")
            file_path = Path(url2pathname(parsed.path))
            if not file_path.exists():
                raise ValueError(f"Target file does not exist: {target}")
        return target
    if "://" in target:
        raise ValueError(f"Unsupported target scheme in: {target}")
    raise ValueError(f"Target must be an existing local file or a valid URL: {target}")


def _tool_available(tool: str) -> bool:
    return shutil.which(tool) is not None


def run_preflight_checks(timeout_seconds: int) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    tools: dict[str, dict[str, Any]] = {}
    ok = True
    for name, command in PREFLIGHT_TOOL_CHECKS:
        command_text = " ".join(command)
        resolved_command = shutil.which(command[0]) or ""
        if not _tool_available(command[0]):
            message = f'{command[0]} is not available in PATH'
            version_provenance = _build_version_provenance(
                source="binary-missing",
                command=command_text,
                resolved_command=resolved_command,
                version="",
            )
            entry = {
                "tool": name,
                "status": "error",
                "message": message,
                "command": command_text,
                "resolved_command": resolved_command,
                "version": "",
                "version_provenance": version_provenance,
            }
            results.append(entry)
            tools[name] = {
                "status": "error",
                "command": command_text,
                "resolved_command": resolved_command,
                "version": "",
                "message": message,
                "version_provenance": version_provenance,
            }
            ok = False
            continue
        command_ok, output = _run_command(command, timeout_seconds)
        status = "ok" if command_ok else "error"
        message = (output or "").strip() or ("available" if command_ok else "check failed")
        version = _extract_version_line(output) if command_ok else ""
        version_provenance = _build_version_provenance(
            source="command-output-first-line" if command_ok else "command-error",
            command=command_text,
            resolved_command=resolved_command,
            version=version or "",
        )
        entry = {
            "tool": name,
            "status": status,
            "message": message,
            "command": command_text,
            "resolved_command": resolved_command,
            "version": version or "",
            "version_provenance": version_provenance,
        }
        results.append(entry)
        tools[name] = {
            "status": status,
            "command": command_text,
            "resolved_command": resolved_command,
            "version": version or "",
            "message": message,
            "version_provenance": version_provenance,
        }
        ok = ok and command_ok
    return {"ok": ok, "checks": results, "tools": tools}


def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def _load_policy_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        raise ValueError(f'policy config file does not exist: {path}')
    payload = json.loads(config_path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('--policy-config must point to a JSON object')
    unknown_keys = sorted(set(payload) - ALLOWED_POLICY_CONFIG_KEYS)
    if unknown_keys:
        allowed = ", ".join(sorted(ALLOWED_POLICY_CONFIG_KEYS))
        raise ValueError(
            f'--policy-config contains unsupported keys: {", ".join(unknown_keys)} (allowed: {allowed})'
        )
    return payload


def _load_baseline_report(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    baseline_path = Path(path)
    if not baseline_path.exists():
        raise ValueError(f'baseline report file does not exist: {path}')
    payload = json.loads(baseline_path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('--baseline-report must point to a JSON object')
    findings = payload.get('findings')
    if findings is None:
        payload['findings'] = []
    elif not isinstance(findings, list):
        raise ValueError('--baseline-report JSON must include findings as a list')
    return payload

def _normalize_rule_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f'{name} must be a list of rule ids')
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


def _collect_scanner_rule_ids(axe_data: dict[str, Any] | None, lighthouse_data: dict[str, Any] | None) -> list[str]:
    rule_ids: set[str] = set()
    if isinstance(axe_data, dict):
        for violation in axe_data.get("violations", []):
            if not isinstance(violation, dict):
                continue
            rule_id = str(violation.get("id", "")).strip()
            if rule_id:
                rule_ids.add(rule_id)
    if isinstance(lighthouse_data, dict):
        audits = lighthouse_data.get("audits", {})
        if isinstance(audits, dict):
            for audit_id in audits:
                if isinstance(audit_id, str):
                    value = audit_id.strip()
                    if value:
                        rule_ids.add(value)
    return sorted(rule_ids)


def _build_scanner_capabilities(
    preflight: dict[str, Any],
    report: dict[str, Any],
    args: argparse.Namespace,
    axe_data: dict[str, Any] | None,
    lighthouse_data: dict[str, Any] | None,
) -> dict[str, Any]:
    tools = preflight.get("tools", {})
    run_tools = report.get("run_meta", {}).get("tools", {})
    available_rules = _collect_scanner_rule_ids(axe_data, lighthouse_data)
    scanner_map = {
        "axe": {
            "requested": not args.skip_axe,
            "mocked": bool(args.mock_axe_json),
            "preflight_tool": "@axe-core/cli",
        },
        "lighthouse": {
            "requested": not args.skip_lighthouse,
            "mocked": bool(args.mock_lighthouse_json),
            "preflight_tool": "lighthouse",
        },
    }
    scanners: dict[str, Any] = {}
    for scanner, config in scanner_map.items():
        preflight_tool = config["preflight_tool"]
        preflight_entry = tools.get(preflight_tool, {})
        preflight_status = str(preflight_entry.get("status", "unknown"))
        input_mode = "skipped"
        if config["mocked"]:
            input_mode = "mock"
        elif config["requested"]:
            input_mode = "live"
        scanners[scanner] = {
            "requested": config["requested"],
            "input_mode": input_mode,
            "preflight_status": preflight_status,
            "run_status": run_tools.get(scanner, "unknown"),
            "available": bool(config["mocked"] or preflight_status == "ok"),
        }

    return {
        "scanners": scanners,
        "available_rules": available_rules,
        "available_rule_count": len(available_rules),
    }

def _rebuild_summary(report: dict[str, Any]) -> None:
    findings = report.get('findings', [])
    fixes = report.get('fixes', [])
    summary = report.setdefault('summary', {})
    summary['total_findings'] = len(findings)
    summary['fixed_findings'] = sum(1 for item in findings if item.get('status') == 'fixed')
    summary['auto_fixed_count'] = summary['fixed_findings']
    summary['needs_manual_review'] = sum(1 for item in findings if item.get('status') == 'needs-review')
    summary['manual_required_count'] = sum(1 for item in findings if item.get('manual_review_required'))
    summary.setdefault('diff_summary', [])
    summary.setdefault('before_after_targets', [])
    summary.setdefault('change_summary', [])
    summary.setdefault('fix_blockers', [])
    summary['remediation_lifecycle'] = {
        'planned': sum(1 for item in fixes if item.get('status') == 'planned'),
        'implemented': sum(1 for item in fixes if item.get('status') == 'implemented'),
        'verified': sum(1 for item in fixes if item.get('status') == 'verified'),
        'manual_review_required': sum(1 for item in fixes if item.get('manual_review_required')),
    }



def _coerce_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float) and value.is_integer():
        return int(value) if value > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            parsed = int(text)
            return parsed if parsed > 0 else None
    return None


def _finding_sort_key(finding: dict[str, Any], sort_mode: str) -> tuple[Any, ...]:
    severity = str(finding.get('severity', 'info'))
    severity_rank = SEVERITY_RANK.get(severity, 0)
    rule_id = str(finding.get('rule_id', ''))
    target = str(finding.get('changed_target', ''))
    source = str(finding.get('source', ''))
    issue_id = str(finding.get('id', ''))
    source_line = _coerce_positive_int(finding.get('source_line')) or 10**9
    source_column = _coerce_positive_int(finding.get('source_column')) or 10**9

    if sort_mode == 'rule':
        return (rule_id, target, -severity_rank, source_line, source_column, source, issue_id)
    if sort_mode == 'target':
        return (target, rule_id, -severity_rank, source_line, source_column, source, issue_id)
    return (-severity_rank, rule_id, target, source_line, source_column, source, issue_id)


def _sort_report_findings(report: dict[str, Any], sort_mode: str) -> None:
    findings = sorted(
        report.get('findings', []),
        key=lambda item: _finding_sort_key(item, sort_mode),
    )
    report['findings'] = findings


def _cap_report_findings(report: dict[str, Any], max_findings: int) -> dict[str, int]:
    if max_findings <= 0:
        raise ValueError('--max-findings must be >= 1')

    findings = report.get('findings', [])
    before_count = len(findings)
    if before_count <= max_findings:
        return {'before': before_count, 'after': before_count, 'truncated': 0}

    capped = findings[:max_findings]
    kept_ids = {item.get('id') for item in capped}
    report['findings'] = capped
    report['fixes'] = [item for item in report.get('fixes', []) if item.get('finding_id') in kept_ids]
    report['citations'] = [item for item in report.get('citations', []) if item.get('finding_id') in kept_ids]

    summary = report.setdefault('summary', {})
    summary['change_summary'] = [
        item for item in summary.get('change_summary', []) if item.get('finding_id') in kept_ids
    ]
    summary['fix_blockers'] = [
        item for item in summary.get('fix_blockers', []) if item.get('finding_id') in kept_ids
    ]
    _rebuild_summary(report)
    return {'before': before_count, 'after': len(capped), 'truncated': before_count - len(capped)}


def _build_compact_summary(
    report: dict[str, Any],
    report_format: str,
    machine_output: Path,
    output_md: Path,
    should_fail: bool,
    fail_on: str | None,
    exit_code: int,
) -> dict[str, Any]:
    summary = report.get('summary', {})
    compact: dict[str, Any] = {
        'status': 'failed' if should_fail else 'ok',
        'report_format': report_format,
        'machine_output': str(machine_output),
        'markdown_output': str(output_md),
        'total_findings': summary.get('total_findings', 0),
        'fixed_findings': summary.get('fixed_findings', 0),
        'manual_required_count': summary.get('manual_required_count', 0),
    }
    if fail_on:
        compact['policy_gate'] = {
            'fail_on': fail_on,
            'failed': should_fail,
            'exit_code': exit_code if should_fail else 0,
            'scope': report.get('run_meta', {}).get('policy_gate', {}).get('scope', 'all-unresolved'),
        }
    baseline_diff = report.get('run_meta', {}).get('baseline_diff')
    if baseline_diff:
        compact['baseline_diff'] = {
            'introduced_count': baseline_diff.get('introduced_count', 0),
            'resolved_count': baseline_diff.get('resolved_count', 0),
            'persistent_count': baseline_diff.get('persistent_count', 0),
        }
    findings_cap = report.get('run_meta', {}).get('findings_cap')
    if findings_cap:
        compact['findings_cap'] = findings_cap
    scanner_capabilities = summary.get('scanner_capabilities')
    if scanner_capabilities:
        compact['scanner_capabilities'] = scanner_capabilities
    effective_policy = report.get('run_meta', {}).get('policy_effective')
    if effective_policy:
        compact['policy_effective'] = effective_policy
    policy_rule_overlap = report.get('run_meta', {}).get('policy_rule_overlap')
    if policy_rule_overlap:
        compact['policy_rule_overlap'] = policy_rule_overlap
    return compact

def _apply_rule_policy(
    report: dict[str, Any],
    include_rules: list[str],
    ignore_rules: list[str],
) -> tuple[int, int]:
    include_set = {item for item in include_rules if item}
    ignore_set = {item for item in ignore_rules if item}
    finding_ids = {
        finding['id']
        for finding in report.get('findings', [])
        if (not include_set or finding.get('rule_id') in include_set)
        and finding.get('rule_id') not in ignore_set
    }
    before_count = len(report.get('findings', []))
    report['findings'] = [item for item in report.get('findings', []) if item.get('id') in finding_ids]
    report['fixes'] = [item for item in report.get('fixes', []) if item.get('finding_id') in finding_ids]
    report['citations'] = [item for item in report.get('citations', []) if item.get('finding_id') in finding_ids]

    summary = report.setdefault('summary', {})
    summary['change_summary'] = [
        item for item in summary.get('change_summary', []) if item.get('finding_id') in finding_ids
    ]
    summary['fix_blockers'] = [
        item for item in summary.get('fix_blockers', []) if item.get('finding_id') in finding_ids
    ]
    _rebuild_summary(report)
    return before_count, len(report.get('findings', []))


def _sarif_level_from_severity(severity: str) -> str:
    if severity in {'critical', 'serious'}:
        return 'error'
    if severity == 'moderate':
        return 'warning'
    return 'note'

def _finding_signature(finding: dict[str, Any]) -> str:
    rule_id = str(finding.get('rule_id', '')).strip()
    changed_target = str(finding.get('changed_target', '')).strip()
    return f'{rule_id}|{changed_target}'


def _normalize_signature_target(target: str, mode: str) -> str:
    value = target.strip()
    if not value:
        return ''
    if mode == 'none':
        return value

    if re.match(r'^[A-Za-z]:[\\/]', value):
        host = ''
        path = value.replace('\\', '/')
    else:
        parsed = urlparse(value)
        if parsed.scheme:
            host = (parsed.netloc or '').lower()
            path = parsed.path or '/'
        else:
            host = ''
            path = value.replace('\\', '/')

    path = re.sub(r'/+', '/', path).rstrip('/') or '/'
    if re.match(r'^/[A-Za-z]:/', path):
        path = path[1:]
    if mode == 'path-only':
        return path
    if mode == 'host-path':
        return f'{host}{path}' if host else path
    return value


def _canonicalize_signature_selector(selector: str, mode: str) -> str:
    value = selector.strip()
    if mode == 'none' or not value:
        return value
    value = re.sub(r'\s+', ' ', value)
    value = re.sub(r'\s*([>+~,])\s*', r'\1', value)
    value = re.sub(r'\[\s*', '[', value)
    value = re.sub(r'\s*\]', ']', value)
    return value.strip()


def _build_baseline_signature_config(args: argparse.Namespace) -> dict[str, Any]:
    return {
        'include_target_in_signature': bool(args.baseline_include_target),
        'target_normalization': args.baseline_target_normalization,
        'selector_canonicalization': args.baseline_selector_canonicalization,
    }


def _finding_signature_with_config(
    finding: dict[str, Any],
    signature_config: dict[str, Any],
    report_target: str,
) -> str:
    rule_id = str(finding.get('rule_id', '')).strip()
    selector = _canonicalize_signature_selector(
        str(finding.get('changed_target', '')).strip(),
        str(signature_config.get('selector_canonicalization', 'none')),
    )
    components = [rule_id]
    if signature_config.get('include_target_in_signature'):
        target = _normalize_signature_target(
            report_target,
            str(signature_config.get('target_normalization', 'none')),
        )
        components.append(target)
    components.append(selector)
    return '|'.join(components)


def _unresolved_finding_signatures(
    report: dict[str, Any],
    signature_config: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    effective_signature_config = signature_config or {
        'include_target_in_signature': False,
        'target_normalization': 'none',
        'selector_canonicalization': 'none',
    }
    report_target = str(report.get('target', {}).get('value', '')).strip()
    signatures: dict[str, dict[str, Any]] = {}
    for finding in report.get('findings', []):
        if finding.get('status') == 'fixed':
            continue
        signatures[_finding_signature_with_config(finding, effective_signature_config, report_target)] = finding
    return signatures


def _build_baseline_diff(
    current_report: dict[str, Any],
    baseline_report: dict[str, Any],
    signature_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_signature_config = signature_config or {
        'include_target_in_signature': False,
        'target_normalization': 'none',
        'selector_canonicalization': 'none',
    }
    current_findings = _unresolved_finding_signatures(current_report, effective_signature_config)
    baseline_findings = _unresolved_finding_signatures(baseline_report, effective_signature_config)
    current_keys = set(current_findings)
    baseline_keys = set(baseline_findings)
    introduced_keys = sorted(current_keys - baseline_keys)
    resolved_keys = sorted(baseline_keys - current_keys)
    persistent_keys = sorted(current_keys & baseline_keys)

    return {
        'current_unresolved_count': len(current_keys),
        'baseline_unresolved_count': len(baseline_keys),
        'introduced_count': len(introduced_keys),
        'resolved_count': len(resolved_keys),
        'persistent_count': len(persistent_keys),
        'introduced_signatures': introduced_keys,
        'resolved_signatures': resolved_keys,
        'persistent_signatures': persistent_keys,
        'introduced_findings': [current_findings[key] for key in introduced_keys],
        'signature_config': effective_signature_config,
    }


def _build_debt_transition_summary(baseline_diff: dict[str, Any]) -> dict[str, Any]:
    introduced_signatures = list(baseline_diff.get('introduced_signatures', []))
    persistent_signatures = list(baseline_diff.get('persistent_signatures', []))
    resolved_signatures = list(baseline_diff.get('resolved_signatures', []))
    return {
        DEBT_STATE_NEW: {
            'count': len(introduced_signatures),
            'signatures': introduced_signatures,
        },
        DEBT_STATE_ACCEPTED: {
            'count': len(persistent_signatures),
            'signatures': persistent_signatures,
        },
        DEBT_STATE_RETIRED: {
            'count': len(resolved_signatures),
            'signatures': resolved_signatures,
        },
    }


def _tag_findings_with_debt_state(
    report: dict[str, Any],
    baseline_diff: dict[str, Any],
    signature_config: dict[str, Any],
) -> None:
    findings = report.get('findings')
    if not isinstance(findings, list):
        return
    report_target = str(report.get('target', {}).get('value', '')).strip()
    introduced = set(baseline_diff.get('introduced_signatures', []))
    persistent = set(baseline_diff.get('persistent_signatures', []))
    resolved = set(baseline_diff.get('resolved_signatures', []))
    for finding in findings:
        signature = _finding_signature_with_config(finding, signature_config, report_target)
        if signature in introduced:
            finding['debt_state'] = DEBT_STATE_NEW
        elif signature in persistent:
            finding['debt_state'] = DEBT_STATE_ACCEPTED
        elif signature in resolved:
            finding['debt_state'] = DEBT_STATE_RETIRED


def _stage_report_schema_artifact(output_dir: Path) -> tuple[dict[str, Any], Path]:
    if not REPORT_SCHEMA_SOURCE_PATH.exists():
        raise FileNotFoundError(f'report schema file is missing: {REPORT_SCHEMA_SOURCE_PATH}')
    schema_dir = output_dir / 'schemas'
    schema_dir.mkdir(parents=True, exist_ok=True)
    staged_path = schema_dir / REPORT_SCHEMA_FILENAME
    staged_path.write_text(REPORT_SCHEMA_SOURCE_PATH.read_text(encoding='utf-8'), encoding='utf-8')
    metadata = {
        'name': REPORT_SCHEMA_NAME,
        'version': REPORT_SCHEMA_VERSION,
        'artifact': str(staged_path),
        'compatibility': f"^{REPORT_SCHEMA_VERSION.split('.')[0]}.0.0",
    }
    return metadata, staged_path

def _report_to_sarif(report: dict[str, Any], contract_target: str, local_target: Path | None) -> dict[str, Any]:
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    location_uri = local_target.as_posix() if local_target else contract_target

    for finding in report.get('findings', []):
        rule_id = str(finding.get('rule_id', 'unknown'))
        if rule_id not in rules:
            rules[rule_id] = {
                'id': rule_id,
                'name': rule_id,
                'shortDescription': {'text': rule_id},
                'properties': {
                    'severity': finding.get('severity', 'info'),
                    'wcag': finding.get('sc', []),
                },
            }
        message_parts = [str(finding.get('current', rule_id))]
        selector = str(finding.get('changed_target', '')).strip()
        if selector and selector != 'unknown':
            message_parts.append(f'selector: {selector}')

        physical_location: dict[str, Any] = {
            'artifactLocation': {
                'uri': location_uri,
            }
        }
        source_line = _coerce_positive_int(finding.get('source_line'))
        source_column = _coerce_positive_int(finding.get('source_column'))
        if source_line is not None:
            region: dict[str, int] = {'startLine': source_line}
            if source_column is not None:
                region['startColumn'] = source_column
            physical_location['region'] = region

        results.append(
            {
                'ruleId': rule_id,
                'level': _sarif_level_from_severity(str(finding.get('severity', 'info'))),
                'message': {'text': ' | '.join(message_parts)},
                'locations': [
                    {
                        'physicalLocation': physical_location,
                    }
                ],
                'properties': {
                    'finding_id': finding.get('id'),
                    'status': finding.get('status'),
                    'sc': finding.get('sc', []),
                    'source_line': source_line,
                    'source_column': source_column,
                },
            }
        )

    return {
        '$schema': 'https://json.schemastore.org/sarif-2.1.0.json',
        'version': '2.1.0',
        'runs': [
            {
                'tool': {
                    'driver': {
                        'name': 'libro-agent-wcag',
                        'rules': list(rules.values()),
                    }
                },
                'results': results,
            }
        ],
    }


def _resolve_fail_threshold(report: dict[str, Any], fail_on: str) -> tuple[bool, int]:
    threshold_rank = SEVERITY_RANK[fail_on]
    for finding in report.get('findings', []):
        if finding.get('status') == 'fixed':
            continue
        severity = str(finding.get('severity', 'info'))
        if SEVERITY_RANK.get(severity, 0) >= threshold_rank:
            return True, FAIL_ON_EXIT_CODES[fail_on]
    return False, 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run WCAG audit with axe+Lighthouse.")
    parser.add_argument("--task-mode", default="modify", choices=["create", "modify"])
    parser.add_argument(
        "--execution-mode",
        default="suggest-only",
        choices=["audit-only", "suggest-only", "apply-fixes"],
    )
    parser.add_argument("--wcag-version", default="2.1", choices=["2.0", "2.1", "2.2"])
    parser.add_argument("--conformance-level", default="AA", choices=["A", "AA", "AAA"])
    parser.add_argument("--target")
    parser.add_argument("--output-language", default="zh-TW")
    parser.add_argument("--output-dir", default="out")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--report-format",
        choices=["json", "sarif"],
        default=None,
        help="Primary machine-readable output format.",
    )
    parser.add_argument(
        "--fail-on",
        choices=["critical", "serious", "moderate"],
        default=None,
        help="Fail with deterministic exit code when unresolved findings reach this severity.",
    )
    parser.add_argument(
        "--include-rule",
        action="append",
        default=[],
        help="Include only specific normalized rule ids (repeatable).",
    )
    parser.add_argument(
        "--ignore-rule",
        action="append",
        default=[],
        help="Ignore specific normalized rule ids (repeatable).",
    )
    parser.add_argument(
        "--policy-config",
        help="Optional JSON file with report_format/fail_on/include_rules/ignore_rules.",
    )
    parser.add_argument(
        "--policy-preset",
        choices=sorted(POLICY_PRESETS),
        default=None,
        help="Optional policy preset (strict|balanced|legacy) for deterministic fail-on and rule filters.",
    )
    parser.add_argument(
        "--policy-bundle",
        choices=sorted(POLICY_BUNDLES),
        default=None,
        help="Optional policy bundle template (strict-web-app|legacy-content|marketing-site).",
    )
    parser.add_argument(
        "--list-policy-presets",
        action="store_true",
        help="Print available policy presets and exit.",
    )
    parser.add_argument(
        "--list-policy-config-keys",
        action="store_true",
        help="Print supported --policy-config keys and exit.",
    )
    parser.add_argument(
        "--explain-policy",
        action="store_true",
        help="Include effective merged policy settings in run metadata and summary output.",
    )
    parser.add_argument(
        "--strict-rule-overlap",
        action="store_true",
        help="Fail when any rule id appears in both include and ignore policy lists.",
    )
    parser.add_argument(
        "--write-effective-policy",
        nargs="?",
        const="AUTO",
        default=None,
        help="Write effective merged policy JSON (optional path; defaults to <output-dir>/wcag-effective-policy.json).",
    )
    parser.add_argument(
        "--baseline-report",
        help="Optional prior JSON report to compare unresolved debt and detect newly introduced findings.",
    )
    parser.add_argument(
        "--baseline-include-target",
        action="store_true",
        help="Include normalized report target value in baseline signatures for stricter comparison.",
    )
    parser.add_argument(
        "--baseline-target-normalization",
        choices=sorted(BASELINE_TARGET_NORMALIZATION_MODES),
        default="none",
        help="Normalization mode for report target when --baseline-include-target is enabled.",
    )
    parser.add_argument(
        "--baseline-selector-canonicalization",
        choices=sorted(BASELINE_SELECTOR_CANONICALIZATION_MODES),
        default="none",
        help="Selector canonicalization mode used when building baseline signatures.",
    )
    parser.add_argument(
        "--fail-on-new-only",
        action="store_true",
        help="When used with --fail-on and --baseline-report, fail only on newly introduced debt.",
    )
    parser.add_argument(
        "--scanner-retry-attempts",
        type=int,
        default=DEFAULT_SCANNER_RETRY_ATTEMPTS,
        help="Retry attempts per scanner for transient runtime failures (minimum: 1).",
    )
    parser.add_argument(
        "--scanner-retry-backoff-seconds",
        type=float,
        default=DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS,
        help="Initial retry backoff in seconds for transient scanner failures.",
    )
    parser.add_argument("--skip-axe", action="store_true")
    parser.add_argument("--skip-lighthouse", action="store_true")
    parser.add_argument("--mock-axe-json")
    parser.add_argument("--mock-lighthouse-json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--max-findings",
        type=int,
        default=None,
        help="Limit findings included in output artifacts after deterministic sorting.",
    )
    parser.add_argument(
        "--sort-findings",
        choices=sorted(FINDING_SORT_MODES),
        default="severity",
        help="Deterministic sort mode for report findings before optional truncation.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print compact JSON summary to stdout while still writing full report artifacts.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Check runtime tooling availability (npx, axe, lighthouse) and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_policy_presets:
        print(json.dumps(_policy_presets_payload(), ensure_ascii=False, indent=2))
        return 0
    if args.list_policy_config_keys:
        print(json.dumps(_policy_config_keys_payload(), ensure_ascii=False, indent=2))
        return 0
    if not args.target and not args.preflight_only:
        raise ValueError('--target is required unless --list-policy-presets or --list-policy-config-keys is used')

    policy_config = _load_policy_config(args.policy_config)
    baseline_report = _load_baseline_report(args.baseline_report)
    policy_bundle = _resolve_policy_bundle(args.policy_bundle)
    policy_preset = _resolve_policy_preset(args.policy_preset)
    config_report_format = policy_config.get('report_format')
    config_fail_on = policy_config.get('fail_on')
    config_include = _normalize_rule_list(policy_config.get('include_rules'), 'include_rules')
    config_ignore = _normalize_rule_list(policy_config.get('ignore_rules'), 'ignore_rules')

    if config_report_format and config_report_format not in {'json', 'sarif'}:
        raise ValueError('policy-config report_format must be one of: json, sarif')
    if config_fail_on and config_fail_on not in {'critical', 'serious', 'moderate'}:
        raise ValueError('policy-config fail_on must be one of: critical, serious, moderate')

    bundle_fail_on = policy_bundle.get('fail_on')
    bundle_include = _normalize_rule_list(policy_bundle.get('include_rules'), 'bundle.include_rules')
    bundle_ignore = _normalize_rule_list(policy_bundle.get('ignore_rules'), 'bundle.ignore_rules')

    preset_fail_on = policy_preset.get('fail_on')
    preset_include = _normalize_rule_list(policy_preset.get('include_rules'), 'preset.include_rules')
    preset_ignore = _normalize_rule_list(policy_preset.get('ignore_rules'), 'preset.ignore_rules')

    cli_include_rules = [item.strip() for item in args.include_rule if item.strip()]
    cli_ignore_rules = [item.strip() for item in args.ignore_rule if item.strip()]

    report_format = args.report_format or config_report_format or 'json'
    fail_on = args.fail_on or config_fail_on or preset_fail_on or bundle_fail_on
    include_rules = _merge_rule_list(
        bundle_include,
        preset_include,
        config_include,
        cli_include_rules,
    )
    ignore_rules = _merge_rule_list(
        bundle_ignore,
        preset_ignore,
        config_ignore,
        cli_ignore_rules,
    )
    overlapping_rules = _find_rule_policy_overlaps(include_rules, ignore_rules)
    if overlapping_rules and args.strict_rule_overlap:
        raise ValueError(
            '--strict-rule-overlap detected rule ids present in both include and ignore lists: '
            + ", ".join(overlapping_rules)
        )
    policy_sources = {
        'report_format': _policy_value_source(args.report_format, config_report_format, None, None, 'default'),
        'fail_on': _policy_value_source(args.fail_on, config_fail_on, preset_fail_on, bundle_fail_on, 'unset'),
        'include_rules': _build_rule_sources(bundle_include, preset_include, config_include, cli_include_rules),
        'ignore_rules': _build_rule_sources(bundle_ignore, preset_ignore, config_ignore, cli_ignore_rules),
    }

    if args.skip_axe and args.mock_axe_json:
        raise ValueError('--skip-axe cannot be combined with --mock-axe-json')
    if args.skip_lighthouse and args.mock_lighthouse_json:
        raise ValueError('--skip-lighthouse cannot be combined with --mock-lighthouse-json')
    if args.dry_run and args.execution_mode != 'apply-fixes':
        raise ValueError('--dry-run is only supported when --execution-mode is apply-fixes')
    if args.scanner_retry_attempts < 1:
        raise ValueError('--scanner-retry-attempts must be >= 1')
    if args.scanner_retry_backoff_seconds < 0:
        raise ValueError('--scanner-retry-backoff-seconds must be >= 0')
    if args.max_findings is not None and args.max_findings < 1:
        raise ValueError('--max-findings must be >= 1')
    if args.fail_on_new_only and not args.fail_on:
        raise ValueError('--fail-on-new-only requires --fail-on')
    if args.fail_on_new_only and not args.baseline_report:
        raise ValueError('--fail-on-new-only requires --baseline-report')

    if args.preflight_only:
        preflight = run_preflight_checks(args.timeout)
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0 if preflight["ok"] else 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    effective_policy_output = _resolve_effective_policy_path(args.write_effective_policy, output_dir)
    schema_metadata, staged_schema_path = _stage_report_schema_artifact(output_dir)
    baseline_signature_config = _build_baseline_signature_config(args)
    effective_policy = _build_effective_policy(
        report_format=report_format,
        fail_on=fail_on,
        include_rules=include_rules,
        ignore_rules=ignore_rules,
        policy_bundle=policy_bundle,
        policy_preset=policy_preset,
        policy_config_path=args.policy_config,
        policy_sources=policy_sources,
        fail_on_new_only=bool(args.fail_on_new_only),
        baseline_report_path=args.baseline_report,
        baseline_signature_config=baseline_signature_config,
        overlapping_rules=overlapping_rules,
    )

    contract = resolve_contract(
        {
            "task_mode": args.task_mode,
            "execution_mode": args.execution_mode,
            "wcag_version": args.wcag_version,
            "conformance_level": args.conformance_level,
            "target": args.target,
            "output_language": args.output_language,
        }
    )
    local_target = target_to_local_path(contract.target)
    scanner_target = _resolve_target_for_scanners(contract.target)

    preflight_required = not (
        (args.skip_axe or args.mock_axe_json) and (args.skip_lighthouse or args.mock_lighthouse_json)
    )
    if preflight_required:
        preflight = run_preflight_checks(args.timeout)
    else:
        preflight = {
            "ok": True,
            "checks": [
                {
                    "tool": "runtime",
                    "status": "skipped",
                    "message": "scanner tooling preflight skipped due to mock or skip flags",
                    "command": "",
                    "resolved_command": "",
                    "version": "",
                    "version_provenance": {
                        "source": "skipped",
                        "command": "",
                        "resolved_command": "",
                        "version": "",
                    },
                }
            ],
            "tools": {
                "runtime": {
                    "status": "skipped",
                    "command": "",
                    "resolved_command": "",
                    "version": "",
                    "message": "scanner tooling preflight skipped due to mock or skip flags",
                    "version_provenance": {
                        "source": "skipped",
                        "command": "",
                        "resolved_command": "",
                        "version": "",
                    },
                }
            },
        }

    axe_data = None
    axe_error = None
    scanner_retry_runs: list[dict[str, Any]] = []
    if args.mock_axe_json:
        axe_data = json.loads(Path(args.mock_axe_json).read_text(encoding='utf-8'))
    elif not args.skip_axe:
        axe_data, axe_error, axe_retry = _run_scanner_with_retry(
            'axe',
            lambda: _try_run_axe(scanner_target, output_dir, args.timeout),
            args.scanner_retry_attempts,
            args.scanner_retry_backoff_seconds,
        )
        scanner_retry_runs.append(axe_retry)

    lighthouse_data = None
    lighthouse_error = None
    if args.mock_lighthouse_json:
        lighthouse_data = json.loads(Path(args.mock_lighthouse_json).read_text(encoding='utf-8'))
    elif not args.skip_lighthouse:
        lighthouse_data, lighthouse_error, lighthouse_retry = _run_scanner_with_retry(
            'lighthouse',
            lambda: _try_run_lighthouse(
                scanner_target,
                output_dir,
                args.timeout,
            ),
            args.scanner_retry_attempts,
            args.scanner_retry_backoff_seconds,
        )
        scanner_retry_runs.append(lighthouse_retry)

    report = normalize_report(
        contract=contract,
        axe_data=axe_data,
        lighthouse_data=lighthouse_data,
        axe_error=axe_error,
        lighthouse_error=lighthouse_error,
        axe_skipped=args.skip_axe,
        lighthouse_skipped=args.skip_lighthouse,
    )
    report['run_meta']['preflight'] = preflight
    report['report_schema'] = schema_metadata
    report['run_meta']['report_schema_version'] = REPORT_SCHEMA_VERSION
    report['run_meta']['report_schema_artifact'] = str(staged_schema_path)
    report['run_meta']['retry_policy'] = {
        'attempts': args.scanner_retry_attempts,
        'initial_backoff_seconds': args.scanner_retry_backoff_seconds,
        'max_backoff_seconds': MAX_SCANNER_RETRY_BACKOFF_SECONDS,
    }
    if policy_preset:
        report['run_meta']['policy_preset'] = policy_preset
    if policy_bundle:
        report['run_meta']['policy_bundle'] = policy_bundle
    if args.explain_policy:
        report['run_meta']['policy_effective'] = effective_policy
        report.setdefault('summary', {})['policy_effective'] = {
            'report_format': effective_policy['report_format'],
            'fail_on': effective_policy['fail_on'],
            'bundle': effective_policy['bundle'],
            'preset': effective_policy['preset'],
            'include_rule_count': len(effective_policy['include_rules']),
            'ignore_rule_count': len(effective_policy['ignore_rules']),
            'overlapping_rule_count': len(effective_policy.get('overlapping_rules', [])),
        }
    if effective_policy_output is not None:
        effective_policy_output.parent.mkdir(parents=True, exist_ok=True)
        effective_policy_output.write_text(json.dumps(effective_policy, ensure_ascii=False, indent=2), encoding='utf-8')
        report['run_meta']['effective_policy_artifact'] = str(effective_policy_output)
        report['run_meta']['notes'].append(
            f'Saved effective policy artifact: {effective_policy_output}'
        )
    if scanner_retry_runs:
        report['run_meta']['scanner_retries'] = scanner_retry_runs
        retried_tools = [item['tool'] for item in scanner_retry_runs if item.get('retry_count', 0) > 0]
        if retried_tools:
            report['run_meta']['notes'].append(
                f"Retried scanner execution for transient errors: {', '.join(sorted(set(retried_tools)))}."
            )
    if not preflight['ok']:
        report['run_meta']['notes'].append(
            'Preflight checks detected tooling issues; scanner results may be incomplete.'
        )

    before_policy_count, after_policy_count = _apply_rule_policy(report, include_rules, ignore_rules)
    if include_rules or ignore_rules:
        report['run_meta']['policy'] = {
            'bundle': policy_bundle.get('name'),
            'preset': policy_preset.get('name'),
            'include_rules': include_rules,
            'ignore_rules': ignore_rules,
            'overlapping_rules': overlapping_rules,
            'rule_overlap_resolution': 'ignore-rules-win',
            'before_filter_count': before_policy_count,
            'after_filter_count': after_policy_count,
        }
        report['run_meta']['notes'].append(
            f'Rule policy filter applied: {before_policy_count} -> {after_policy_count} findings.'
        )
    if overlapping_rules:
        report['run_meta']['policy_rule_overlap'] = {
            'overlapping_rules': overlapping_rules,
            'resolution': 'ignore-rules-win',
        }
        report['run_meta']['notes'].append(
            'Rule policy overlap detected (ignore-rules-win): ' + ", ".join(overlapping_rules)
        )

    if contract.execution_mode == 'apply-fixes':
        if args.dry_run:
            diff_path = output_dir / 'wcag-fixes.dry-run.diff'
            snapshot_path = output_dir / 'wcag-fixed-report.dry-run.snapshot.json'
        else:
            diff_path = output_dir / 'wcag-fixes.diff'
            snapshot_path = output_dir / 'wcag-fixed-report.snapshot.json'

        if local_target is None:
            report['run_meta']['notes'].append('apply-fixes skipped: target is not a local file path.')
            _remove_if_exists(diff_path)
            _remove_if_exists(snapshot_path)
        elif not supports_apply_fixes_target(local_target):
            report['run_meta']['notes'].append(
                f'apply-fixes skipped: unsupported local target extension "{local_target.suffix or "<none>"}".'
            )
            _remove_if_exists(diff_path)
            _remove_if_exists(snapshot_path)
        else:
            report, diff_text = apply_report_fixes(local_target, report, dry_run=args.dry_run)
            if diff_text:
                write_diff(diff_text, diff_path)
                diff_type = 'projected-unified-diff' if args.dry_run else 'unified-diff'
                report['run_meta'].setdefault('diff_artifacts', []).append(
                    {'path': str(diff_path), 'type': diff_type}
                )
                if args.dry_run:
                    report['run_meta']['notes'].append(
                        f'Saved projected auto-fix diff (--dry-run): {diff_path}'
                    )
                else:
                    report['run_meta']['notes'].append(f'Saved auto-fix diff: {diff_path}')
                write_snapshot(report, snapshot_path)
            else:
                _remove_if_exists(diff_path)
                _remove_if_exists(snapshot_path)

    baseline_diff: dict[str, Any] | None = None
    if baseline_report:
        baseline_diff = _build_baseline_diff(report, baseline_report, baseline_signature_config)
        debt_transitions = _build_debt_transition_summary(baseline_diff)
        _tag_findings_with_debt_state(report, baseline_diff, baseline_signature_config)
        report['run_meta']['baseline_diff'] = {
            **baseline_diff,
            'baseline_report_path': args.baseline_report,
            'debt_transitions': debt_transitions,
        }
        report.setdefault('summary', {})['debt_transitions'] = debt_transitions
        report['run_meta']['notes'].append(
            (
                'Baseline diff: introduced='
                f"{baseline_diff['introduced_count']}, "
                f"resolved={baseline_diff['resolved_count']}, "
                f"persistent={baseline_diff['persistent_count']}."
            )
        )

    _sort_report_findings(report, args.sort_findings)
    report['run_meta']['sorting'] = {
        'mode': args.sort_findings,
        'deterministic': True,
        'finding_count': len(report.get('findings', [])),
    }

    gate_findings = list(report.get('findings', []))
    if args.max_findings is not None:
        findings_cap = _cap_report_findings(report, args.max_findings)
        report['run_meta']['findings_cap'] = {
            'max_findings': args.max_findings,
            **findings_cap,
        }
        if findings_cap['truncated'] > 0:
            report['run_meta']['notes'].append(
                f"Applied --max-findings={args.max_findings}: truncated {findings_cap['truncated']} findings."
            )
    scanner_capabilities = _build_scanner_capabilities(preflight, report, args, axe_data, lighthouse_data)
    report['run_meta']['scanner_capabilities'] = scanner_capabilities
    report.setdefault('summary', {})['scanner_capabilities'] = {
        'available_scanners': sorted(
            [name for name, details in scanner_capabilities['scanners'].items() if details.get('available')]
        ),
        'unavailable_scanners': sorted(
            [name for name, details in scanner_capabilities['scanners'].items() if not details.get('available')]
        ),
        'available_rule_count': scanner_capabilities['available_rule_count'],
    }
    output_json = output_dir / 'wcag-report.json'
    output_md = output_dir / 'wcag-report.md'
    if report_format == 'json':
        write_report_files(report, str(output_json), str(output_md))
        machine_output = output_json
    else:
        output_sarif = output_dir / 'wcag-report.sarif'
        output_sarif.write_text(
            json.dumps(_report_to_sarif(report, contract.target, local_target), ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(to_markdown_table(report), encoding='utf-8')
        machine_output = output_sarif

    if fail_on:
        gate_report = {'findings': gate_findings}
        gate_scope = 'all-unresolved'
        if args.fail_on_new_only:
            introduced_signatures = set((baseline_diff or {}).get('introduced_signatures', []))
            report_target = str(report.get('target', {}).get('value', '')).strip()
            gate_report = {
                'findings': [
                    item
                    for item in gate_findings
                    if _finding_signature_with_config(item, baseline_signature_config, report_target)
                    in introduced_signatures
                ],
            }
            gate_scope = 'introduced-only'
        should_fail, exit_code = _resolve_fail_threshold(gate_report, fail_on)
        report['run_meta']['policy_gate'] = {
            'fail_on': fail_on,
            'failed': should_fail,
            'exit_code': exit_code if should_fail else 0,
            'scope': gate_scope,
            'evaluated_findings': len(gate_report.get('findings', [])),
        }
        if report_format == 'json':
            write_report_files(report, str(output_json), str(output_md))
        elif machine_output.suffix == '.sarif':
            output_sarif = machine_output
            output_sarif.write_text(
                json.dumps(_report_to_sarif(report, contract.target, local_target), ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            output_md.write_text(to_markdown_table(report), encoding='utf-8')
    else:
        should_fail, exit_code = False, 0

    if args.summary_only:
        compact_summary = _build_compact_summary(
            report=report,
            report_format=report_format,
            machine_output=machine_output,
            output_md=output_md,
            should_fail=should_fail,
            fail_on=fail_on,
            exit_code=exit_code,
        )
        print(json.dumps(compact_summary, ensure_ascii=False))
    else:
        print(f'Saved machine-readable report ({report_format}): {machine_output}')
        print(f'Saved Markdown table: {output_md}')
        if report['run_meta']['notes']:
            print('Notes:')
            for note in report['run_meta']['notes']:
                print(f'- {note}')
        if should_fail:
            print(f'Policy gate failed: unresolved finding severity >= {fail_on}')
    if should_fail:
        return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

