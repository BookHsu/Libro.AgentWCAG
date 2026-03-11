#!/usr/bin/env python3
"""Core vendor-neutral helpers for the WCAG web skill."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from remediation_library import get_strategy

DEFAULT_WCAG_VERSION = "2.1"
DEFAULT_LEVEL = "AA"
DEFAULT_LANGUAGE = "zh-TW"
DEFAULT_EXECUTION_MODE = "suggest-only"
WORKFLOW_VERSION = "1.0.0"

VALID_VERSIONS = {"2.0", "2.1", "2.2"}
VALID_LEVELS = {"A", "AA", "AAA"}
VALID_TASK_MODES = {"create", "modify"}
VALID_EXECUTION_MODES = {"audit-only", "suggest-only", "apply-fixes"}

MARKDOWN_COLUMNS = {
    "en": [
        "Issue ID",
        "Source",
        "WCAG Version",
        "Level",
        "SC",
        "Current",
        "Fix",
        "Changed Target",
        "Citation",
        "Status",
    ],
    "zh-TW": [
        "問題編號",
        "來源",
        "WCAG 版本",
        "等級",
        "SC",
        "現況",
        "修正建議",
        "變更目標",
        "引用",
        "狀態",
    ],
}

MARKDOWN_LABELS = {
    "en": {
        "execution_mode": "Execution mode",
        "files_modified": "Files modified by core workflow",
        "modification_owner": "Modification executed by",
        "task_mode": "Task mode",
        "yes": "yes",
        "no": "no",
    },
    "zh-TW": {
        "execution_mode": "執行模式",
        "files_modified": "核心流程是否已修改檔案",
        "modification_owner": "實際修改執行者",
        "task_mode": "任務模式",
        "yes": "是",
        "no": "否",
    },
}

WCAG_UNDERSTANDING_PATHS = {
    "1.1.1": "non-text-content",
    "1.2.2": "captions-prerecorded",
    "1.2.3": "audio-description-or-media-alternative-prerecorded",
    "1.2.5": "audio-description-prerecorded",
    "1.3.1": "info-and-relationships",
    "1.3.2": "meaningful-sequence",
    "1.3.3": "sensory-characteristics",
    "1.4.3": "contrast-minimum",
    "1.4.4": "resize-text",
    "1.4.10": "reflow",
    "1.4.11": "non-text-contrast",
    "1.4.12": "text-spacing",
    "1.4.13": "content-on-hover-or-focus",
    "2.1.1": "keyboard",
    "2.1.2": "no-keyboard-trap",
    "2.2.1": "timing-adjustable",
    "2.2.2": "pause-stop-hide",
    "2.3.1": "three-flashes-or-below-threshold",
    "2.4.1": "bypass-blocks",
    "2.4.2": "page-titled",
    "2.4.3": "focus-order",
    "2.4.4": "link-purpose-in-context",
    "2.4.6": "headings-and-labels",
    "2.4.7": "focus-visible",
    "2.4.11": "focus-not-obscured-minimum",
    "2.4.12": "focus-not-obscured-enhanced",
    "2.4.13": "focus-appearance",
    "2.5.3": "label-in-name",
    "2.5.7": "dragging-movements",
    "2.5.8": "target-size-minimum",
    "3.1.1": "language-of-page",
    "3.1.2": "language-of-parts",
    "3.2.1": "on-focus",
    "3.2.2": "on-input",
    "3.2.5": "change-on-request",
    "3.2.6": "consistent-help",
    "3.3.1": "error-identification",
    "3.3.2": "labels-or-instructions",
    "3.3.3": "error-suggestion",
    "3.3.4": "error-prevention-legal-financial-data",
    "3.3.7": "redundant-entry",
    "3.3.8": "accessible-authentication-minimum",
    "3.3.9": "accessible-authentication-enhanced",
    "4.1.1": "parsing",
    "4.1.2": "name-role-value",
    "4.1.3": "status-messages",
}

WCAG_22_MANUAL_REVIEW_SC = {
    "2.4.11": "Review whether focused elements remain at least partially visible.",
    "2.4.12": "Review whether focused elements remain fully unobscured in enhanced scenarios.",
    "2.4.13": "Review whether focus appearance meets WCAG 2.2 requirements.",
    "2.5.7": "Review whether dragging interactions have a single-pointer alternative.",
    "2.5.8": "Review whether targets meet minimum target size requirements.",
    "3.2.6": "Review whether help mechanisms remain consistent across pages.",
    "3.3.7": "Review whether redundant-entry protections are provided where needed.",
    "3.3.8": "Review accessible authentication without cognitive function tests.",
    "3.3.9": "Review enhanced accessible authentication support.",
}

AXE_RULE_TO_SC = {
    "image-alt": ["1.1.1"],
    "input-image-alt": ["1.1.1"],
    "object-alt": ["1.1.1"],
    "area-alt": ["1.1.1"],
    "svg-img-alt": ["1.1.1"],
    "aria-input-field-name": ["4.1.2", "3.3.2"],
    "aria-meter-name": ["4.1.2"],
    "aria-progressbar-name": ["4.1.2"],
    "aria-toggle-field-name": ["4.1.2"],
    "aria-tooltip-name": ["4.1.2"],
    "aria-command-name": ["4.1.2"],
    "aria-dialog-name": ["4.1.2"],
    "label": ["3.3.2", "1.3.1"],
    "select-name": ["3.3.2", "4.1.2"],
    "form-field-multiple-labels": ["3.3.2"],
    "color-contrast": ["1.4.3"],
    "link-in-text-block": ["1.4.3"],
    "scrollable-region-focusable": ["2.1.1"],
    "accesskeys": ["2.1.1"],
    "aria-required-attr": ["4.1.2"],
    "aria-valid-attr-value": ["4.1.2"],
    "aria-allowed-attr": ["4.1.2"],
    "aria-allowed-role": ["4.1.2"],
    "aria-required-children": ["4.1.2"],
    "aria-required-parent": ["4.1.2"],
    "aria-roles": ["4.1.2"],
    "aria-valid-attr": ["4.1.2"],
    "aria-hidden-focus": ["4.1.2", "2.4.3"],
    "duplicate-id-aria": ["4.1.1", "4.1.2"],
    "button-name": ["4.1.2"],
    "link-name": ["2.4.4", "4.1.2"],
    "empty-heading": ["1.3.1", "2.4.6"],
    "heading-order": ["1.3.1", "2.4.6"],
    "html-has-lang": ["3.1.1"],
    "html-lang-valid": ["3.1.1"],
    "html-xml-lang-mismatch": ["3.1.1"],
    "landmark-banner-is-top-level": ["1.3.1"],
    "landmark-contentinfo-is-top-level": ["1.3.1"],
    "landmark-main-is-top-level": ["1.3.1"],
    "landmark-no-duplicate-banner": ["1.3.1"],
    "landmark-no-duplicate-contentinfo": ["1.3.1"],
    "landmark-no-duplicate-main": ["1.3.1"],
    "landmark-unique": ["1.3.1"],
    "list": ["1.3.1"],
    "listitem": ["1.3.1"],
    "meta-refresh": ["2.2.1", "3.2.5"],
    "meta-viewport": ["1.4.4", "1.4.10"],
    "nested-interactive": ["4.1.2", "2.1.1"],
    "p-as-heading": ["1.3.1", "2.4.6"],
    "presentation-role-conflict": ["4.1.2"],
    "region": ["1.3.1", "2.4.1"],
    "skip-link": ["2.4.1"],
    "tabindex": ["2.4.3"],
    "table-fake-caption": ["1.3.1"],
    "td-has-header": ["1.3.1"],
    "valid-lang": ["3.1.2"],
    "video-caption": ["1.2.2"],
}

LIGHTHOUSE_RULE_TO_SC = {
    "image-alt": ["1.1.1"],
    "label": ["3.3.2", "1.3.1"],
    "color-contrast": ["1.4.3"],
    "button-name": ["4.1.2"],
    "aria-required-attr": ["4.1.2"],
    "aria-allowed-attr": ["4.1.2"],
    "aria-allowed-role": ["4.1.2"],
    "aria-hidden-body": ["1.3.1", "4.1.2"],
    "aria-hidden-focus": ["4.1.2", "2.4.3"],
    "aria-input-field-name": ["4.1.2", "3.3.2"],
    "aria-meter-name": ["4.1.2"],
    "aria-progressbar-name": ["4.1.2"],
    "aria-required-children": ["4.1.2"],
    "aria-required-parent": ["4.1.2"],
    "aria-roles": ["4.1.2"],
    "aria-toggle-field-name": ["4.1.2"],
    "aria-tooltip-name": ["4.1.2"],
    "aria-valid-attr": ["4.1.2"],
    "aria-valid-attr-value": ["4.1.2"],
    "bypass": ["2.4.1"],
    "definition-list": ["1.3.1"],
    "dlitem": ["1.3.1"],
    "document-title": ["2.4.2"],
    "duplicate-id-aria": ["4.1.1", "4.1.2"],
    "form-field-multiple-labels": ["3.3.2"],
    "heading-order": ["1.3.1", "2.4.6"],
    "html-has-lang": ["3.1.1"],
    "html-lang-valid": ["3.1.1"],
    "input-image-alt": ["1.1.1"],
    "link-name": ["2.4.4", "4.1.2"],
    "list": ["1.3.1"],
    "listitem": ["1.3.1"],
    "meta-refresh": ["2.2.2", "3.2.5"],
    "meta-viewport": ["1.4.4", "1.4.10"],
    "object-alt": ["1.1.1"],
    "select-name": ["3.3.2", "4.1.2"],
    "tabindex": ["2.4.3"],
    "td-headers-attr": ["1.3.1"],
    "th-has-data-cells": ["1.3.1"],
    "valid-lang": ["3.1.2"],
    "video-caption": ["1.2.2"],
}

SEVERITY_ORDER = {"critical": 4, "serious": 3, "moderate": 2, "minor": 1, "info": 0}


@dataclass
class Contract:
    task_mode: str
    execution_mode: str
    wcag_version: str
    conformance_level: str
    target: str
    output_language: str


def build_citation_url(wcag_version: str, sc: str) -> str:
    slug = WCAG_UNDERSTANDING_PATHS.get(sc)
    if not slug:
        return ""
    normalized_version = wcag_version.replace(".", "")
    return f"https://www.w3.org/WAI/WCAG{normalized_version}/Understanding/{slug}"


def _language_key(output_language: str) -> str:
    return "zh-TW" if output_language.lower().startswith("zh") else "en"


def resolve_contract(raw: dict[str, Any]) -> Contract:
    task_mode = raw.get("task_mode", "modify")
    execution_mode = raw.get("execution_mode", DEFAULT_EXECUTION_MODE)
    wcag_version = raw.get("wcag_version", DEFAULT_WCAG_VERSION)
    conformance_level = raw.get("conformance_level", DEFAULT_LEVEL)
    target = str(raw.get("target", "")).strip()
    output_language = raw.get("output_language", DEFAULT_LANGUAGE)

    if task_mode not in VALID_TASK_MODES:
        raise ValueError(f"Unsupported task_mode: {task_mode}")
    if execution_mode not in VALID_EXECUTION_MODES:
        raise ValueError(f"Unsupported execution_mode: {execution_mode}")
    if wcag_version not in VALID_VERSIONS:
        raise ValueError(f"Unsupported wcag_version: {wcag_version}")
    if conformance_level not in VALID_LEVELS:
        raise ValueError(f"Unsupported conformance_level: {conformance_level}")
    if not target:
        raise ValueError("target is required")

    return Contract(
        task_mode=task_mode,
        execution_mode=execution_mode,
        wcag_version=wcag_version,
        conformance_level=conformance_level,
        target=target,
        output_language=output_language,
    )


def load_json_file(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    payload = Path(path)
    if not payload.exists():
        return None
    with payload.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _map_axe_to_findings(axe_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not axe_data:
        return []
    findings: list[dict[str, Any]] = []
    violations = axe_data.get("violations", [])
    for violation in violations:
        rule_id = violation.get("id", "axe-unknown")
        nodes = violation.get("nodes", [])
        current = violation.get("description") or violation.get("help") or rule_id
        changed_target = ", ".join(
            "/".join(node.get("target", []))
            for node in nodes
            if isinstance(node.get("target"), list) and node.get("target")
        )
        if not changed_target:
            changed_target = "unknown"
        findings.append(
            {
                "source": "axe",
                "sources": ["axe"],
                "rule_id": rule_id,
                "severity": violation.get("impact", "info"),
                "sc": AXE_RULE_TO_SC.get(rule_id, []),
                "current": current,
                "changed_target": changed_target,
                "status": "open",
            }
        )
    return findings


def _map_lighthouse_severity(score: float | int | None) -> str:
    if score is None:
        return "info"
    numeric_score = float(score)
    if numeric_score <= 0.15:
        return "critical"
    if numeric_score <= 0.5:
        return "serious"
    if numeric_score <= 0.85:
        return "moderate"
    return "minor"


def _map_lighthouse_to_findings(
    lighthouse_data: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not lighthouse_data:
        return []
    findings: list[dict[str, Any]] = []
    audits = lighthouse_data.get("audits", {})
    for audit_key, audit in audits.items():
        score = audit.get("score")
        if score is None or score == 1:
            continue
        score_mode = audit.get("scoreDisplayMode", "")
        if score_mode in {"informative", "notApplicable"}:
            continue
        changed_target = "unknown"
        details = audit.get("details", {})
        items = details.get("items", []) if isinstance(details, dict) else []
        if items and isinstance(items[0], dict):
            node = items[0].get("node", {})
            if isinstance(node, dict):
                changed_target = node.get("selector", "unknown")
        findings.append(
            {
                "source": "lighthouse",
                "sources": ["lighthouse"],
                "rule_id": audit_key,
                "severity": _map_lighthouse_severity(score),
                "sc": LIGHTHOUSE_RULE_TO_SC.get(audit_key, []),
                "current": audit.get("title", audit_key),
                "changed_target": changed_target,
                "status": "open",
            }
        )
    return findings


def _manual_fallback_finding(source: str) -> dict[str, Any]:
    return {
        "source": "manual",
        "sources": ["manual"],
        "rule_id": f"{source}-unavailable",
        "severity": "info",
        "sc": [],
        "current": f"{source} scan failed. Run manual review checklist.",
        "changed_target": "manual-review",
        "status": "needs-review",
    }


def _sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda item: SEVERITY_ORDER.get(str(item.get("severity", "info")), 0),
        reverse=True,
    )


def _dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (str(finding.get("rule_id", "")), str(finding.get("changed_target", "")))
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = {
                **finding,
                "sources": sorted(set(finding.get("sources", [finding["source"]]))),
            }
            continue
        existing["sources"] = sorted(
            set(existing.get("sources", [])) | set(finding.get("sources", [finding["source"]]))
        )
        existing["source"] = "+".join(existing["sources"])
        existing["sc"] = sorted(set(existing.get("sc", [])) | set(finding.get("sc", [])))
        if SEVERITY_ORDER.get(finding["severity"], 0) > SEVERITY_ORDER.get(existing["severity"], 0):
            existing["severity"] = finding["severity"]
        if len(str(finding.get("current", ""))) > len(str(existing.get("current", ""))):
            existing["current"] = finding["current"]
        if existing["status"] != "needs-review" and finding.get("status") == "needs-review":
            existing["status"] = "needs-review"
    return list(deduped.values())


def _manual_review_findings_for_wcag_22(contract: Contract, existing_sc: set[str]) -> list[dict[str, Any]]:
    if contract.wcag_version != "2.2":
        return []
    findings: list[dict[str, Any]] = []
    for sc, description in WCAG_22_MANUAL_REVIEW_SC.items():
        if sc in existing_sc:
            continue
        findings.append(
            {
                "source": "manual",
                "sources": ["manual"],
                "rule_id": f"wcag22-manual-{sc}",
                "severity": "info",
                "sc": [sc],
                "current": description,
                "changed_target": "manual-review",
                "status": "needs-review",
            }
        )
    return findings


def normalize_report(
    contract: Contract,
    axe_data: dict[str, Any] | None,
    lighthouse_data: dict[str, Any] | None,
    axe_error: str | None = None,
    lighthouse_error: str | None = None,
    axe_skipped: bool = False,
    lighthouse_skipped: bool = False,
) -> dict[str, Any]:
    findings = _map_axe_to_findings(axe_data) + _map_lighthouse_to_findings(lighthouse_data)
    notes: list[str] = []
    tools = {
        "axe": "skipped" if axe_skipped else ("ok" if axe_data and not axe_error else "error"),
        "lighthouse": (
            "skipped"
            if lighthouse_skipped
            else ("ok" if lighthouse_data and not lighthouse_error else "error")
        ),
    }

    if tools["axe"] == "error":
        notes.append(f"axe failed: {axe_error or 'unknown error'}")
        findings.append(_manual_fallback_finding("axe"))
    if tools["lighthouse"] == "error":
        notes.append(f"lighthouse failed: {lighthouse_error or 'unknown error'}")
        findings.append(_manual_fallback_finding("lighthouse"))

    deduped_findings = _dedupe_findings(findings)
    known_sc = {sc for finding in deduped_findings for sc in finding.get("sc", [])}
    deduped_findings.extend(_manual_review_findings_for_wcag_22(contract, known_sc))
    deduped_findings = _sort_findings(deduped_findings)

    normalized_findings: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    change_summary: list[dict[str, Any]] = []

    for index, raw in enumerate(deduped_findings, start=1):
        issue_id = f"ISSUE-{index:03d}"
        fix_id = f"FIX-{index:03d}"
        sc_values = raw.get("sc") or []
        strategy = get_strategy(raw["rule_id"])
        normalized_findings.append(
            {
                "id": issue_id,
                "source": raw["source"],
                "sources": raw.get("sources", [raw["source"]]),
                "rule_id": raw["rule_id"],
                "severity": raw["severity"],
                "confidence": strategy["confidence"],
                "sc": sc_values,
                "current": raw["current"],
                "changed_target": raw["changed_target"],
                "status": raw["status"],
            }
        )
        fixes.append(
            {
                "id": fix_id,
                "finding_id": issue_id,
                "description": strategy["summary"],
                "changed_target": raw["changed_target"],
                "status": "verified" if raw["status"] == "fixed" else "planned",
                "remediation_priority": strategy["priority"],
                "confidence": strategy["confidence"],
                "auto_fix_supported": strategy["auto_fix_supported"],
                "framework_hints": strategy["framework_hints"],
            }
        )
        change_summary.append(
            {
                "finding_id": issue_id,
                "rule_id": raw["rule_id"],
                "changed_target": raw["changed_target"],
                "recommended_action": strategy["summary"],
                "remediation_priority": strategy["priority"],
            }
        )
        for sc in sc_values:
            citation = build_citation_url(contract.wcag_version, sc)
            if citation:
                citations.append({"finding_id": issue_id, "sc": sc, "url": citation})

    summary = {
        "total_findings": len(normalized_findings),
        "fixed_findings": sum(1 for item in normalized_findings if item["status"] == "fixed"),
        "needs_manual_review": sum(
            1 for item in normalized_findings if item["status"] == "needs-review"
        ),
        "change_summary": change_summary,
    }

    return {
        "run_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "workflow_version": WORKFLOW_VERSION,
            "execution_mode": contract.execution_mode,
            "output_language": contract.output_language,
            "files_modified": False,
            "modification_owner": "agent-or-adapter",
            "tools": tools,
            "notes": notes,
        },
        "target": {
            "value": contract.target,
            "task_mode": contract.task_mode,
        },
        "standard": {
            "wcag_version": contract.wcag_version,
            "conformance_level": contract.conformance_level,
        },
        "findings": normalized_findings,
        "fixes": fixes,
        "citations": citations,
        "summary": summary,
    }


def to_markdown_table(report: dict[str, Any]) -> str:
    language_key = _language_key(report["run_meta"].get("output_language", DEFAULT_LANGUAGE))
    labels = MARKDOWN_LABELS[language_key]
    execution_mode = report["run_meta"]["execution_mode"]
    modified_text = labels["yes"] if report["run_meta"].get("files_modified") else labels["no"]
    summary_lines = [
        f"{labels['execution_mode']}: {execution_mode}",
        f"{labels['task_mode']}: {report['target']['task_mode']}",
        f"{labels['files_modified']}: {modified_text}",
        f"{labels['modification_owner']}: {report['run_meta'].get('modification_owner', 'agent-or-adapter')}",
        "",
    ]
    header_columns = MARKDOWN_COLUMNS[language_key]
    header = "| " + " | ".join(header_columns) + " |"
    separator = "| " + " | ".join(["---"] * len(header_columns)) + " |"
    lines = summary_lines + [header, separator]
    version = report["standard"]["wcag_version"]
    level = report["standard"]["conformance_level"]
    fixes_by_finding = {fix["finding_id"]: fix for fix in report.get("fixes", [])}
    citations_by_finding: dict[str, list[str]] = {}
    for row in report.get("citations", []):
        citations_by_finding.setdefault(row["finding_id"], []).append(f"{row['sc']}: {row['url']}")

    for finding in report.get("findings", []):
        finding_id = finding["id"]
        fix = fixes_by_finding.get(finding_id, {})
        citation = " ; ".join(citations_by_finding.get(finding_id, []))
        lines.append(
            "| "
            + " | ".join(
                [
                    finding_id,
                    finding.get("source", ""),
                    version,
                    level,
                    ",".join(finding.get("sc", [])),
                    _escape_pipe(finding.get("current", "")),
                    _escape_pipe(fix.get("description", "")),
                    _escape_pipe(finding.get("changed_target", "")),
                    _escape_pipe(citation),
                    finding.get("status", ""),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _escape_pipe(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_report_files(report: dict[str, Any], json_path: str, markdown_path: str) -> None:
    json_target = Path(json_path)
    markdown_target = Path(markdown_path)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    markdown_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_target.write_text(to_markdown_table(report), encoding="utf-8")
