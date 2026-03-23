#!/usr/bin/env python3
"""Baseline governance helpers for accessibility audit orchestration."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname

BASELINE_TARGET_NORMALIZATION_MODES = {"none", "host-path", "path-only"}
BASELINE_SELECTOR_CANONICALIZATION_MODES = {"none", "basic"}
BASELINE_EVIDENCE_MODES = {"none", "hash", "hash-chain"}
WAIVER_EXPIRY_MODES = {"ignore", "warn", "fail"}
WAIVER_EXPIRY_EXIT_CODE = 45
DEBT_STATE_NEW = "new"
DEBT_STATE_ACCEPTED = "accepted"
DEBT_STATE_RETIRED = "retired"
DEBT_STATE_REGRESSED = "regressed"
DEBT_WAIVER_REQUIRED_FIELDS = {"signature", "owner", "approved_at", "expires_at", "reason"}
DEBT_TREND_SCHEMA_VERSION = "1.0.0"
REPORT_SCHEMA_VERSION = "1.0.0"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finding_signature(finding: dict[str, Any]) -> str:
    rule_id = str(finding.get("rule_id", "")).strip()
    target = str(finding.get("changed_target", "")).strip()
    return f"{rule_id}|{target}"


def _normalize_signature_target(target: str, mode: str) -> str:
    value = str(target or "").strip()
    if not value or mode == "none":
        return value

    parsed = urlparse(value)
    if parsed.scheme == "file":
        file_path = Path(url2pathname(parsed.path)).as_posix().lower()
        return file_path
    if parsed.scheme in {"http", "https"}:
        host = parsed.netloc.lower()
        path = parsed.path or "/"
        if mode == "path-only":
            return path
        return f"{host}{path}"

    local_path = Path(value).as_posix().lower()
    return local_path


def _canonicalize_signature_selector(selector: str, mode: str) -> str:
    value = str(selector or "").strip()
    if mode != "basic" or not value:
        return value
    normalized = " ".join(value.split())
    normalized = normalized.replace(" > ", ">").replace("> ", ">").replace(" >", ">")
    return normalized


def _build_baseline_signature_config(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "include_target_in_signature": bool(args.baseline_include_target),
        "target_normalization": args.baseline_target_normalization,
        "selector_canonicalization": args.baseline_selector_canonicalization,
    }


def _finding_signature_with_config(
    finding: dict[str, Any],
    signature_config: dict[str, Any] | None,
    report_target: str = "",
) -> str:
    effective_signature_config = signature_config or {}
    selector = _canonicalize_signature_selector(
        str(finding.get("changed_target", "")).strip(),
        str(effective_signature_config.get("selector_canonicalization", "none")),
    )
    if not effective_signature_config.get("include_target_in_signature"):
        return f"{str(finding.get('rule_id', '')).strip()}|{selector}"
    target = _normalize_signature_target(
        report_target,
        str(effective_signature_config.get("target_normalization", "none")),
    )
    return f"{str(finding.get('rule_id', '')).strip()}|{target}|{selector}"


def _unresolved_finding_signatures(
    report: dict[str, Any],
    signature_config: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    effective_signature_config = signature_config or {}
    report_target = str(report.get("target", {}).get("value", "")).strip()
    signatures: dict[str, dict[str, Any]] = {}
    for finding in report.get("findings", []):
        if not isinstance(finding, dict):
            continue
        status = str(finding.get("status", "")).strip().lower()
        if status == "fixed":
            continue
        signatures[_finding_signature_with_config(finding, effective_signature_config, report_target)] = finding
    return signatures


def _build_baseline_evidence_material(
    report: dict[str, Any],
    signature_config: dict[str, Any],
) -> dict[str, Any]:
    signatures = sorted(_unresolved_finding_signatures(report, signature_config))
    target = str(report.get("target", {}).get("value", "")).strip()
    return {
        "target": target,
        "signature_config": signature_config,
        "unresolved_signatures": signatures,
    }


def _compute_report_evidence_hash(
    report: dict[str, Any],
    signature_config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    material = _build_baseline_evidence_material(report, signature_config)
    canonical = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_text(canonical), material


def _verify_baseline_report_evidence(
    baseline_report: dict[str, Any],
    signature_config: dict[str, Any],
) -> dict[str, Any]:
    baseline_hash, _ = _compute_report_evidence_hash(baseline_report, signature_config)
    evidence = baseline_report.get("run_meta", {}).get("baseline_evidence", {})
    declared_hash = str(evidence.get("report_hash", "")).strip() if isinstance(evidence, dict) else ""
    declared_chain = str(evidence.get("chain_hash", "")).strip() if isinstance(evidence, dict) else ""
    declared_parent_hash = (
        str(evidence.get("baseline_report_hash", "")).strip() if isinstance(evidence, dict) else ""
    )

    if declared_hash and declared_hash != baseline_hash:
        raise ValueError(
            "baseline evidence verification failed: declared report_hash does not match baseline report content"
        )

    if declared_chain:
        expected_chain = _sha256_text(f"{declared_parent_hash}:{baseline_hash}") if declared_parent_hash else baseline_hash
        if declared_chain != expected_chain:
            raise ValueError(
                "baseline evidence verification failed: declared chain_hash does not match baseline report lineage"
            )

    return {
        "declared": bool(declared_hash),
        "verified": not declared_hash or declared_hash == baseline_hash,
        "baseline_report_hash": baseline_hash,
        "baseline_chain_hash": declared_chain,
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
        "declared": False,
        "verified": False,
        "baseline_report_hash": "",
        "baseline_chain_hash": "",
    }
    if baseline_report:
        baseline_verification = _verify_baseline_report_evidence(baseline_report, signature_config)

    evidence: dict[str, Any] = {
        "mode": evidence_mode,
        "generated_at": _utc_timestamp(),
        "report_hash": current_hash,
        "signature_count": len(material.get("unresolved_signatures", [])),
        "signature_config": signature_config,
    }
    if evidence_mode == "hash-chain":
        parent_hash = (
            baseline_verification.get("baseline_chain_hash")
            or baseline_verification.get("baseline_report_hash")
            or ""
        )
        evidence["baseline_report_hash"] = baseline_verification.get("baseline_report_hash", "")
        evidence["baseline_chain_parent"] = parent_hash
        evidence["chain_hash"] = _sha256_text(f"{parent_hash}:{current_hash}") if parent_hash else current_hash
    elif baseline_verification.get("baseline_report_hash"):
        evidence["baseline_report_hash"] = baseline_verification.get("baseline_report_hash", "")

    evidence["baseline_verification"] = {
        "declared": baseline_verification.get("declared", False),
        "verified": baseline_verification.get("verified", False),
    }
    return evidence


def _parse_waiver_timestamp(value: str, field: str, index: int) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as err:
        raise ValueError(f"--baseline-report debt_waivers[{index}].{field} must be ISO8601 with timezone") from err
    if parsed.tzinfo is None:
        raise ValueError(f"--baseline-report debt_waivers[{index}].{field} must include timezone offset")
    return parsed.astimezone(timezone.utc)


def _validate_debt_waivers(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("--baseline-report debt_waivers must be a list")
    validated: list[dict[str, str]] = []
    seen_signatures: set[str] = set()
    for index, raw_waiver in enumerate(value):
        if not isinstance(raw_waiver, dict):
            raise ValueError(f"--baseline-report debt_waivers[{index}] must be a JSON object")
        missing_keys = sorted(DEBT_WAIVER_REQUIRED_FIELDS - set(raw_waiver))
        unknown_keys = sorted(set(raw_waiver) - DEBT_WAIVER_REQUIRED_FIELDS)
        if missing_keys or unknown_keys:
            raise ValueError(
                f"--baseline-report debt_waivers[{index}] must contain exactly keys: "
                "signature, owner, approved_at, expires_at, reason "
                f'(missing: {missing_keys or "none"}, unknown: {unknown_keys or "none"})'
            )
        waiver: dict[str, str] = {}
        for field in sorted(DEBT_WAIVER_REQUIRED_FIELDS):
            raw_value = raw_waiver.get(field)
            if not isinstance(raw_value, str) or not raw_value.strip():
                raise ValueError(f"--baseline-report debt_waivers[{index}].{field} must be a non-empty string")
            waiver[field] = raw_value.strip()
        if waiver["signature"] in seen_signatures:
            raise ValueError(f'--baseline-report debt_waivers[{index}].signature is duplicated: {waiver["signature"]}')
        approved_at = _parse_waiver_timestamp(waiver["approved_at"], "approved_at", index)
        expires_at = _parse_waiver_timestamp(waiver["expires_at"], "expires_at", index)
        if expires_at <= approved_at:
            raise ValueError(f"--baseline-report debt_waivers[{index}] expires_at must be later than approved_at")
        waiver["approved_at"] = approved_at.isoformat().replace("+00:00", "Z")
        waiver["expires_at"] = expires_at.isoformat().replace("+00:00", "Z")
        seen_signatures.add(waiver["signature"])
        validated.append(waiver)
    return validated


def _load_baseline_report(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    baseline_path = Path(path)
    if not baseline_path.exists():
        raise ValueError(f"baseline report file does not exist: {path}")
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--baseline-report must point to a JSON object")
    findings = payload.get("findings")
    if findings is None:
        payload["findings"] = []
    elif not isinstance(findings, list):
        raise ValueError("--baseline-report JSON must include findings as a list")
    payload["debt_waivers"] = _validate_debt_waivers(payload.get("debt_waivers"))
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
        DEBT_STATE_NEW: _coerce_non_negative_int(((transitions.get(DEBT_STATE_NEW) or {}).get("count"))),
        DEBT_STATE_ACCEPTED: _coerce_non_negative_int(((transitions.get(DEBT_STATE_ACCEPTED) or {}).get("count"))),
        DEBT_STATE_RETIRED: _coerce_non_negative_int(((transitions.get(DEBT_STATE_RETIRED) or {}).get("count"))),
        DEBT_STATE_REGRESSED: _coerce_non_negative_int((waiver_review or {}).get("expired_count")),
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
    counts = raw.get("counts")
    if not isinstance(counts, dict):
        return None
    return {
        "recorded_at": str(raw.get("recorded_at", "")).strip() or "",
        "source_report": str(raw.get("source_report", "")).strip() or "",
        "counts": {
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
    run_meta = baseline_report.get("run_meta")
    if not isinstance(run_meta, dict):
        return None
    baseline_diff = run_meta.get("baseline_diff")
    if not isinstance(baseline_diff, dict):
        return None
    transitions = baseline_diff.get("debt_transitions")
    if not isinstance(transitions, dict):
        return None
    waiver_review = baseline_diff.get("waiver_review")
    if not isinstance(waiver_review, dict):
        waiver_review = None
    counts = _build_debt_trend_counts(transitions, waiver_review)
    recorded_at = str(run_meta.get("generated_at") or run_meta.get("completed_at") or "").strip()
    source_report = baseline_report_path or str(baseline_diff.get("baseline_report_path", "")).strip()
    return {
        "recorded_at": recorded_at,
        "source_report": source_report,
        "counts": counts,
    }


def _extract_historical_debt_trend_points(
    baseline_report: dict[str, Any],
    baseline_report_path: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    report_schema_version = str(
        ((baseline_report.get("report_schema") or {}).get("version")) if isinstance(baseline_report, dict) else ""
    ).strip()
    if report_schema_version and report_schema_version != REPORT_SCHEMA_VERSION:
        return [], {
            "history_reset_reason": "schema-version-mismatch",
            "baseline_report_schema_version": report_schema_version,
            "expected_report_schema_version": REPORT_SCHEMA_VERSION,
            "loaded_point_count": 0,
        }

    run_meta = baseline_report.get("run_meta")
    if not isinstance(run_meta, dict):
        return [], {"history_reset_reason": "missing-history", "loaded_point_count": 0}
    trend = run_meta.get("debt_trend")
    if not isinstance(trend, dict):
        fallback = _derive_baseline_point_from_legacy_report(baseline_report, baseline_report_path)
        if fallback:
            return [fallback], {"history_reset_reason": "legacy-fallback", "loaded_point_count": 1}
        return [], {"history_reset_reason": "missing-history", "loaded_point_count": 0}

    schema_version = str(trend.get("schema_version", "")).strip()
    if schema_version and schema_version != DEBT_TREND_SCHEMA_VERSION:
        return [], {
            "history_reset_reason": "trend-schema-version-mismatch",
            "baseline_trend_schema_version": schema_version,
            "expected_trend_schema_version": DEBT_TREND_SCHEMA_VERSION,
            "loaded_point_count": 0,
        }
    raw_points = trend.get("points")
    if not isinstance(raw_points, list):
        return [], {"history_reset_reason": "missing-history", "loaded_point_count": 0}
    points = [point for point in (_sanitize_debt_trend_point(item) for item in raw_points) if point is not None]
    return points, {"history_reset_reason": None, "loaded_point_count": len(points)}


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
        "recorded_at": now_utc.isoformat().replace("+00:00", "Z"),
        "source_report": baseline_report_path or "",
        "counts": _build_debt_trend_counts(debt_transitions, waiver_review),
    }
    merged_points = history_points + [current_point]
    points = merged_points[-window:]
    previous = points[-2]["counts"] if len(points) > 1 else _empty_debt_trend_counts()
    latest = points[-1]["counts"]
    delta = {
        DEBT_STATE_NEW: latest[DEBT_STATE_NEW] - previous[DEBT_STATE_NEW],
        DEBT_STATE_ACCEPTED: latest[DEBT_STATE_ACCEPTED] - previous[DEBT_STATE_ACCEPTED],
        DEBT_STATE_RETIRED: latest[DEBT_STATE_RETIRED] - previous[DEBT_STATE_RETIRED],
        DEBT_STATE_REGRESSED: latest[DEBT_STATE_REGRESSED] - previous[DEBT_STATE_REGRESSED],
    }
    return {
        "schema_version": DEBT_TREND_SCHEMA_VERSION,
        "generated_at": now_utc.isoformat().replace("+00:00", "Z"),
        "window": window,
        "points": points,
        "summary": {
            "total_points": len(points),
            "history_points_used": max(0, len(points) - 1),
            "latest_counts": latest,
            "delta_from_previous": delta,
        },
        "history_meta": history_meta,
    }


def _build_baseline_diff(
    current_report: dict[str, Any],
    baseline_report: dict[str, Any],
    signature_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_signature_config = signature_config or {}
    current_findings = _unresolved_finding_signatures(current_report, effective_signature_config)
    baseline_findings = _unresolved_finding_signatures(baseline_report, effective_signature_config)
    current_signatures = set(current_findings)
    baseline_signatures = set(baseline_findings)
    introduced = sorted(current_signatures - baseline_signatures)
    resolved = sorted(baseline_signatures - current_signatures)
    persistent = sorted(current_signatures & baseline_signatures)
    return {
        "current_unresolved_count": len(current_signatures),
        "baseline_unresolved_count": len(baseline_signatures),
        "introduced_count": len(introduced),
        "resolved_count": len(resolved),
        "persistent_count": len(persistent),
        "introduced_signatures": introduced,
        "resolved_signatures": resolved,
        "persistent_signatures": persistent,
        "introduced_findings": [current_findings[key] for key in introduced],
        "signature_config": effective_signature_config,
    }


def _build_debt_transition_summary(baseline_diff: dict[str, Any]) -> dict[str, Any]:
    introduced = baseline_diff.get("introduced_signatures", [])
    persistent = baseline_diff.get("persistent_signatures", [])
    resolved = baseline_diff.get("resolved_signatures", [])
    return {
        DEBT_STATE_NEW: {"count": len(introduced), "signatures": list(introduced)},
        DEBT_STATE_ACCEPTED: {"count": len(persistent), "signatures": list(persistent)},
        DEBT_STATE_RETIRED: {"count": len(resolved), "signatures": list(resolved)},
    }


def _build_debt_waiver_index(baseline_report: dict[str, Any]) -> dict[str, dict[str, str]]:
    waivers = baseline_report.get("debt_waivers", [])
    if not isinstance(waivers, list):
        return {}
    index: dict[str, dict[str, str]] = {}
    for waiver in waivers:
        if isinstance(waiver, dict):
            signature = str(waiver.get("signature", "")).strip()
            if signature:
                index[signature] = dict(waiver)
    return index


def _evaluate_debt_waiver_review(
    baseline_diff: dict[str, Any],
    baseline_report: dict[str, Any],
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    persistent = list(baseline_diff.get("persistent_signatures", []))
    waiver_index = _build_debt_waiver_index(baseline_report)
    valid_waivers: list[dict[str, str]] = []
    expired_waivers: list[dict[str, str]] = []
    missing_signatures: list[str] = []
    for signature in persistent:
        waiver = waiver_index.get(signature)
        if not waiver:
            missing_signatures.append(signature)
            continue
        expires_at = datetime.fromisoformat(waiver["expires_at"].replace("Z", "+00:00"))
        waiver_entry = {
            "signature": signature,
            "owner": str(waiver["owner"]),
            "approved_at": str(waiver["approved_at"]),
            "expires_at": str(waiver["expires_at"]),
            "reason": str(waiver["reason"]),
        }
        if expires_at <= now:
            expired_waivers.append(waiver_entry)
        else:
            valid_waivers.append(waiver_entry)
    return {
        "accepted_count": len(persistent),
        "valid_count": len(valid_waivers),
        "expired_count": len(expired_waivers),
        "missing_count": len(missing_signatures),
        "valid_waivers": valid_waivers,
        "expired_waivers": expired_waivers,
        "missing_signatures": missing_signatures,
        "evaluated_at": now.isoformat().replace("+00:00", "Z"),
    }


def _tag_findings_with_debt_state(
    report: dict[str, Any],
    baseline_diff: dict[str, Any],
    signature_config: dict[str, Any] | None = None,
) -> None:
    effective_signature_config = signature_config or {}
    report_target = str(report.get("target", {}).get("value", "")).strip()
    introduced = set(baseline_diff.get("introduced_signatures", []))
    persistent = set(baseline_diff.get("persistent_signatures", []))
    resolved = set(baseline_diff.get("resolved_signatures", []))

    for finding in report.get("findings", []):
        if not isinstance(finding, dict):
            continue
        signature = _finding_signature_with_config(finding, effective_signature_config, report_target)
        if signature in introduced:
            finding["debt_state"] = DEBT_STATE_NEW
        elif signature in persistent:
            finding["debt_state"] = DEBT_STATE_ACCEPTED
        elif signature in resolved:
            finding["debt_state"] = DEBT_STATE_RETIRED


__all__ = [
    "BASELINE_EVIDENCE_MODES",
    "BASELINE_SELECTOR_CANONICALIZATION_MODES",
    "BASELINE_TARGET_NORMALIZATION_MODES",
    "DEBT_STATE_ACCEPTED",
    "DEBT_STATE_NEW",
    "DEBT_STATE_REGRESSED",
    "DEBT_STATE_RETIRED",
    "DEBT_TREND_SCHEMA_VERSION",
    "DEBT_WAIVER_REQUIRED_FIELDS",
    "WAIVER_EXPIRY_EXIT_CODE",
    "WAIVER_EXPIRY_MODES",
    "_build_baseline_diff",
    "_build_baseline_signature_config",
    "_build_debt_transition_summary",
    "_build_debt_trend_payload",
    "_build_run_baseline_evidence",
    "_canonicalize_signature_selector",
    "_coerce_non_negative_int",
    "_compute_report_evidence_hash",
    "_empty_debt_trend_counts",
    "_evaluate_debt_waiver_review",
    "_finding_signature_with_config",
    "_load_baseline_report",
    "_normalize_signature_target",
    "_sha256_file",
    "_tag_findings_with_debt_state",
    "_unresolved_finding_signatures",
    "_validate_debt_waivers",
    "_utc_timestamp",
]
