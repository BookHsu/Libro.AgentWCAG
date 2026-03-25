#!/usr/bin/env python3
"""Normalize raw scanner payloads into the Libro.AgentWCAG contract."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[2] / "skills" / "libro-wcag" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from wcag_workflow import normalize_report as build_report
from wcag_workflow import resolve_contract, to_markdown_table


def normalize_wcag_payload(
    *,
    target: str,
    raw_report: dict[str, Any],
    task_mode: str = "modify",
    execution_mode: str = "suggest-only",
    wcag_version: str = "2.1",
    conformance_level: str = "AA",
    output_language: str = "zh-TW",
) -> dict[str, object]:
    contract = resolve_contract(
        {
            "task_mode": task_mode,
            "execution_mode": execution_mode,
            "wcag_version": wcag_version,
            "conformance_level": conformance_level,
            "target": target,
            "output_language": output_language,
        }
    )
    report = build_report(
        contract=contract,
        axe_data=raw_report.get("axe_data"),
        lighthouse_data=raw_report.get("lighthouse_data"),
        axe_error=raw_report.get("axe_error"),
        lighthouse_error=raw_report.get("lighthouse_error"),
        axe_skipped=bool(raw_report.get("axe_skipped", False)),
        lighthouse_skipped=bool(raw_report.get("lighthouse_skipped", False)),
    )
    return {
        "report": report,
        "markdown": to_markdown_table(report),
    }


__all__ = ["normalize_wcag_payload"]
