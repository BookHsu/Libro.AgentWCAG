#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from wcag_workflow import (
    AXE_RULE_TO_SC,
    LIGHTHOUSE_RULE_TO_SC,
    _escape_pipe,
    build_citation_url,
    normalize_report,
    resolve_contract,
    to_markdown_table,
    write_report_files,
)


class WorkflowTests(unittest.TestCase):
    def test_default_standard_fallback(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        self.assertEqual(contract.execution_mode, "suggest-only")
        self.assertEqual(contract.wcag_version, "2.1")
        self.assertEqual(contract.conformance_level, "AA")
        self.assertEqual(contract.output_language, "zh-TW")

    def test_standard_variants_are_accepted(self) -> None:
        for version, level in [("2.1", "AA"), ("2.2", "AAA"), ("2.0", "A")]:
            contract = resolve_contract(
                {
                    "task_mode": "modify",
                    "execution_mode": "apply-fixes",
                    "wcag_version": version,
                    "conformance_level": level,
                    "target": "https://example.com",
                }
            )
            self.assertEqual(contract.execution_mode, "apply-fixes")
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
        self.assertIn("執行模式: suggest-only", markdown)
        self.assertIn("核心流程是否已修改檔案: 否", markdown)
        self.assertIn("實際修改執行者: agent-or-adapter", markdown)
        for finding in report["findings"]:
            self.assertIn(finding["id"], markdown)
        self.assertIn("問題編號", markdown)

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
        self.assertTrue(any("/WCAG21/" in url for url in citation_urls))

    def test_manual_fallback_when_tool_fails(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(contract, None, {"audits": {}}, axe_error="command failed")
        self.assertEqual(report["run_meta"]["tools"]["axe"], "error")
        self.assertTrue(any(item["status"] == "needs-review" for item in report["findings"]))

    def test_skipped_tool_is_not_reported_as_error(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(
            contract,
            {"violations": []},
            None,
            lighthouse_skipped=True,
        )
        self.assertEqual(report["run_meta"]["tools"]["lighthouse"], "skipped")
        self.assertFalse(any("lighthouse failed" in note for note in report["run_meta"]["notes"]))

    def test_manual_fallback_fix_remains_planned(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(contract, None, {"audits": {}}, axe_error="command failed")
        manual_fix = next(item for item in report["fixes"] if item["finding_id"] == "ISSUE-001")
        self.assertEqual(manual_fix["status"], "planned")

    def test_citation_url_uses_selected_version(self) -> None:
        self.assertIn("/WCAG20/", build_citation_url("2.0", "1.1.1"))
        self.assertIn("/WCAG21/", build_citation_url("2.1", "1.1.1"))
        self.assertIn("/WCAG22/", build_citation_url("2.2", "1.1.1"))

    def test_expanded_rule_mapping_generates_citation(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        axe_data = {
            "violations": [
                {
                    "id": "link-name",
                    "impact": "serious",
                    "description": "Links must have discernible text",
                    "nodes": [{"target": ["a.cta"]}],
                }
            ]
        }
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        citation_urls = [item["url"] for item in report["citations"]]
        self.assertTrue(any("/WCAG21/" in url for url in citation_urls))

    def test_rule_mappings_cover_broad_common_rules(self) -> None:
        self.assertGreaterEqual(len(AXE_RULE_TO_SC), 30)
        self.assertGreaterEqual(len(LIGHTHOUSE_RULE_TO_SC), 20)

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

    def test_apply_fixes_mode_is_reported(self) -> None:
        contract = resolve_contract(
            {
                "target": "https://example.com",
                "execution_mode": "apply-fixes",
            }
        )
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)
        markdown = to_markdown_table(report)
        self.assertEqual(report["run_meta"]["execution_mode"], "apply-fixes")
        self.assertFalse(report["run_meta"]["files_modified"])
        self.assertIn("執行模式: apply-fixes", markdown)
        self.assertIn("核心流程是否已修改檔案: 否", markdown)

    def test_dedupes_same_rule_and_target_across_sources(self) -> None:
        contract = resolve_contract({"target": "https://example.com", "output_language": "en"})
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
                "image-alt": {
                    "score": 0,
                    "scoreDisplayMode": "binary",
                    "title": "Image elements have [alt] attributes",
                    "details": {"items": [{"node": {"selector": "img.hero"}}]},
                }
            }
        }
        report = normalize_report(contract, axe_data, lighthouse_data)
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(report["findings"][0]["source"], "axe+lighthouse")
        self.assertEqual(report["findings"][0]["sources"], ["axe", "lighthouse"])

    def test_multiple_sc_generate_multiple_citations(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        axe_data = {
            "violations": [
                {
                    "id": "label",
                    "impact": "serious",
                    "description": "Form elements need labels",
                    "nodes": [{"target": ["input#email"]}],
                }
            ]
        }
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        finding_id = report["findings"][0]["id"]
        citations = [item for item in report["citations"] if item["finding_id"] == finding_id]
        self.assertEqual(len(citations), 2)
        self.assertEqual({item["sc"] for item in citations}, {"1.3.1", "3.3.2"})

    def test_fix_metadata_includes_strategy_fields(self) -> None:
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
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        fix = report["fixes"][0]
        self.assertIn("remediation_priority", fix)
        self.assertIn("confidence", fix)
        self.assertIn("auto_fix_supported", fix)
        self.assertIn("framework_hints", fix)
        self.assertTrue(fix["auto_fix_supported"])
    def test_assisted_rule_contains_assisted_steps_and_verification_rules(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        axe_data = {
            "violations": [
                {
                    "id": "skip-link",
                    "impact": "serious",
                    "description": "Page should contain a skip link",
                    "nodes": [{"target": ["body"]}],
                }
            ]
        }
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        fix = report["fixes"][0]
        self.assertEqual(fix["fixability"], "assisted")
        self.assertFalse(fix["auto_fix_supported"])
        self.assertGreaterEqual(len(fix["assisted_steps"]), 2)
        self.assertGreaterEqual(len(fix["verification_rules"]), 2)

    def test_summary_includes_change_summary(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)
        self.assertIn("change_summary", report["summary"])


    def test_report_contract_includes_fixability_verification_and_diff_fields(self) -> None:
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
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        finding = report["findings"][0]
        fix = report["fixes"][0]
        self.assertEqual(finding["fixability"], "auto-fix")
        self.assertEqual(finding["verification_status"], "not-run")
        self.assertFalse(finding["manual_review_required"])
        self.assertEqual(fix["fixability"], "auto-fix")
        self.assertEqual(fix["verification_status"], "not-run")
        self.assertIn("diff_summary", report["summary"])
        self.assertIn("remediation_lifecycle", report["summary"])
        self.assertIn("diff_artifacts", report["run_meta"])
        self.assertIn("risk_level", finding)
        self.assertIn("downgrade_reason", finding)
        self.assertIn("risk_level", fix)
        self.assertIn("downgrade_reason", fix)
        self.assertIn("fix_blockers", fix)
        self.assertIn("fix_blockers", report["summary"])

    def test_manual_review_items_are_flagged_in_contract(self) -> None:
        contract = resolve_contract({"target": "https://example.com", "wcag_version": "2.2"})
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)
        manual = next(item for item in report["findings"] if item["status"] == "needs-review")
        self.assertEqual(manual["fixability"], "manual")
        self.assertEqual(manual["verification_status"], "manual-review")
        self.assertTrue(manual["manual_review_required"])

    def test_findings_include_confidence(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        axe_data = {
            "violations": [
                {
                    "id": "button-name",
                    "impact": "serious",
                    "description": "Buttons must have discernible text",
                    "nodes": [{"target": ["button.icon"]}],
                }
            ]
        }
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        self.assertEqual(report["findings"][0]["confidence"], "high")

    def test_invalid_execution_mode_raises(self) -> None:
        with self.assertRaises(ValueError):
            resolve_contract({"target": "https://example.com", "execution_mode": "rewrite-all"})

    def test_escape_pipe_handles_none(self) -> None:
        self.assertEqual(_escape_pipe(None), "None")

    def test_empty_nodes_default_changed_target(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        axe_data = {
            "violations": [
                {
                    "id": "image-alt",
                    "impact": "serious",
                    "description": "Images must have alternate text",
                    "nodes": [],
                }
            ]
        }
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        self.assertEqual(report["findings"][0]["changed_target"], "unknown")

    def test_output_language_english_changes_markdown_labels(self) -> None:
        contract = resolve_contract({"target": "https://example.com", "output_language": "en-US"})
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)
        markdown = to_markdown_table(report)
        self.assertIn("Execution mode: suggest-only", markdown)
        self.assertIn("Files modified by core workflow: no", markdown)
        self.assertIn("Modification executed by: agent-or-adapter", markdown)
        self.assertIn("Issue ID", markdown)

    def test_wcag_22_manual_review_findings_are_added(self) -> None:
        contract = resolve_contract({"target": "https://example.com", "wcag_version": "2.2"})
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)
        manual_sc = {item["sc"][0] for item in report["findings"] if item["source"] == "manual" and item["sc"]}
        self.assertIn("2.4.11", manual_sc)
        self.assertIn("3.3.9", manual_sc)

    def test_lighthouse_severity_uses_score_bands(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        lighthouse_data = {
            "audits": {
                "image-alt": {
                    "score": 0.9,
                    "scoreDisplayMode": "binary",
                    "title": "Images have alt text",
                    "details": {"items": [{"node": {"selector": "img.hero"}}]},
                }
            }
        }
        report = normalize_report(contract, {"violations": []}, lighthouse_data, None, None)
        self.assertEqual(report["findings"][0]["severity"], "minor")


    def test_apply_fixes_mode_records_downgrade_and_blockers_for_non_auto_fix(self) -> None:
        contract = resolve_contract(
            {
                "target": "https://example.com",
                "execution_mode": "apply-fixes",
            }
        )
        axe_data = {
            "violations": [
                {
                    "id": "heading-order",
                    "impact": "moderate",
                    "description": "Heading levels should only increase by one",
                    "nodes": [{"target": ["h3.section"]}],
                }
            ]
        }
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        finding = report["findings"][0]
        fix = report["fixes"][0]
        self.assertEqual(finding["downgrade_reason"], "auto-fix-not-supported")
        self.assertEqual(fix["downgrade_reason"], "auto-fix-not-supported")
        self.assertIn("no-safe-auto-fix", fix["fix_blockers"])
        self.assertEqual(report["summary"]["fix_blockers"][0]["rule_id"], "heading-order")

    def test_normalize_report_cli_generates_outputs(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory() as tmp:
            raw_json = Path(tmp) / "axe.json"
            output_json = Path(tmp) / "report.json"
            output_md = Path(tmp) / "report.md"
            raw_json.write_text(
                json.dumps(
                    {
                        "violations": [
                            {
                                "id": "image-alt",
                                "impact": "serious",
                                "description": "Images must have alternate text",
                                "nodes": [{"target": ["img.hero"]}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "skills/libro-agent-wcag/scripts/normalize_report.py",
                    "--target",
                    "https://example.com",
                    "--execution-mode",
                    "audit-only",
                    "--output-language",
                    "en",
                    "--axe-json",
                    str(raw_json),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_meta"]["execution_mode"], "audit-only")
            self.assertTrue(output_md.exists())


if __name__ == "__main__":
    unittest.main()

