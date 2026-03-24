#!/usr/bin/env python3
"""Run the existing WCAG audit CLI as an MCP tool wrapper."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = REPO_ROOT / "skills" / "libro-wcag" / "scripts" / "run_accessibility_audit.py"


def build_audit_command(
    *,
    target: str,
    output_dir: Path,
    task_mode: str = "modify",
    execution_mode: str = "audit-only",
    wcag_version: str = "2.1",
    conformance_level: str = "AA",
    output_language: str = "zh-TW",
    timeout: int = 120,
) -> list[str]:
    return [
        sys.executable,
        str(AUDIT_SCRIPT),
        "--task-mode",
        task_mode,
        "--execution-mode",
        execution_mode,
        "--wcag-version",
        wcag_version,
        "--conformance-level",
        conformance_level,
        "--target",
        target,
        "--output-language",
        output_language,
        "--output-dir",
        str(output_dir),
        "--timeout",
        str(timeout),
        "--report-format",
        "json",
    ]


def audit_page(
    *,
    target: str,
    task_mode: str = "modify",
    execution_mode: str = "audit-only",
    wcag_version: str = "2.1",
    conformance_level: str = "AA",
    output_language: str = "zh-TW",
    timeout: int = 120,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="libro-wcag-mcp-audit-") as tmp:
        output_dir = Path(tmp) / "out"
        command = build_audit_command(
            target=target,
            output_dir=output_dir,
            task_mode=task_mode,
            execution_mode=execution_mode,
            wcag_version=wcag_version,
            conformance_level=conformance_level,
            output_language=output_language,
            timeout=timeout,
        )
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stdout + completed.stderr).strip() or "audit command failed")
        report_path = output_dir / "wcag-report.json"
        markdown_path = output_dir / "wcag-report.md"
        return {
            "report": json.loads(report_path.read_text(encoding="utf-8")),
            "markdown": markdown_path.read_text(encoding="utf-8"),
            "stdout": completed.stdout.strip(),
        }


__all__ = ["audit_page", "build_audit_command"]
