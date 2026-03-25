#!/usr/bin/env python3
"""Generate remediation suggestions from normalized findings."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[2] / "skills" / "libro-wcag" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from remediation_library import get_strategy
from wcag_workflow import build_citation_url, resolve_contract


def suggest_from_findings(
    *,
    target: str,
    findings: list[dict[str, Any]],
    task_mode: str = "modify",
    wcag_version: str = "2.1",
    conformance_level: str = "AA",
    output_language: str = "zh-TW",
) -> dict[str, object]:
    contract = resolve_contract(
        {
            "task_mode": task_mode,
            "execution_mode": "suggest-only",
            "wcag_version": wcag_version,
            "conformance_level": conformance_level,
            "target": target,
            "output_language": output_language,
        }
    )
    suggestions: list[dict[str, object]] = []
    for finding in findings:
        rule_id = str(finding.get("rule_id", "unknown"))
        strategy = get_strategy(rule_id)
        citations = [
            {"sc": sc, "url": build_citation_url(contract.wcag_version, sc)}
            for sc in finding.get("sc", [])
            if build_citation_url(contract.wcag_version, sc)
        ]
        suggestions.append(
            {
                "finding_id": finding.get("id"),
                "rule_id": rule_id,
                "summary": strategy["summary"],
                "priority": strategy["priority"],
                "confidence": strategy["confidence"],
                "auto_fix_supported": strategy["auto_fix_supported"],
                "assisted_steps": strategy["assisted_steps"],
                "verification_rules": strategy["verification_rules"],
                "framework_hints": strategy["framework_hints"],
                "citations": citations,
            }
        )
    return {
        "target": contract.target,
        "standard": {
            "wcag_version": contract.wcag_version,
            "conformance_level": contract.conformance_level,
        },
        "execution_mode": "suggest-only",
        "suggestions": suggestions,
    }


__all__ = ["suggest_from_findings"]
