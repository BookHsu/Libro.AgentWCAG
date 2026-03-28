#!/usr/bin/env python3
"""Aggregate multiple wcag-report.json files into a unified summary report.

Implements TODO items from 20260328_report_todo.md:
  A1: Executive Summary (scope, compliance rate, verdict)
  A2: Severity Breakdown (counts, percentages)
  A3: Fixability Analysis (auto-fix/assisted/manual)
  A4: Per-Target Breakdown (per-page severity + status)
  A5: WCAG SC Coverage Analysis (principle grouping, uncovered SCs)
  A6: Top Issues (top N rules, top N targets)
  A7: Auto-Fix Opportunity (framework group, residual, command)
  B1: JSON aggregate output structure
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEVERITY_LEVELS = ("critical", "serious", "moderate", "minor", "info")
FIXABILITY_LEVELS = ("auto-fix", "assisted", "manual")
VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_NEEDS_REVIEW = "needs-review"
TARGET_STATUS_CLEAN = "clean"
TARGET_STATUS_ISSUES = "issues"
TARGET_STATUS_CRITICAL = "critical"


def load_report(path: Path) -> dict[str, Any]:
    """Load and minimally validate a single wcag-report.json."""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    if "findings" not in data:
        raise ValueError(f"Missing 'findings' key in {path}")
    return data


def load_reports(paths: list[Path]) -> list[dict[str, Any]]:
    """Load multiple report files, raising on first failure."""
    return [load_report(p) for p in paths]


def _percentage(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total * 100, 1)


def _target_status(findings: list[dict[str, Any]]) -> str:
    """Determine target status from its findings."""
    if not findings:
        return TARGET_STATUS_CLEAN
    severities = {f.get("severity") for f in findings}
    if "critical" in severities:
        return TARGET_STATUS_CRITICAL
    return TARGET_STATUS_ISSUES


def _determine_verdict(
    total_targets: int,
    clean_targets: int,
    has_critical: bool,
) -> str:
    if total_targets == 0:
        return VERDICT_PASS
    if has_critical:
        return VERDICT_FAIL
    if clean_targets == total_targets:
        return VERDICT_PASS
    return VERDICT_NEEDS_REVIEW


def _collect_all_findings(
    reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten findings from all reports."""
    all_findings: list[dict[str, Any]] = []
    for report in reports:
        all_findings.extend(report.get("findings", []))
    return all_findings


def _build_scope(
    reports: list[dict[str, Any]],
    all_findings: list[dict[str, Any]],
    wcag_version: str,
    conformance_level: str,
) -> dict[str, Any]:
    """A1: Executive Summary — scope section."""
    total_targets = len(reports)
    targets_with_issues = sum(
        1 for r in reports if r.get("findings")
    )
    clean_targets = total_targets - targets_with_issues
    total_findings = len(all_findings)
    has_critical = any(
        f.get("severity") == "critical" for f in all_findings
    )
    return {
        "total_targets": total_targets,
        "targets_with_issues": targets_with_issues,
        "clean_targets": clean_targets,
        "total_findings": total_findings,
        "compliance_rate": _percentage(clean_targets, total_targets) / 100,
        "wcag_version": wcag_version,
        "conformance_level": conformance_level,
        "verdict": _determine_verdict(total_targets, clean_targets, has_critical),
    }


def _build_severity(
    all_findings: list[dict[str, Any]],
) -> dict[str, dict[str, int | float]]:
    """A2: Severity Breakdown."""
    total = len(all_findings)
    counts = Counter(f.get("severity", "info") for f in all_findings)
    return {
        level: {
            "count": counts.get(level, 0),
            "percentage": _percentage(counts.get(level, 0), total),
        }
        for level in SEVERITY_LEVELS
    }


def _build_fixability(
    all_findings: list[dict[str, Any]],
) -> dict[str, dict[str, int | float]]:
    """A3: Fixability Analysis."""
    total = len(all_findings)
    counts = Counter(f.get("fixability", "manual") for f in all_findings)
    result: dict[str, dict[str, int | float]] = {
        level: {
            "count": counts.get(level, 0),
            "percentage": _percentage(counts.get(level, 0), total),
        }
        for level in FIXABILITY_LEVELS
    }
    auto_fix_count = counts.get("auto-fix", 0)
    result["fix_coverage"] = _percentage(auto_fix_count, total) / 100
    return result


def _build_targets(
    reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """A4: Per-Target Breakdown."""
    targets: list[dict[str, Any]] = []
    for report in reports:
        target_value = report.get("target", {}).get("value", "unknown")
        findings = report.get("findings", [])
        severity_counts: dict[str, int] = {}
        for level in SEVERITY_LEVELS:
            count = sum(1 for f in findings if f.get("severity") == level)
            if count > 0:
                severity_counts[level] = count
        auto_fixable = sum(
            1 for f in findings if f.get("fixability") == "auto-fix"
        )
        targets.append({
            "target": target_value,
            "total_findings": len(findings),
            "severity": severity_counts,
            "auto_fixable": auto_fixable,
            "status": _target_status(findings),
        })
    targets.sort(key=lambda t: t["total_findings"], reverse=True)
    return targets


def _build_remediation_lifecycle(
    reports: list[dict[str, Any]],
    all_findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """A8 (partial): Remediation lifecycle from existing fix data."""
    planned = 0
    implemented = 0
    verified = 0
    manual_review_required = 0
    for report in reports:
        lifecycle = report.get("summary", {}).get("remediation_lifecycle", {})
        planned += lifecycle.get("planned", 0)
        implemented += lifecycle.get("implemented", 0)
        verified += lifecycle.get("verified", 0)
        manual_review_required += lifecycle.get("manual_review_required", 0)
    total = len(all_findings)
    return {
        "planned": planned,
        "implemented": implemented,
        "verified": verified,
        "manual_review_required": manual_review_required,
        "fix_coverage": _percentage(implemented + verified, total) / 100 if total else 0.0,
    }


WCAG_PRINCIPLE_PREFIXES = {
    "perceivable": "1.",
    "operable": "2.",
    "understandable": "3.",
    "robust": "4.",
}

DEFAULT_TOP_N = 10


def _build_wcag_principles(
    all_findings: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """A5: WCAG SC Coverage — group findings by WCAG principle."""
    principle_sc: dict[str, set[str]] = {p: set() for p in WCAG_PRINCIPLE_PREFIXES}
    principle_counts: dict[str, int] = {p: 0 for p in WCAG_PRINCIPLE_PREFIXES}

    for finding in all_findings:
        for sc in finding.get("sc", []):
            for principle, prefix in WCAG_PRINCIPLE_PREFIXES.items():
                if sc.startswith(prefix):
                    principle_sc[principle].add(sc)
                    principle_counts[principle] += 1
                    break

    return {
        principle: {
            "count": principle_counts[principle],
            "sc": sorted(principle_sc[principle]),
        }
        for principle in WCAG_PRINCIPLE_PREFIXES
    }


def _build_top_rules(
    all_findings: list[dict[str, Any]],
    top_n: int = DEFAULT_TOP_N,
) -> list[dict[str, Any]]:
    """A6: Top Issues — most frequent rules across all targets."""
    rule_counter: Counter[str] = Counter()
    rule_fixability: dict[str, str] = {}
    rule_sc: dict[str, set[str]] = {}

    for finding in all_findings:
        rule_id = finding.get("rule_id", "unknown")
        rule_counter[rule_id] += 1
        if rule_id not in rule_fixability:
            rule_fixability[rule_id] = finding.get("fixability", "manual")
        rule_sc.setdefault(rule_id, set()).update(finding.get("sc", []))

    return [
        {
            "rule_id": rule_id,
            "count": count,
            "fixability": rule_fixability.get(rule_id, "manual"),
            "sc": sorted(rule_sc.get(rule_id, set())),
        }
        for rule_id, count in rule_counter.most_common(top_n)
    ]


def _build_auto_fix_opportunity(
    all_findings: list[dict[str, Any]],
    reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """A7: Auto-fix opportunity with framework grouping."""
    fixable_count = sum(
        1 for f in all_findings if f.get("fixability") == "auto-fix"
    )
    total = len(all_findings)
    estimated_residual = total - fixable_count

    # Gather framework hints from fixes across reports
    framework_counts: Counter[str] = Counter()
    for report in reports:
        for fix in report.get("fixes", []):
            hints = fix.get("framework_hints", {})
            for framework in hints:
                framework_counts[framework] += 1

    result: dict[str, Any] = {
        "fixable_count": fixable_count,
        "estimated_residual": estimated_residual,
        "command": "libro scan <directory> --execution-mode apply-fixes",
    }
    if framework_counts:
        result["framework_groups"] = [
            {"framework": fw, "count": c}
            for fw, c in framework_counts.most_common()
        ]
    return result


def _build_baseline_diff(
    reports: list[dict[str, Any]],
    baseline_reports: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """A9: Trend / Baseline Diff — compare current vs prior run."""
    if not baseline_reports:
        return None

    current_sigs = set()
    for report in reports:
        for f in report.get("findings", []):
            sig = (
                report.get("target", {}).get("value", ""),
                f.get("rule_id", ""),
                ",".join(f.get("sc", [])),
            )
            current_sigs.add(sig)

    baseline_sigs = set()
    for report in baseline_reports:
        for f in report.get("findings", []):
            sig = (
                report.get("target", {}).get("value", ""),
                f.get("rule_id", ""),
                ",".join(f.get("sc", [])),
            )
            baseline_sigs.add(sig)

    new_findings = current_sigs - baseline_sigs
    resolved = baseline_sigs - current_sigs
    persistent = current_sigs & baseline_sigs

    return {
        "new_count": len(new_findings),
        "resolved_count": len(resolved),
        "persistent_count": len(persistent),
        "current_total": len(current_sigs),
        "baseline_total": len(baseline_sigs),
    }


def _resolve_standard(
    reports: list[dict[str, Any]],
) -> tuple[str, str]:
    """Determine the common WCAG version and conformance level across reports."""
    versions = {r.get("standard", {}).get("wcag_version", "2.1") for r in reports}
    levels = {r.get("standard", {}).get("conformance_level", "AA") for r in reports}
    version = versions.pop() if len(versions) == 1 else "2.1"
    level = levels.pop() if len(levels) == 1 else "AA"
    return version, level


def build_aggregate_report(
    reports: list[dict[str, Any]],
    *,
    wcag_version: str | None = None,
    conformance_level: str | None = None,
    baseline_reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the complete aggregate report from multiple single-target reports.

    Returns a dict matching the structure defined in 20260328_report_todo.md § D.
    """
    resolved_version, resolved_level = _resolve_standard(reports)
    version = wcag_version or resolved_version
    level = conformance_level or resolved_level

    all_findings = _collect_all_findings(reports)
    scope = _build_scope(reports, all_findings, version, level)
    severity = _build_severity(all_findings)
    fixability = _build_fixability(all_findings)
    targets = _build_targets(reports)
    wcag_principles = _build_wcag_principles(all_findings)
    top_rules = _build_top_rules(all_findings)
    remediation = _build_remediation_lifecycle(reports, all_findings)
    auto_fix = _build_auto_fix_opportunity(all_findings, reports)
    baseline_diff = _build_baseline_diff(reports, baseline_reports)

    return {
        "report_type": "aggregate",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "standard": {
            "wcag_version": version,
            "conformance_level": level,
        },
        "scope": scope,
        "severity": severity,
        "fixability": fixability,
        "wcag_principles": wcag_principles,
        "top_rules": top_rules,
        "targets": targets,
        "remediation_lifecycle": remediation,
        "baseline_diff": baseline_diff,
        "auto_fix_opportunity": auto_fix,
    }


def write_aggregate_json(report: dict[str, Any], output_path: Path) -> None:
    """Write the aggregate report as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
