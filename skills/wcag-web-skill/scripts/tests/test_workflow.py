#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wcag_workflow import normalize_report, resolve_contract, to_markdown_table, write_report_files


class WorkflowTests(unittest.TestCase):
    def test_default_standard_fallback(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        self.assertEqual(contract.wcag_version, "2.1")
        self.assertEqual(contract.conformance_level, "AA")
        self.assertEqual(contract.output_language, "zh-TW")

    def test_standard_variants_are_accepted(self) -> None:
        for version, level in [("2.1", "AA"), ("2.2", "AAA"), ("2.0", "A")]:
            contract = resolve_contract(
                {
                    "task_mode": "modify",
                    "wcag_version": version,
                    "conformance_level": level,
                    "target": "https://example.com",
                }
            )
            self.assertEqual(contract.wcag_version, version)
            self.assertEqual(contract.conformance_level, level)

    def test_markdown_json_alignment(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        axe_data = {
            "violations": [
                {
                    "id": "image-alt",
                    "impact": "serious",
                    "description": "Images must have alternate text",
                    "nodes": [{"target": ["img.hero"]}],
                }
            ]
        }
        lighthouse_data = {
            "audits": {
                "label": {
                    "score": 0,
                    "scoreDisplayMode": "binary",
                    "title": "Form elements have labels",
                    "details": {"items": [{"node": {"selector": "input#email"}}]},
                }
            }
        }
        report = normalize_report(contract, axe_data, lighthouse_data)
        markdown = to_markdown_table(report)
        for finding in report["findings"]:
            self.assertIn(finding["id"], markdown)

    def test_citation_presence_for_major_finding(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        axe_data = {
            "violations": [
                {
                    "id": "color-contrast",
                    "impact": "critical",
                    "description": "Elements must have sufficient color contrast",
                    "nodes": [{"target": [".low-contrast"]}],
                }
            ]
        }
        report = normalize_report(contract, axe_data, None, lighthouse_error="missing")
        citation_urls = [item["url"] for item in report["citations"]]
        self.assertTrue(any("w3.org" in url for url in citation_urls))

    def test_manual_fallback_when_tool_fails(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(contract, None, {"audits": {}}, axe_error="command failed")
        self.assertEqual(report["run_meta"]["tools"]["axe"], "error")
        self.assertTrue(any(item["status"] == "needs-review" for item in report["findings"]))

    def test_write_report_files(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "report.json"
            md_path = Path(tmp) / "report.md"
            write_report_files(report, str(json_path), str(md_path))
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("summary", payload)


if __name__ == "__main__":
    unittest.main()

