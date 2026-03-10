#!/usr/bin/env python3
"""Core vendor-neutral helpers for the WCAG web skill."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_WCAG_VERSION = "2.1"
DEFAULT_LEVEL = "AA"
DEFAULT_LANGUAGE = "zh-TW"
WORKFLOW_VERSION = "1.0.0"

VALID_VERSIONS = {"2.0", "2.1", "2.2"}
VALID_LEVELS = {"A", "AA", "AAA"}
VALID_TASK_MODES = {"create", "modify"}

MARKDOWN_COLUMNS = [
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
]

SC_CITATIONS = {
    "1.1.1": "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content",
    "1.3.1": "https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships",
    "1.4.3": "https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum",
    "2.1.1": "https://www.w3.org/WAI/WCAG22/Understanding/keyboard",
    "2.4.7": "https://www.w3.org/WAI/WCAG22/Understanding/focus-visible",
    "3.3.2": "https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions",
    "4.1.2": "https://www.w3.org/WAI/WCAG22/Understanding/name-role-value",
}

AXE_RULE_TO_SC = {
    "image-alt": ["1.1.1"],
    "label": ["3.3.2", "1.3.1"],
    "color-contrast": ["1.4.3"],
    "aria-required-attr": ["4.1.2"],
    "aria-valid-attr-value": ["4.1.2"],
    "button-name": ["4.1.2"],
}

LIGHTHOUSE_RULE_TO_SC = {
    "image-alt": ["1.1.1"],
    "label": ["3.3.2", "1.3.1"],
    "color-contrast": ["1.4.3"],
    "button-name": ["4.1.2"],
    "aria-required-attr": ["4.1.2"],
}

SEVERITY_ORDER = {"critical": 4, "serious": 3, "moderate": 2, "minor": 1, "info": 0}


@dataclass
class Contract:
    task_mode: str
    wcag_version: str
    conformance_level: str
    target: str
    output_language: str


def resolve_contract(raw: dict[str, Any]) -> Contract:
    task_mode = raw.get("task_mode", "modify")
    wcag_version = raw.get("wcag_version", DEFAULT_WCAG_VERSION)
    conformance_level = raw.get("conformance_level", DEFAULT_LEVEL)
    target = str(raw.get("target", "")).strip()
    output_language = raw.get("output_language", DEFAULT_LANGUAGE)

    if task_mode not in VALID_TASK_MODES:
        raise ValueError(f"Unsupported task_mode: {task_mode}")
    if wcag_version not in VALID_VERSIONS:
        raise ValueError(f"Unsupported wcag_version: {wcag_version}")
    if conformance_level not in VALID_LEVELS:
        raise ValueError(f"Unsupported conformance_level: {conformance_level}")
    if not target:
        raise ValueError("target is required")

    return Contract(
        task_mode=task_mode,
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
                "rule_id": rule_id,
                "severity": violation.get("impact", "info"),
                "sc": AXE_RULE_TO_SC.get(rule_id, []),
                "current": current,
                "changed_target": changed_target,
                "status": "open",
            }
        )
    return findings


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
                "rule_id": audit_key,
                "severity": "serious" if score == 0 else "moderate",
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


def normalize_report(
    contract: Contract,
    axe_data: dict[str, Any] | None,
    lighthouse_data: dict[str, Any] | None,
    axe_error: str | None = None,
    lighthouse_error: str | None = None,
) -> dict[str, Any]:
    findings = _map_axe_to_findings(axe_data) + _map_lighthouse_to_findings(lighthouse_data)
    notes: list[str] = []
    tools = {
        "axe": "ok" if axe_data and not axe_error else "error",
        "lighthouse": "ok" if lighthouse_data and not lighthouse_error else "error",
    }

    if tools["axe"] == "error":
        notes.append(f"axe failed: {axe_error or 'unknown error'}")
        findings.append(_manual_fallback_finding("axe"))
    if tools["lighthouse"] == "error":
        notes.append(f"lighthouse failed: {lighthouse_error or 'unknown error'}")
        findings.append(_manual_fallback_finding("lighthouse"))

    findings = _sort_findings(findings)
    normalized_findings: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []

    for index, raw in enumerate(findings, start=1):
        issue_id = f"ISSUE-{index:03d}"
        fix_id = f"FIX-{index:03d}"
        sc_values = raw.get("sc") or []
        first_sc = sc_values[0] if sc_values else ""
        citation = SC_CITATIONS.get(first_sc, "")
        normalized_findings.append(
            {
                "id": issue_id,
                "source": raw["source"],
                "severity": raw["severity"],
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
                "description": f"Remediate {raw['rule_id']} issue.",
                "changed_target": raw["changed_target"],
                "status": "planned" if raw["status"] == "open" else "verified",
            }
        )
        if first_sc and citation:
            citations.append({"finding_id": issue_id, "sc": first_sc, "url": citation})

    summary = {
        "total_findings": len(normalized_findings),
        "fixed_findings": sum(1 for item in normalized_findings if item["status"] == "fixed"),
        "needs_manual_review": sum(
            1 for item in normalized_findings if item["status"] == "needs-review"
        ),
    }

    return {
        "run_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "workflow_version": WORKFLOW_VERSION,
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
    header = "| " + " | ".join(MARKDOWN_COLUMNS) + " |"
    separator = "| " + " | ".join(["---"] * len(MARKDOWN_COLUMNS)) + " |"
    lines = [header, separator]
    version = report["standard"]["wcag_version"]
    level = report["standard"]["conformance_level"]
    fixes_by_finding = {fix["finding_id"]: fix for fix in report.get("fixes", [])}
    citations_by_finding = {row["finding_id"]: row["url"] for row in report.get("citations", [])}

    for finding in report.get("findings", []):
        finding_id = finding["id"]
        fix = fixes_by_finding.get(finding_id, {})
        citation = citations_by_finding.get(finding_id, "")
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
                    citation,
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

