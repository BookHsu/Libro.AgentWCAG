#!/usr/bin/env python3
"""Run axe and Lighthouse scans, then emit normalized WCAG outputs."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from wcag_workflow import normalize_report, resolve_contract, write_report_files


def _run_command(command: list[str]) -> tuple[bool, str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode == 0:
        return True, completed.stdout
    error = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
    return False, error


def _try_run_axe(target: str, output_dir: Path) -> tuple[dict[str, Any] | None, str | None]:
    axe_json = output_dir / "axe.raw.json"
    command = ["npx", "@axe-core/cli", target, "--save", str(axe_json)]
    ok, result = _run_command(command)
    if not ok:
        return None, result
    if not axe_json.exists():
        return None, "axe did not generate output json"
    with axe_json.open("r", encoding="utf-8") as handle:
        return json.load(handle), None


def _try_run_lighthouse(target: str, output_dir: Path) -> tuple[dict[str, Any] | None, str | None]:
    lighthouse_json = output_dir / "lighthouse.raw.json"
    command = [
        "npx",
        "lighthouse",
        target,
        "--only-categories=accessibility",
        "--output=json",
        f"--output-path={lighthouse_json}",
        "--chrome-flags=--headless=new",
    ]
    ok, result = _run_command(command)
    if not ok:
        return None, result
    if not lighthouse_json.exists():
        return None, "lighthouse did not generate output json"
    with lighthouse_json.open("r", encoding="utf-8") as handle:
        return json.load(handle), None


def _resolve_target_for_scanners(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https", "file"}:
        return target
    local_path = Path(target)
    if local_path.exists():
        return local_path.resolve().as_uri()
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run WCAG audit with axe+Lighthouse.")
    parser.add_argument("--task-mode", default="modify", choices=["create", "modify"])
    parser.add_argument("--wcag-version", default="2.1", choices=["2.0", "2.1", "2.2"])
    parser.add_argument("--conformance-level", default="AA", choices=["A", "AA", "AAA"])
    parser.add_argument("--target", required=True)
    parser.add_argument("--output-language", default="zh-TW")
    parser.add_argument("--output-dir", default="out")
    parser.add_argument("--skip-axe", action="store_true")
    parser.add_argument("--skip-lighthouse", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    contract = resolve_contract(
        {
            "task_mode": args.task_mode,
            "wcag_version": args.wcag_version,
            "conformance_level": args.conformance_level,
            "target": args.target,
            "output_language": args.output_language,
        }
    )
    scanner_target = _resolve_target_for_scanners(contract.target)

    axe_data = None
    axe_error = None
    if not args.skip_axe:
        axe_data, axe_error = _try_run_axe(scanner_target, output_dir)

    lighthouse_data = None
    lighthouse_error = None
    if not args.skip_lighthouse:
        lighthouse_data, lighthouse_error = _try_run_lighthouse(scanner_target, output_dir)

    report = normalize_report(
        contract=contract,
        axe_data=axe_data,
        lighthouse_data=lighthouse_data,
        axe_error=axe_error,
        lighthouse_error=lighthouse_error,
        axe_skipped=args.skip_axe,
        lighthouse_skipped=args.skip_lighthouse,
    )

    output_json = output_dir / "wcag-report.json"
    output_md = output_dir / "wcag-report.md"
    write_report_files(report, str(output_json), str(output_md))

    print(f"Saved JSON report: {output_json}")
    print(f"Saved Markdown table: {output_md}")
    if report["run_meta"]["notes"]:
        print("Notes:")
        for note in report["run_meta"]["notes"]:
            print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
