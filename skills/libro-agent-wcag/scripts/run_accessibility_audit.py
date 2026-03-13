#!/usr/bin/env python3
"""Run axe and Lighthouse scans, then emit normalized WCAG outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
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
BASELINE_EVIDENCE_MODES = {"none", "hash", "hash-chain"}
WAIVER_EXPIRY_MODES = {"ignore", "warn", "fail"}
WAIVER_EXPIRY_EXIT_CODE = 45
RISK_CALIBRATION_MODES = {"off", "warn", "strict"}
RISK_CALIBRATION_SCHEMA_VERSION = "1.0.0"
RISK_CALIBRATION_EXIT_CODE = 46
RISK_CALIBRATION_MIN_SAMPLES = 3
RISK_CALIBRATION_PRECISION_THRESHOLD = 0.6
HIGH_SEVERITY_LEVELS = {"critical", "serious"}
REPLAY_VERIFICATION_SCHEMA_VERSION = "1.0.0"
REPLAY_VERIFICATION_EXIT_CODE = 47
DEBT_STATE_NEW = "new"
DEBT_STATE_ACCEPTED = "accepted"
DEBT_STATE_RETIRED = "retired"
DEBT_STATE_REGRESSED = "regressed"
DEBT_WAIVER_REQUIRED_FIELDS = {"signature", "owner", "approved_at", "expires_at", "reason"}
DEBT_TREND_SCHEMA_VERSION = "1.0.0"
DEFAULT_DEBT_TREND_WINDOW = 5
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


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(8192), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _build_baseline_evidence_material(
    report: dict[str, Any],
    signature_config: dict[str, Any],
) -> dict[str, Any]:
    signatures = sorted(_unresolved_finding_signatures(report, signature_config))
    target = str(report.get('target', {}).get('value', '')).strip()
    return {
        'target': target,
        'signature_config': signature_config,
        'unresolved_signatures': signatures,
    }


def _compute_report_evidence_hash(
    report: dict[str, Any],
    signature_config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    material = _build_baseline_evidence_material(report, signature_config)
    canonical = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return _sha256_text(canonical), material


def _verify_baseline_report_evidence(
    baseline_report: dict[str, Any],
    signature_config: dict[str, Any],
) -> dict[str, Any]:
    baseline_hash, _ = _compute_report_evidence_hash(baseline_report, signature_config)
    evidence = baseline_report.get('run_meta', {}).get('baseline_evidence', {})
    declared_hash = str(evidence.get('report_hash', '')).strip() if isinstance(evidence, dict) else ''
    declared_chain = str(evidence.get('chain_hash', '')).strip() if isinstance(evidence, dict) else ''
    declared_parent_hash = str(evidence.get('baseline_report_hash', '')).strip() if isinstance(evidence, dict) else ''

    if declared_hash and declared_hash != baseline_hash:
        raise ValueError('baseline evidence verification failed: declared report_hash does not match baseline report content')

    if declared_chain:
        expected_chain = _sha256_text(f'{declared_parent_hash}:{baseline_hash}') if declared_parent_hash else baseline_hash
        if declared_chain != expected_chain:
            raise ValueError('baseline evidence verification failed: declared chain_hash does not match baseline report lineage')

    return {
        'declared': bool(declared_hash),
        'verified': not declared_hash or declared_hash == baseline_hash,
        'baseline_report_hash': baseline_hash,
        'baseline_chain_hash': declared_chain,
    }


def _build_run_baseline_evidence(
    *,
    report: dict[str, Any],
    baseline_report: dict[str, Any],
    signature_config: dict[str, Any],
    evidence_mode: str,
) -> dict[str, Any]:
    current_hash, material = _compute_report_evidence_hash(report, signature_config)
    baseline_verification = {
        'declared': False,
        'verified': False,
        'baseline_report_hash': '',
        'baseline_chain_hash': '',
    }
    if baseline_report:
        baseline_verification = _verify_baseline_report_evidence(baseline_report, signature_config)

    evidence: dict[str, Any] = {
        'mode': evidence_mode,
        'generated_at': _utc_timestamp(),
        'report_hash': current_hash,
        'signature_count': len(material.get('unresolved_signatures', [])),
        'signature_config': signature_config,
    }
    if evidence_mode == 'hash-chain':
        parent_hash = (
            baseline_verification.get('baseline_chain_hash')
            or baseline_verification.get('baseline_report_hash')
            or ''
        )
        evidence['baseline_report_hash'] = baseline_verification.get('baseline_report_hash', '')
        evidence['baseline_chain_parent'] = parent_hash
        evidence['chain_hash'] = _sha256_text(f'{parent_hash}:{current_hash}') if parent_hash else current_hash
    elif baseline_verification.get('baseline_report_hash'):
        evidence['baseline_report_hash'] = baseline_verification.get('baseline_report_hash', '')

    evidence['baseline_verification'] = {
        'declared': baseline_verification.get('declared', False),
        'verified': baseline_verification.get('verified', False),
    }
    return evidence


def _build_artifact_manifest(
    *,
    output_dir: Path,
    report_format: str,
    target: str,
    artifact_paths: dict[str, Path],
    baseline_evidence: dict[str, Any] | None,
) -> tuple[dict[str, Any], Path]:
    artifacts: list[dict[str, Any]] = []
    for kind in sorted(artifact_paths):
        path = artifact_paths[kind]
        if not path.exists() or not path.is_file():
            continue
        artifacts.append(
            {
                'kind': kind,
                'path': str(path),
                'size_bytes': path.stat().st_size,
                'sha256': _sha256_file(path),
            }
        )

    manifest: dict[str, Any] = {
        'generated_at': _utc_timestamp(),
        'generator': {
            'name': 'run_accessibility_audit.py',
            'version': REPORT_SCHEMA_VERSION,
        },
        'target': target,
        'report_format': report_format,
        'artifact_count': len(artifacts),
        'artifacts': artifacts,
    }
    if baseline_evidence:
        manifest['baseline_evidence'] = {
            'mode': baseline_evidence.get('mode'),
            'report_hash': baseline_evidence.get('report_hash'),
            'chain_hash': baseline_evidence.get('chain_hash'),
            'baseline_report_hash': baseline_evidence.get('baseline_report_hash'),
            'baseline_verification': baseline_evidence.get('baseline_verification', {}),
        }

    manifest_path = output_dir / 'artifact-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest, manifest_path


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


def _parse_waiver_timestamp(value: str, field: str, index: int) -> datetime:
    normalized = value.strip()
    if normalized.endswith('Z'):
        normalized = normalized[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as err:
        raise ValueError(
            f'--baseline-report debt_waivers[{index}].{field} must be ISO8601 with timezone'
        ) from err
    if parsed.tzinfo is None:
        raise ValueError(f'--baseline-report debt_waivers[{index}].{field} must include timezone offset')
    return parsed.astimezone(timezone.utc)


def _validate_debt_waivers(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError('--baseline-report debt_waivers must be a list')
    validated: list[dict[str, str]] = []
    seen_signatures: set[str] = set()
    for index, raw_waiver in enumerate(value):
        if not isinstance(raw_waiver, dict):
            raise ValueError(f'--baseline-report debt_waivers[{index}] must be a JSON object')
        missing_keys = sorted(DEBT_WAIVER_REQUIRED_FIELDS - set(raw_waiver))
        unknown_keys = sorted(set(raw_waiver) - DEBT_WAIVER_REQUIRED_FIELDS)
        if missing_keys or unknown_keys:
            raise ValueError(
                f'--baseline-report debt_waivers[{index}] must contain exactly keys: '
                'signature, owner, approved_at, expires_at, reason '
                f'(missing: {missing_keys or "none"}, unknown: {unknown_keys or "none"})'
            )
        waiver: dict[str, str] = {}
        for field in sorted(DEBT_WAIVER_REQUIRED_FIELDS):
            raw_value = raw_waiver.get(field)
            if not isinstance(raw_value, str) or not raw_value.strip():
                raise ValueError(f'--baseline-report debt_waivers[{index}].{field} must be a non-empty string')
            waiver[field] = raw_value.strip()
        if waiver['signature'] in seen_signatures:
            raise ValueError(f'--baseline-report debt_waivers[{index}].signature is duplicated: {waiver["signature"]}')
        approved_at = _parse_waiver_timestamp(waiver['approved_at'], 'approved_at', index)
        expires_at = _parse_waiver_timestamp(waiver['expires_at'], 'expires_at', index)
        if expires_at <= approved_at:
            raise ValueError(
                f'--baseline-report debt_waivers[{index}] expires_at must be later than approved_at'
            )
        waiver['approved_at'] = approved_at.isoformat().replace('+00:00', 'Z')
        waiver['expires_at'] = expires_at.isoformat().replace('+00:00', 'Z')
        seen_signatures.add(waiver['signature'])
        validated.append(waiver)
    return validated


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
    payload['debt_waivers'] = _validate_debt_waivers(payload.get('debt_waivers'))
    return payload


def _coerce_non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        converted = int(value)
    except (TypeError, ValueError):
        return 0
    return converted if converted >= 0 else 0


def _build_debt_trend_counts(
    debt_transitions: dict[str, Any] | None,
    waiver_review: dict[str, Any] | None,
) -> dict[str, int]:
    transitions = debt_transitions or {}
    return {
        DEBT_STATE_NEW: _coerce_non_negative_int(((transitions.get(DEBT_STATE_NEW) or {}).get('count'))),
        DEBT_STATE_ACCEPTED: _coerce_non_negative_int(((transitions.get(DEBT_STATE_ACCEPTED) or {}).get('count'))),
        DEBT_STATE_RETIRED: _coerce_non_negative_int(((transitions.get(DEBT_STATE_RETIRED) or {}).get('count'))),
        DEBT_STATE_REGRESSED: _coerce_non_negative_int((waiver_review or {}).get('expired_count')),
    }


def _empty_debt_trend_counts() -> dict[str, int]:
    return {
        DEBT_STATE_NEW: 0,
        DEBT_STATE_ACCEPTED: 0,
        DEBT_STATE_RETIRED: 0,
        DEBT_STATE_REGRESSED: 0,
    }


def _sanitize_debt_trend_point(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    counts = raw.get('counts')
    if not isinstance(counts, dict):
        return None
    return {
        'recorded_at': str(raw.get('recorded_at', '')).strip() or '',
        'source_report': str(raw.get('source_report', '')).strip() or '',
        'counts': {
            DEBT_STATE_NEW: _coerce_non_negative_int(counts.get(DEBT_STATE_NEW)),
            DEBT_STATE_ACCEPTED: _coerce_non_negative_int(counts.get(DEBT_STATE_ACCEPTED)),
            DEBT_STATE_RETIRED: _coerce_non_negative_int(counts.get(DEBT_STATE_RETIRED)),
            DEBT_STATE_REGRESSED: _coerce_non_negative_int(counts.get(DEBT_STATE_REGRESSED)),
        },
    }


def _derive_baseline_point_from_legacy_report(
    baseline_report: dict[str, Any],
    baseline_report_path: str | None,
) -> dict[str, Any] | None:
    run_meta = baseline_report.get('run_meta')
    if not isinstance(run_meta, dict):
        return None
    baseline_diff = run_meta.get('baseline_diff')
    if not isinstance(baseline_diff, dict):
        return None
    transitions = baseline_diff.get('debt_transitions')
    if not isinstance(transitions, dict):
        return None
    waiver_review = baseline_diff.get('waiver_review')
    if not isinstance(waiver_review, dict):
        waiver_review = None
    counts = _build_debt_trend_counts(transitions, waiver_review)
    recorded_at = str(run_meta.get('generated_at') or run_meta.get('completed_at') or '').strip()
    source_report = baseline_report_path or str(baseline_diff.get('baseline_report_path', '')).strip()
    return {
        'recorded_at': recorded_at,
        'source_report': source_report,
        'counts': counts,
    }


def _extract_historical_debt_trend_points(
    baseline_report: dict[str, Any],
    baseline_report_path: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    report_schema_version = str(
        ((baseline_report.get('report_schema') or {}).get('version')) if isinstance(baseline_report, dict) else ''
    ).strip()
    if report_schema_version and report_schema_version != REPORT_SCHEMA_VERSION:
        return [], {
            'history_reset_reason': 'schema-version-mismatch',
            'baseline_report_schema_version': report_schema_version,
            'expected_report_schema_version': REPORT_SCHEMA_VERSION,
            'loaded_point_count': 0,
        }

    run_meta = baseline_report.get('run_meta')
    if not isinstance(run_meta, dict):
        return [], {'history_reset_reason': 'missing-history', 'loaded_point_count': 0}
    trend = run_meta.get('debt_trend')
    if not isinstance(trend, dict):
        fallback = _derive_baseline_point_from_legacy_report(baseline_report, baseline_report_path)
        if fallback:
            return [fallback], {'history_reset_reason': 'legacy-fallback', 'loaded_point_count': 1}
        return [], {'history_reset_reason': 'missing-history', 'loaded_point_count': 0}

    schema_version = str(trend.get('schema_version', '')).strip()
    if schema_version and schema_version != DEBT_TREND_SCHEMA_VERSION:
        return [], {
            'history_reset_reason': 'trend-schema-version-mismatch',
            'baseline_trend_schema_version': schema_version,
            'expected_trend_schema_version': DEBT_TREND_SCHEMA_VERSION,
            'loaded_point_count': 0,
        }
    raw_points = trend.get('points')
    if not isinstance(raw_points, list):
        return [], {'history_reset_reason': 'missing-history', 'loaded_point_count': 0}
    points = [point for point in (_sanitize_debt_trend_point(item) for item in raw_points) if point is not None]
    return points, {'history_reset_reason': None, 'loaded_point_count': len(points)}


def _build_debt_trend_payload(
    *,
    now_utc: datetime,
    window: int,
    baseline_report: dict[str, Any],
    baseline_report_path: str | None,
    debt_transitions: dict[str, Any] | None,
    waiver_review: dict[str, Any] | None,
) -> dict[str, Any]:
    history_points, history_meta = _extract_historical_debt_trend_points(baseline_report, baseline_report_path)
    current_point = {
        'recorded_at': now_utc.isoformat().replace('+00:00', 'Z'),
        'source_report': baseline_report_path or '',
        'counts': _build_debt_trend_counts(debt_transitions, waiver_review),
    }
    merged_points = history_points + [current_point]
    points = merged_points[-window:]
    previous = points[-2]['counts'] if len(points) > 1 else _empty_debt_trend_counts()
    latest = points[-1]['counts']
    delta = {
        DEBT_STATE_NEW: latest[DEBT_STATE_NEW] - previous[DEBT_STATE_NEW],
        DEBT_STATE_ACCEPTED: latest[DEBT_STATE_ACCEPTED] - previous[DEBT_STATE_ACCEPTED],
        DEBT_STATE_RETIRED: latest[DEBT_STATE_RETIRED] - previous[DEBT_STATE_RETIRED],
        DEBT_STATE_REGRESSED: latest[DEBT_STATE_REGRESSED] - previous[DEBT_STATE_REGRESSED],
    }
    return {
        'schema_version': DEBT_TREND_SCHEMA_VERSION,
        'generated_at': now_utc.isoformat().replace('+00:00', 'Z'),
        'window': window,
        'points': points,
        'summary': {
            'total_points': len(points),
            'history_points_used': max(0, len(points) - 1),
            'latest_counts': latest,
            'delta_from_previous': delta,
        },
        'history_meta': history_meta,
    }


def _is_actionable_outcome(finding: dict[str, Any]) -> bool:
    status = str(finding.get('status', '')).strip().lower()
    if status not in {'open', 'fixed'}:
        return False
    if bool(finding.get('manual_review_required')):
        return False
    return not bool(str(finding.get('downgrade_reason', '')).strip())


def _extract_rule_signals_from_report(report: dict[str, Any]) -> dict[str, dict[str, int]]:
    signals: dict[str, dict[str, int]] = {}
    findings = report.get('findings')
    if not isinstance(findings, list):
        return signals
    for item in findings:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get('rule_id', '')).strip()
        if not rule_id:
            continue
        severity = str(item.get('severity', 'info')).strip().lower()
        bucket = signals.setdefault(
            rule_id,
            {
                'observations': 0,
                'actionable_count': 0,
                'high_severity_observations': 0,
                'high_severity_actionable_count': 0,
            },
        )
        actionable = _is_actionable_outcome(item)
        bucket['observations'] += 1
        if actionable:
            bucket['actionable_count'] += 1
        if severity in HIGH_SEVERITY_LEVELS:
            bucket['high_severity_observations'] += 1
            if actionable:
                bucket['high_severity_actionable_count'] += 1
    return signals


def _merge_rule_signals(
    aggregate: dict[str, dict[str, int]],
    additional: dict[str, dict[str, int]],
) -> None:
    for rule_id, stats in additional.items():
        bucket = aggregate.setdefault(
            rule_id,
            {
                'observations': 0,
                'actionable_count': 0,
                'high_severity_observations': 0,
                'high_severity_actionable_count': 0,
            },
        )
        bucket['observations'] += int(stats.get('observations', 0))
        bucket['actionable_count'] += int(stats.get('actionable_count', 0))
        bucket['high_severity_observations'] += int(stats.get('high_severity_observations', 0))
        bucket['high_severity_actionable_count'] += int(stats.get('high_severity_actionable_count', 0))


def _load_risk_calibration_source(
    source_path: str | None,
) -> tuple[dict[str, dict[str, int]], dict[str, Any]]:
    if not source_path:
        return {}, {'downgrade_reason': 'missing-evidence', 'message': '--risk-calibration-source is required'}
    source = Path(source_path)
    if not source.exists():
        return {}, {'downgrade_reason': 'missing-evidence', 'message': f'source path does not exist: {source_path}'}

    aggregate: dict[str, dict[str, int]] = {}
    report_files = [source] if source.is_file() else sorted(source.rglob('*.json'))
    if not report_files:
        return {}, {'downgrade_reason': 'missing-evidence', 'message': 'no JSON evidence files found'}

    stale_schema_files: list[str] = []
    parsed_reports = 0
    for report_file in report_files:
        try:
            payload = json.loads(report_file.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue

        if 'rules' in payload and isinstance(payload.get('rules'), list) and 'findings' not in payload:
            schema_version = str(payload.get('schema_version', '')).strip()
            if schema_version and schema_version != RISK_CALIBRATION_SCHEMA_VERSION:
                return {}, {
                    'downgrade_reason': 'stale-schema',
                    'message': (
                        'risk calibration schema mismatch: '
                        f'{schema_version} != {RISK_CALIBRATION_SCHEMA_VERSION}'
                    ),
                }
            rule_entries = payload.get('rules', [])
            seen_rule_ids: set[str] = set()
            for entry in rule_entries:
                if not isinstance(entry, dict):
                    continue
                rule_id = str(entry.get('rule_id', '')).strip()
                if not rule_id:
                    continue
                if rule_id in seen_rule_ids:
                    return {}, {
                        'downgrade_reason': 'conflicting-rule-ids',
                        'message': f'duplicate rule_id in calibration artifact: {rule_id}',
                    }
                seen_rule_ids.add(rule_id)
                _merge_rule_signals(
                    aggregate,
                    {
                        rule_id: {
                            'observations': _coerce_non_negative_int(entry.get('observations')),
                            'actionable_count': _coerce_non_negative_int(entry.get('actionable_count')),
                            'high_severity_observations': _coerce_non_negative_int(
                                entry.get('high_severity_observations')
                            ),
                            'high_severity_actionable_count': _coerce_non_negative_int(
                                entry.get('high_severity_actionable_count')
                            ),
                        }
                    },
                )
            parsed_reports += 1
            continue

        schema_version = str(((payload.get('report_schema') or {}).get('version'))).strip()
        if schema_version and schema_version != REPORT_SCHEMA_VERSION:
            stale_schema_files.append(str(report_file))
            continue
        _merge_rule_signals(aggregate, _extract_rule_signals_from_report(payload))
        parsed_reports += 1

    if not aggregate:
        if stale_schema_files:
            return {}, {
                'downgrade_reason': 'stale-schema',
                'message': f'no usable evidence after schema filtering ({len(stale_schema_files)} stale files)',
            }
        return {}, {'downgrade_reason': 'missing-evidence', 'message': 'no usable findings in calibration source'}
    return aggregate, {
        'parsed_reports': parsed_reports,
        'scanned_files': len(report_files),
        'stale_schema_file_count': len(stale_schema_files),
    }


def _evaluate_risk_calibration(
    *,
    report: dict[str, Any],
    source_path: str | None,
    mode: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        'schema_version': RISK_CALIBRATION_SCHEMA_VERSION,
        'mode': mode,
        'source_path': source_path or '',
        'min_high_severity_samples': RISK_CALIBRATION_MIN_SAMPLES,
        'high_severity_precision_threshold': RISK_CALIBRATION_PRECISION_THRESHOLD,
        'applied': False,
        'downgrade_reason': None,
        'rules': [],
        'unstable_high_severity_rules': [],
        'source_meta': {},
    }
    if mode == 'off':
        result['applied'] = False
        result['downgrade_reason'] = 'mode-off'
        return result

    signals, source_meta = _load_risk_calibration_source(source_path)
    result['source_meta'] = source_meta
    if not signals:
        result['downgrade_reason'] = str(source_meta.get('downgrade_reason') or 'missing-evidence')
        return result

    current_high_rule_ids = sorted(
        {
            str(item.get('rule_id', '')).strip()
            for item in report.get('findings', [])
            if isinstance(item, dict)
            and str(item.get('severity', 'info')).strip().lower() in HIGH_SEVERITY_LEVELS
            and str(item.get('status', '')).strip().lower() != 'fixed'
            and str(item.get('rule_id', '')).strip()
        }
    )
    result['current_high_severity_rules'] = current_high_rule_ids

    rule_rows: list[dict[str, Any]] = []
    unstable_rules: list[str] = []
    for rule_id in sorted(signals):
        stats = signals[rule_id]
        observations = int(stats.get('observations', 0))
        actionable_count = int(stats.get('actionable_count', 0))
        high_observations = int(stats.get('high_severity_observations', 0))
        high_actionable = int(stats.get('high_severity_actionable_count', 0))
        precision = round((actionable_count / observations), 4) if observations else 0.0
        high_precision = round((high_actionable / high_observations), 4) if high_observations else None
        unstable = bool(
            rule_id in current_high_rule_ids
            and high_observations >= RISK_CALIBRATION_MIN_SAMPLES
            and high_precision is not None
            and high_precision < RISK_CALIBRATION_PRECISION_THRESHOLD
        )
        if unstable:
            unstable_rules.append(rule_id)
        rule_rows.append(
            {
                'rule_id': rule_id,
                'observations': observations,
                'actionable_count': actionable_count,
                'precision': precision,
                'high_severity_observations': high_observations,
                'high_severity_actionable_count': high_actionable,
                'high_severity_precision': high_precision,
                'unstable_high_severity': unstable,
            }
        )
    result['rules'] = rule_rows
    result['unstable_high_severity_rules'] = unstable_rules
    result['applied'] = True
    return result


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
    baseline_evidence_mode: str,
    waiver_expiry_mode: str,
    risk_calibration_mode: str,
    risk_calibration_source: str | None,
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
        policy_gate = report.get('run_meta', {}).get('policy_gate', {})
        compact['policy_gate'] = {
            'fail_on': fail_on,
            'failed': bool(policy_gate.get('failed', False)),
            'exit_code': int(policy_gate.get('exit_code', 0)),
            'scope': policy_gate.get('scope', 'all-unresolved'),
        }
    baseline_diff = report.get('run_meta', {}).get('baseline_diff')
    if baseline_diff:
        compact['baseline_diff'] = {
            'introduced_count': baseline_diff.get('introduced_count', 0),
            'resolved_count': baseline_diff.get('resolved_count', 0),
            'persistent_count': baseline_diff.get('persistent_count', 0),
        }
        waiver_review = baseline_diff.get('waiver_review')
        if waiver_review:
            compact['waiver_review'] = {
                'accepted_count': waiver_review.get('accepted_count', 0),
                'expired_count': waiver_review.get('expired_count', 0),
                'missing_count': waiver_review.get('missing_count', 0),
                'valid_count': waiver_review.get('valid_count', 0),
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
    baseline_evidence = report.get('run_meta', {}).get('baseline_evidence')
    if baseline_evidence:
        compact['baseline_evidence'] = {
            'mode': baseline_evidence.get('mode'),
            'baseline_verification': baseline_evidence.get('baseline_verification', {}),
        }
    artifact_manifest = report.get('run_meta', {}).get('artifact_manifest')
    if artifact_manifest:
        compact['artifact_manifest'] = artifact_manifest
    waiver_gate = report.get('run_meta', {}).get('waiver_gate')
    if waiver_gate:
        compact['waiver_gate'] = waiver_gate
    debt_trend = summary.get('debt_trend')
    if debt_trend:
        compact['debt_trend'] = debt_trend
    risk_calibration = report.get('run_meta', {}).get('risk_calibration')
    if risk_calibration:
        compact['risk_calibration'] = {
            'mode': risk_calibration.get('mode'),
            'applied': bool(risk_calibration.get('applied')),
            'downgrade_reason': risk_calibration.get('downgrade_reason'),
            'unstable_high_severity_rules': risk_calibration.get('unstable_high_severity_rules', []),
        }
    replay_verification = report.get('run_meta', {}).get('replay_verification')
    if replay_verification:
        compact['replay_verification'] = replay_verification
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



def _build_debt_waiver_index(baseline_report: dict[str, Any]) -> dict[str, dict[str, str]]:
    waivers = baseline_report.get('debt_waivers')
    if not isinstance(waivers, list):
        return {}
    return {
        str(item.get('signature', '')).strip(): item
        for item in waivers
        if isinstance(item, dict) and str(item.get('signature', '')).strip()
    }


def _evaluate_debt_waiver_review(
    baseline_diff: dict[str, Any],
    baseline_report: dict[str, Any],
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    accepted_signatures = sorted(set(baseline_diff.get('persistent_signatures', [])))
    waiver_index = _build_debt_waiver_index(baseline_report)
    expired: list[dict[str, str]] = []
    valid: list[dict[str, str]] = []
    missing: list[str] = []
    for signature in accepted_signatures:
        waiver = waiver_index.get(signature)
        if not waiver:
            missing.append(signature)
            continue
        expires_at = datetime.fromisoformat(str(waiver['expires_at']).replace('Z', '+00:00'))
        waiver_entry = {
            'signature': signature,
            'owner': str(waiver['owner']),
            'approved_at': str(waiver['approved_at']),
            'expires_at': str(waiver['expires_at']),
            'reason': str(waiver['reason']),
        }
        if expires_at <= now:
            expired.append(waiver_entry)
        else:
            valid.append(waiver_entry)
    return {
        'accepted_count': len(accepted_signatures),
        'valid_count': len(valid),
        'expired_count': len(expired),
        'missing_count': len(missing),
        'valid_waivers': valid,
        'expired_waivers': expired,
        'missing_signatures': missing,
        'evaluated_at': now.isoformat().replace('+00:00', 'Z'),
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


def _extract_available_scanners(report: dict[str, Any]) -> set[str]:
    scanner_capabilities = report.get('run_meta', {}).get('scanner_capabilities', {})
    scanners = scanner_capabilities.get('scanners')
    if not isinstance(scanners, dict):
        return set()
    available: set[str] = set()
    for scanner_name, details in scanners.items():
        if not isinstance(details, dict):
            continue
        if details.get('available'):
            available.add(str(scanner_name))
    return available


def _collect_replay_signature_rows(
    report: dict[str, Any],
    signature_config: dict[str, Any] | None = None,
) -> dict[str, dict[str, str]]:
    effective_signature_config = signature_config or {
        'include_target_in_signature': False,
        'target_normalization': 'none',
        'selector_canonicalization': 'none',
    }
    report_target = str(report.get('target', {}).get('value', '')).strip()
    rows: dict[str, dict[str, str]] = {}
    for finding in report.get('findings', []):
        if not isinstance(finding, dict):
            continue
        if finding.get('status') == 'fixed':
            continue
        signature = _finding_signature_with_config(finding, effective_signature_config, report_target)
        rows[signature] = {
            'signature': signature,
            'rule_id': str(finding.get('rule_id', '')).strip(),
            'severity': str(finding.get('severity', 'info')).strip() or 'info',
        }
    return rows


def _load_replay_source_report(replay_dir: Path) -> tuple[dict[str, Any], Path]:
    source_report_path = replay_dir / 'wcag-report.json'
    if not source_report_path.exists():
        raise ValueError(
            '--replay-verify-from must point to a directory containing wcag-report.json: '
            + str(source_report_path)
        )
    payload = json.loads(source_report_path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('replay source report must be a JSON object')
    return payload, source_report_path


def _build_replay_diff_markdown(
    replay_summary: dict[str, Any],
    output_path: Path,
) -> None:
    lines = [
        '# Replay Verification Diff',
        '',
        f"- Source report: `{replay_summary.get('source_report_path', '')}`",
        f"- Generated at: `{replay_summary.get('generated_at', '')}`",
        f"- Gate failed: `{replay_summary.get('gate', {}).get('failed', False)}`",
        '',
        '| Signature | Rule | Severity | Replay Status |',
        '|---|---|---|---|',
    ]
    for item in replay_summary.get('findings', []):
        signature = str(item.get('signature', '')).replace('|', '\\|')
        lines.append(
            f"| `{signature}` | `{item.get('rule_id', '')}` | `{item.get('severity', 'info')}` | `{item.get('status', '')}` |"
        )
    output_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _build_replay_verification_summary(
    current_report: dict[str, Any],
    replay_source_report: dict[str, Any],
    replay_source_path: Path,
    replay_source_dir: Path,
    *,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    generated_at = (now_utc or datetime.now(timezone.utc)).isoformat().replace('+00:00', 'Z')
    signature_config = {
        'include_target_in_signature': False,
        'target_normalization': 'none',
        'selector_canonicalization': 'none',
    }
    source_rows = _collect_replay_signature_rows(replay_source_report, signature_config)
    current_rows = _collect_replay_signature_rows(current_report, signature_config)
    source_signatures = set(source_rows)
    current_signatures = set(current_rows)

    source_target = _normalize_signature_target(
        str(replay_source_report.get('target', {}).get('value', '')).strip(),
        'path-only',
    )
    current_target = _normalize_signature_target(
        str(current_report.get('target', {}).get('value', '')).strip(),
        'path-only',
    )
    source_scanners = sorted(_extract_available_scanners(replay_source_report))
    current_scanners = sorted(_extract_available_scanners(current_report))

    nondeterministic_reasons: list[str] = []
    target_drift = bool(source_target and current_target and source_target != current_target)
    scanner_drift = source_scanners != current_scanners
    if target_drift:
        nondeterministic_reasons.append(
            f'target-drift: source={source_target} current={current_target}'
        )
    if scanner_drift:
        nondeterministic_reasons.append(
            'scanner-capability-drift: source=' + ','.join(source_scanners) + ' current=' + ','.join(current_scanners)
        )

    findings_rows: list[dict[str, str]] = []
    for signature in sorted(source_signatures - current_signatures):
        source = source_rows[signature]
        findings_rows.append(
            {
                'signature': signature,
                'rule_id': source.get('rule_id', ''),
                'severity': source.get('severity', 'info'),
                'status': 'resolved',
            }
        )
    for signature in sorted(source_signatures & current_signatures):
        current = current_rows[signature]
        findings_rows.append(
            {
                'signature': signature,
                'rule_id': current.get('rule_id', ''),
                'severity': current.get('severity', 'info'),
                'status': 'unchanged',
            }
        )
    for signature in sorted(current_signatures - source_signatures):
        current = current_rows[signature]
        findings_rows.append(
            {
                'signature': signature,
                'rule_id': current.get('rule_id', ''),
                'severity': current.get('severity', 'info'),
                'status': 'non-deterministic' if nondeterministic_reasons else 'regressed',
            }
        )

    status_counts = {
        'resolved': sum(1 for item in findings_rows if item.get('status') == 'resolved'),
        'unchanged': sum(1 for item in findings_rows if item.get('status') == 'unchanged'),
        'regressed': sum(1 for item in findings_rows if item.get('status') == 'regressed'),
        'non-deterministic': sum(1 for item in findings_rows if item.get('status') == 'non-deterministic'),
    }
    high_severity_regressed = [
        item for item in findings_rows
        if item.get('status') == 'regressed' and str(item.get('severity', 'info')) in HIGH_SEVERITY_LEVELS
    ]
    gate_failed = len(high_severity_regressed) > 0
    gate = {
        'failed': gate_failed,
        'exit_code': REPLAY_VERIFICATION_EXIT_CODE if gate_failed else 0,
        'high_severity_regressed_count': len(high_severity_regressed),
        'high_severity_regressed_signatures': [item.get('signature', '') for item in high_severity_regressed],
    }
    return {
        'schema_version': REPLAY_VERIFICATION_SCHEMA_VERSION,
        'source_report_dir': str(replay_source_dir),
        'source_report_path': str(replay_source_path),
        'generated_at': generated_at,
        'source_scanners': source_scanners,
        'current_scanners': current_scanners,
        'non_deterministic_reasons': nondeterministic_reasons,
        'status_counts': status_counts,
        'gate': gate,
        'findings': findings_rows,
    }


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
        "--baseline-evidence-mode",
        choices=sorted(BASELINE_EVIDENCE_MODES),
        default="none",
        help="Baseline evidence integrity mode (none|hash|hash-chain) for tamper/staleness checks.",
    )
    parser.add_argument(
        "--waiver-expiry-mode",
        choices=sorted(WAIVER_EXPIRY_MODES),
        default="warn",
        help="Expired baseline debt waiver handling: ignore, warn, or fail.",
    )
    parser.add_argument(
        "--fail-on-new-only",
        action="store_true",
        help="When used with --fail-on and --baseline-report, fail only on newly introduced debt.",
    )
    parser.add_argument(
        "--debt-trend-window",
        type=int,
        default=DEFAULT_DEBT_TREND_WINDOW,
        help="Number of historical baseline trend points to keep in debt-trend artifact output.",
    )
    parser.add_argument(
        "--risk-calibration-source",
        default=None,
        help="JSON report/artifact file or directory used to compute per-rule risk calibration precision.",
    )
    parser.add_argument(
        "--risk-calibration-mode",
        choices=sorted(RISK_CALIBRATION_MODES),
        default="off",
        help="Risk calibration gate mode: off, warn, or strict.",
    )
    parser.add_argument(
        "--replay-verify-from",
        default=None,
        help="Directory containing prior run artifacts (wcag-report.json) for replay verification.",
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
    if args.debt_trend_window < 1:
        raise ValueError('--debt-trend-window must be >= 1')
    if args.fail_on_new_only and not args.fail_on:
        raise ValueError('--fail-on-new-only requires --fail-on')
    if args.fail_on_new_only and not args.baseline_report:
        raise ValueError('--fail-on-new-only requires --baseline-report')
    if args.replay_verify_from and not Path(args.replay_verify_from).exists():
        raise ValueError('--replay-verify-from directory does not exist: ' + str(args.replay_verify_from))

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
        baseline_evidence_mode=args.baseline_evidence_mode,
        waiver_expiry_mode=args.waiver_expiry_mode,
        risk_calibration_mode=args.risk_calibration_mode,
        risk_calibration_source=args.risk_calibration_source,
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

    diff_path: Path | None = None
    snapshot_path: Path | None = None
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
    waiver_review: dict[str, Any] | None = None
    debt_transitions: dict[str, Any] | None = None
    if baseline_report:
        baseline_diff = _build_baseline_diff(report, baseline_report, baseline_signature_config)
        debt_transitions = _build_debt_transition_summary(baseline_diff)
        waiver_review = _evaluate_debt_waiver_review(baseline_diff, baseline_report)
        _tag_findings_with_debt_state(report, baseline_diff, baseline_signature_config)
        report['run_meta']['baseline_diff'] = {
            **baseline_diff,
            'baseline_report_path': args.baseline_report,
            'debt_transitions': debt_transitions,
            'waiver_review': waiver_review,
        }
        report.setdefault('summary', {})['debt_transitions'] = debt_transitions
        report['summary']['waiver_review'] = {
            'accepted_count': waiver_review.get('accepted_count', 0),
            'valid_count': waiver_review.get('valid_count', 0),
            'expired_count': waiver_review.get('expired_count', 0),
            'missing_count': waiver_review.get('missing_count', 0),
        }
        report['run_meta']['notes'].append(
            (
                'Baseline diff: introduced='
                f"{baseline_diff['introduced_count']}, "
                f"resolved={baseline_diff['resolved_count']}, "
                f"persistent={baseline_diff['persistent_count']}."
            )
        )
        if waiver_review['expired_count'] > 0:
            report['run_meta']['notes'].append(
                'Baseline waiver review: '
                f"{waiver_review['expired_count']} expired waiver(s) need renewal or retirement."
            )
        if waiver_review['missing_count'] > 0:
            report['run_meta']['notes'].append(
                'Baseline waiver review: '
                f"{waiver_review['missing_count']} accepted signature(s) missing waiver metadata."
            )

    baseline_evidence: dict[str, Any] | None = None
    if args.baseline_evidence_mode != 'none':
        baseline_evidence = _build_run_baseline_evidence(
            report=report,
            baseline_report=baseline_report,
            signature_config=baseline_signature_config,
            evidence_mode=args.baseline_evidence_mode,
        )
        report['run_meta']['baseline_evidence'] = baseline_evidence
        report.setdefault('summary', {})['baseline_evidence'] = {
            'mode': baseline_evidence.get('mode'),
            'baseline_verification': baseline_evidence.get('baseline_verification', {}),
        }
        if baseline_report:
            report['run_meta']['notes'].append(
                'Baseline evidence verification: '
                + ('passed' if baseline_evidence['baseline_verification'].get('verified') else 'missing declaration')
                + f" (mode={args.baseline_evidence_mode})."
            )

    _sort_report_findings(report, args.sort_findings)
    report['run_meta']['sorting'] = {
        'mode': args.sort_findings,
        'deterministic': True,
        'finding_count': len(report.get('findings', [])),
    }

    gate_findings = list(report.get('findings', []))
    risk_calibration_gate_failed = False
    risk_calibration = _evaluate_risk_calibration(
        report=report,
        source_path=args.risk_calibration_source,
        mode=args.risk_calibration_mode,
    )
    if (
        args.risk_calibration_mode == 'strict'
        and risk_calibration.get('applied')
        and risk_calibration.get('unstable_high_severity_rules')
    ):
        risk_calibration_gate_failed = True
    risk_calibration['gate'] = {
        'mode': args.risk_calibration_mode,
        'failed': risk_calibration_gate_failed,
        'exit_code': RISK_CALIBRATION_EXIT_CODE if risk_calibration_gate_failed else 0,
    }
    report['run_meta']['risk_calibration'] = risk_calibration
    report.setdefault('summary', {})['risk_calibration'] = {
        'mode': risk_calibration.get('mode'),
        'applied': bool(risk_calibration.get('applied')),
        'downgrade_reason': risk_calibration.get('downgrade_reason'),
        'unstable_high_severity_rule_count': len(risk_calibration.get('unstable_high_severity_rules', [])),
    }
    if risk_calibration.get('applied'):
        report['run_meta']['notes'].append(
            'Risk calibration applied: '
            f"{len(risk_calibration.get('rules', []))} rules evaluated, "
            f"{len(risk_calibration.get('unstable_high_severity_rules', []))} unstable high-severity rule(s)."
        )
    elif args.risk_calibration_mode != 'off':
        downgrade_reason = str(risk_calibration.get('downgrade_reason') or 'missing-evidence')
        downgrade_message = str((risk_calibration.get('source_meta') or {}).get('message') or '').strip()
        note = (
            'Risk calibration downgraded '
            f'({downgrade_reason}): {downgrade_message}. '
            'Continuing without calibration gate.'
        )
        report['run_meta']['notes'].append(note)

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
    replay_summary_path: Path | None = None
    replay_diff_path: Path | None = None
    replay_verification: dict[str, Any] | None = None
    if args.replay_verify_from:
        replay_dir = Path(args.replay_verify_from)
        replay_source_report, replay_source_path = _load_replay_source_report(replay_dir)
        replay_verification = _build_replay_verification_summary(
            current_report=report,
            replay_source_report=replay_source_report,
            replay_source_path=replay_source_path,
            replay_source_dir=replay_dir,
        )
        replay_summary_path = output_dir / 'replay-summary.json'
        replay_diff_path = output_dir / 'replay-diff.md'
        replay_summary_path.write_text(json.dumps(replay_verification, ensure_ascii=False, indent=2), encoding='utf-8')
        _build_replay_diff_markdown(replay_verification, replay_diff_path)
        report['run_meta']['replay_verification'] = {
            'source_report_dir': str(replay_dir),
            'summary_path': str(replay_summary_path),
            'diff_path': str(replay_diff_path),
            'status_counts': replay_verification.get('status_counts', {}),
            'non_deterministic_reasons': replay_verification.get('non_deterministic_reasons', []),
            'gate': replay_verification.get('gate', {}),
        }
        report.setdefault('summary', {})['replay_verification'] = {
            'status_counts': replay_verification.get('status_counts', {}),
            'non_deterministic_count': replay_verification.get('status_counts', {}).get('non-deterministic', 0),
            'gate_failed': bool(replay_verification.get('gate', {}).get('failed')),
        }
        report['run_meta']['notes'].append(
            'Replay verification: '
            f"resolved={replay_verification['status_counts']['resolved']}, "
            f"unchanged={replay_verification['status_counts']['unchanged']}, "
            f"regressed={replay_verification['status_counts']['regressed']}, "
            f"non-deterministic={replay_verification['status_counts']['non-deterministic']}."
        )
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

    waiver_gate = {
        'mode': args.waiver_expiry_mode,
        'evaluated_count': waiver_review.get('accepted_count', 0) if waiver_review else 0,
        'expired_count': waiver_review.get('expired_count', 0) if waiver_review else 0,
        'failed': False,
        'exit_code': 0,
    }
    if waiver_review and args.waiver_expiry_mode in {'warn', 'fail'} and waiver_review.get('expired_count', 0) > 0:
        if args.waiver_expiry_mode == 'warn':
            report['run_meta']['notes'].append(
                'Waiver expiry gate warning: expired waivers detected; renew or retire accepted debt.'
            )
        else:
            waiver_gate['failed'] = True
            waiver_gate['exit_code'] = WAIVER_EXPIRY_EXIT_CODE
            should_fail = True
            exit_code = WAIVER_EXPIRY_EXIT_CODE
            report['run_meta']['notes'].append(
                'Waiver expiry gate failed: expired waivers detected under --waiver-expiry-mode=fail.'
            )
    report['run_meta']['waiver_gate'] = waiver_gate

    if risk_calibration_gate_failed:
        if not should_fail:
            should_fail = True
            exit_code = RISK_CALIBRATION_EXIT_CODE
        report['run_meta']['notes'].append(
            'Risk calibration gate failed: unstable high-severity rules detected under --risk-calibration-mode=strict '
            f"({', '.join(risk_calibration.get('unstable_high_severity_rules', []))})."
        )
    if replay_verification and replay_verification.get('gate', {}).get('failed'):
        if not should_fail:
            should_fail = True
            exit_code = REPLAY_VERIFICATION_EXIT_CODE
        report['run_meta']['notes'].append(
            'Replay verification gate failed: high-severity regressed findings were introduced.'
        )

    debt_trend_payload = _build_debt_trend_payload(
        now_utc=datetime.now(timezone.utc),
        window=args.debt_trend_window,
        baseline_report=baseline_report,
        baseline_report_path=args.baseline_report,
        debt_transitions=debt_transitions,
        waiver_review=waiver_review,
    )
    debt_trend_path = output_dir / 'debt-trend.json'
    debt_trend_path.write_text(json.dumps(debt_trend_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    trend_summary = debt_trend_payload.get('summary', {})
    report['run_meta']['debt_trend'] = {
        'schema_version': debt_trend_payload.get('schema_version'),
        'window': debt_trend_payload.get('window'),
        'artifact_path': str(debt_trend_path),
        'latest_counts': trend_summary.get('latest_counts', _empty_debt_trend_counts()),
        'delta_from_previous': trend_summary.get('delta_from_previous', _empty_debt_trend_counts()),
        'history_meta': debt_trend_payload.get('history_meta', {}),
    }
    report.setdefault('summary', {})['debt_trend'] = {
        'window': debt_trend_payload.get('window'),
        'latest_counts': trend_summary.get('latest_counts', _empty_debt_trend_counts()),
        'delta_from_previous': trend_summary.get('delta_from_previous', _empty_debt_trend_counts()),
        'history_points_used': trend_summary.get('history_points_used', 0),
    }
    history_reset_reason = str((debt_trend_payload.get('history_meta') or {}).get('history_reset_reason') or '')
    if history_reset_reason:
        report['run_meta']['notes'].append(
            'Debt trend history reset reason: ' + history_reset_reason
        )
    report['run_meta']['notes'].append(
        f"Debt trend: new={report['summary']['debt_trend']['latest_counts'][DEBT_STATE_NEW]}, "
        f"accepted={report['summary']['debt_trend']['latest_counts'][DEBT_STATE_ACCEPTED]}, "
        f"retired={report['summary']['debt_trend']['latest_counts'][DEBT_STATE_RETIRED]}, "
        f"regressed={report['summary']['debt_trend']['latest_counts'][DEBT_STATE_REGRESSED]} "
        f"(window={args.debt_trend_window})."
    )

    artifact_manifest_path = output_dir / 'artifact-manifest.json'
    report['run_meta']['artifact_manifest'] = {
        'path': str(artifact_manifest_path),
        'algorithm': 'sha256',
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

    artifact_paths: dict[str, Path] = {
        'markdown-report': output_md,
        'report-schema': staged_schema_path,
    }
    if report_format == 'json':
        artifact_paths['machine-report-json'] = output_json
    else:
        artifact_paths['machine-report-sarif'] = machine_output

    if effective_policy_output is not None:
        artifact_paths['effective-policy'] = effective_policy_output
    artifact_paths['debt-trend'] = debt_trend_path
    if replay_summary_path is not None:
        artifact_paths['replay-summary'] = replay_summary_path
    if replay_diff_path is not None:
        artifact_paths['replay-diff'] = replay_diff_path
    if diff_path is not None:
        artifact_paths['fixes-diff'] = diff_path
    if snapshot_path is not None:
        artifact_paths['fixes-snapshot'] = snapshot_path

    axe_raw = output_dir / 'axe.raw.json'
    lighthouse_raw = output_dir / 'lighthouse.raw.json'
    artifact_paths['axe-raw'] = axe_raw
    artifact_paths['lighthouse-raw'] = lighthouse_raw

    _, manifest_path = _build_artifact_manifest(
        output_dir=output_dir,
        report_format=report_format,
        target=contract.target,
        artifact_paths=artifact_paths,
        baseline_evidence=baseline_evidence,
    )
    report['run_meta']['artifact_manifest']['path'] = str(manifest_path)

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
            if report['run_meta'].get('waiver_gate', {}).get('failed'):
                print('Waiver gate failed: one or more accepted debt waivers are expired.')
            elif report['run_meta'].get('risk_calibration', {}).get('gate', {}).get('failed'):
                print('Risk calibration gate failed: unstable high-severity rule outcomes detected.')
            elif report['run_meta'].get('replay_verification', {}).get('gate', {}).get('failed'):
                print('Replay verification gate failed: high-severity regressed findings detected.')
            elif fail_on:
                print(f'Policy gate failed: unresolved finding severity >= {fail_on}')
    if should_fail:
        return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

