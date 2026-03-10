#!/usr/bin/env python3
"""Normalize raw axe/Lighthouse outputs into the skill contract outputs."""

from __future__ import annotations

import argparse

from wcag_workflow import (
    load_json_file,
    normalize_report,
    resolve_contract,
    write_report_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize WCAG scanner outputs.")
    parser.add_argument("--task-mode", default="modify", choices=["create", "modify"])
    parser.add_argument("--wcag-version", default="2.1", choices=["2.0", "2.1", "2.2"])
    parser.add_argument("--conformance-level", default="AA", choices=["A", "AA", "AAA"])
    parser.add_argument("--target", required=True)
    parser.add_argument("--output-language", default="zh-TW")
    parser.add_argument("--axe-json")
    parser.add_argument("--lighthouse-json")
    parser.add_argument("--axe-error")
    parser.add_argument("--lighthouse-error")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = resolve_contract(
        {
            "task_mode": args.task_mode,
            "wcag_version": args.wcag_version,
            "conformance_level": args.conformance_level,
            "target": args.target,
            "output_language": args.output_language,
        }
    )

    report = normalize_report(
        contract=contract,
        axe_data=load_json_file(args.axe_json),
        lighthouse_data=load_json_file(args.lighthouse_json),
        axe_error=args.axe_error,
        lighthouse_error=args.lighthouse_error,
    )
    write_report_files(report, args.output_json, args.output_md)
    print(f"Saved JSON report: {args.output_json}")
    print(f"Saved Markdown table: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

