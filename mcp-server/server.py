#!/usr/bin/env python3
"""Libro.AgentWCAG MCP server (stdio transport)."""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parent / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from audit_page import audit_page
from normalize_report import normalize_wcag_payload
from suggest_fixes import suggest_from_findings

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - import guard for runtime environments
    raise SystemExit(
        "Install MCP dependencies first: python -m pip install -r mcp-server/requirements.txt"
    ) from exc


mcp = FastMCP("libro-wcag")


@mcp.tool()
def libro_wcag_audit(
    target: str,
    task_mode: str = "modify",
    execution_mode: str = "audit-only",
    wcag_version: str = "2.1",
    conformance_level: str = "AA",
    output_language: str = "zh-TW",
    timeout: int = 120,
) -> dict[str, object]:
    return audit_page(
        target=target,
        task_mode=task_mode,
        execution_mode=execution_mode,
        wcag_version=wcag_version,
        conformance_level=conformance_level,
        output_language=output_language,
        timeout=timeout,
    )


@mcp.tool()
def libro_wcag_suggest(
    target: str,
    findings: list[dict[str, object]],
    task_mode: str = "modify",
    wcag_version: str = "2.1",
    conformance_level: str = "AA",
    output_language: str = "zh-TW",
) -> dict[str, object]:
    return suggest_from_findings(
        target=target,
        findings=findings,
        task_mode=task_mode,
        wcag_version=wcag_version,
        conformance_level=conformance_level,
        output_language=output_language,
    )


@mcp.tool()
def libro_wcag_normalize(
    target: str,
    raw_report: dict[str, object],
    task_mode: str = "modify",
    execution_mode: str = "suggest-only",
    wcag_version: str = "2.1",
    conformance_level: str = "AA",
    output_language: str = "zh-TW",
) -> dict[str, object]:
    return normalize_wcag_payload(
        target=target,
        raw_report=raw_report,
        task_mode=task_mode,
        execution_mode=execution_mode,
        wcag_version=wcag_version,
        conformance_level=conformance_level,
        output_language=output_language,
    )


if __name__ == "__main__":  # pragma: no cover - exercised by manual MCP smoke
    mcp.run()
