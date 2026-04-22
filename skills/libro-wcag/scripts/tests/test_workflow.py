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
    SCANNER_RULE_TO_SC,
    WCAG_UNDERSTANDING_PATHS,
    _escape_pipe,
    build_citation_url,
    load_json_file,
    normalize_report,
    resolve_contract,
    to_markdown_table,
    write_report_files,
)
from report_artifacts import _build_compact_summary
from report_renderers import render_badge, render_markdown


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

    def test_markdown_includes_debt_trend_summary_when_present(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)
        report['summary']['debt_trend'] = {
            'window': 4,
            'latest_counts': {'new': 1, 'accepted': 2, 'retired': 3, 'regressed': 1},
            'delta_from_previous': {'new': 1, 'accepted': 0, 'retired': -1, 'regressed': 1},
        }
        markdown = to_markdown_table(report)
        self.assertIn('債務趨勢: new=1, accepted=2, retired=3, regressed=1 (window=4)', markdown)
        self.assertIn('債務趨勢變化: new=1, accepted=0, retired=-1, regressed=1', markdown)

    def test_markdown_warns_when_scanner_coverage_is_incomplete_in_chinese(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(
            contract,
            {"violations": []},
            None,
            lighthouse_error="command timed out after 30 seconds",
        )
        markdown = to_markdown_table(report)
        self.assertIn('⚠️ 掃描器覆蓋不完整: lighthouse (timeout)', markdown)

    def test_aggregate_markdown_renderer_uses_single_report_generated_at_and_baseline_alias(self) -> None:
        contract = resolve_contract({"target": "https://example.com", "output_language": "en"})
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)
        report["run_meta"]["baseline_diff"] = {
            "introduced_count": 2,
            "resolved_count": 1,
            "persistent_count": 3,
        }

        markdown = render_markdown(report, language="en")

        self.assertIn(f"> Generated at: {report['run_meta']['generated_at']}", markdown)
        self.assertIn("| New findings | 2 |", markdown)
        self.assertIn("| Resolved | 1 |", markdown)
        self.assertIn("| Persistent | 3 |", markdown)

    def test_badge_renderer_accepts_single_report_semantics(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)

        badge = json.loads(render_badge(report))

        self.assertEqual(badge["color"], "brightgreen")
        self.assertEqual(badge["message"], "100% (0 findings)")

    def test_compact_summary_normalizes_baseline_new_count_alias(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        report = normalize_report(contract, {"violations": []}, {"audits": {}}, None, None)
        report["run_meta"]["baseline_diff"] = {
            "new_count": 4,
            "resolved_count": 1,
            "persistent_count": 2,
        }

        compact = _build_compact_summary(
            report=report,
            report_format="json",
            machine_output=Path("wcag-report.json"),
            output_md=Path("wcag-report.md"),
            should_fail=False,
            fail_on=None,
            exit_code=0,
        )

        self.assertEqual(compact["baseline_diff"]["introduced_count"], 4)
        self.assertEqual(compact["baseline_diff"]["resolved_count"], 1)
        self.assertEqual(compact["baseline_diff"]["persistent_count"], 2)

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

    def test_axe_list_payload_is_normalized_before_mapping(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        axe_data = [
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
        ]
        report = normalize_report(contract, axe_data, {"audits": {}})
        self.assertTrue(any(item["rule_id"] == "image-alt" for item in report["findings"]))

    def test_findings_include_inline_citations_for_selected_wcag_version(self) -> None:
        contract = resolve_contract({"target": "https://example.com", "wcag_version": "2.0"})
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
        report = normalize_report(contract, axe_data, {"audits": {}})
        finding = next(item for item in report["findings"] if item["rule_id"] == "image-alt")
        urls = [item["url"] for item in finding["citations"]]
        self.assertTrue(any("/WCAG20/" in url for url in urls))

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

    def test_partial_success_preserves_actionable_findings_when_lighthouse_fails(self) -> None:
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
        report = normalize_report(
            contract,
            axe_data,
            None,
            lighthouse_error="command timed out after 30 seconds",
        )
        self.assertTrue(any(item["rule_id"] == "image-alt" for item in report["findings"]))
        self.assertIn("scanner_failures", report["summary"])
        lighthouse_failure = next(
            item for item in report["summary"]["scanner_failures"] if item["tool"] == "lighthouse"
        )
        self.assertEqual(lighthouse_failure["classification"], "timeout")
        markdown = to_markdown_table(report)
        self.assertIn("⚠️ Scanner coverage incomplete: lighthouse (timeout)", markdown)

    def test_partial_success_preserves_actionable_findings_when_axe_fails(self) -> None:
        contract = resolve_contract({"target": "https://example.com", "output_language": "en"})
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
        report = normalize_report(
            contract,
            None,
            lighthouse_data,
            axe_error="command not found: npx",
        )
        self.assertTrue(any(item["rule_id"] == "label" for item in report["findings"]))
        self.assertIn("scanner_failures", report["summary"])
        axe_failure = next(item for item in report["summary"]["scanner_failures"] if item["tool"] == "axe")
        self.assertEqual(axe_failure["classification"], "missing-tool")
    def test_citation_url_uses_selected_version(self) -> None:
        self.assertEqual(
            build_citation_url("2.0", "1.1.1"),
            "https://www.w3.org/WAI/WCAG20/Understanding/non-text-content",
        )
        self.assertIn("/WCAG21/", build_citation_url("2.1", "1.1.1"))
        self.assertIn("/WCAG22/", build_citation_url("2.2", "1.1.1"))

    def test_citation_url_covers_previously_missing_common_success_criteria(self) -> None:
        expected = {
            "1.2.1": "audio-only-and-video-only-prerecorded",
            "1.3.4": "orientation",
            "1.3.5": "identify-input-purpose",
            "1.4.1": "use-of-color",
            "1.4.2": "audio-control",
        }
        for sc, slug in expected.items():
            self.assertEqual(
                build_citation_url("2.2", sc),
                f"https://www.w3.org/WAI/WCAG22/Understanding/{slug}",
            )

    def test_understanding_slug_table_covers_most_success_criteria(self) -> None:
        self.assertGreaterEqual(len(WCAG_UNDERSTANDING_PATHS), 75)

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

    def test_source_specific_rule_mapping_is_derived_from_shared_scanner_table(self) -> None:
        self.assertIs(AXE_RULE_TO_SC, SCANNER_RULE_TO_SC['axe'])
        self.assertIs(LIGHTHOUSE_RULE_TO_SC, SCANNER_RULE_TO_SC['lighthouse'])
        self.assertEqual(SCANNER_RULE_TO_SC['axe']['meta-refresh'], ['2.2.1', '3.2.5'])
        self.assertEqual(SCANNER_RULE_TO_SC['lighthouse']['meta-refresh'], ['2.2.2', '3.2.5'])

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


    def test_rule_family_and_summary_counts_are_populated(self) -> None:
        contract = resolve_contract({'target': 'https://example.com'})
        axe_data = {
            'violations': [
                {
                    'id': 'aria-valid-attr-value',
                    'impact': 'serious',
                    'description': 'Invalid aria attribute value',
                    'nodes': [{'target': ['div[role="button"]']}],
                }
            ]
        }
        report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
        finding = report['findings'][0]
        fix = report['fixes'][0]
        self.assertEqual(finding['rule_family'], 'aria')
        self.assertEqual(fix['rule_family'], 'aria')
        self.assertEqual(report['summary']['auto_fixed_count'], 0)
        self.assertEqual(report['summary']['manual_required_count'], 0)


    def test_new_m5_rules_are_marked_auto_fix_supported(self) -> None:
        contract = resolve_contract({'target': 'https://example.com', 'execution_mode': 'apply-fixes'})
        axe_data = {
            'violations': [
                {
                    'id': 'aria-required-attr',
                    'impact': 'serious',
                    'description': 'missing required aria attrs',
                    'nodes': [{'target': ['.acceptance']}],
                },
                {
                    'id': 'aria-valid-attr-value',
                    'impact': 'moderate',
                    'description': 'invalid aria attr values',
                    'nodes': [{'target': ['.status']}],
                },
                {
                    'id': 'td-has-header',
                    'impact': 'moderate',
                    'description': 'td needs headers',
                    'nodes': [{'target': ['table td']}],
                },
            ]
        }
        lighthouse_data = {
            'audits': {
                'th-has-data-cells': {
                    'score': 0,
                    'scoreDisplayMode': 'binary',
                    'title': 'th should map to data cells',
                    'details': {'items': [{'node': {'selector': 'table th'}}]},
                }
            }
        }
        report = normalize_report(contract, axe_data, lighthouse_data, None, None)
        finding_to_rule = {item['id']: item['rule_id'] for item in report['findings']}
        by_rule = {finding_to_rule[item['finding_id']]: item for item in report['fixes']}
        self.assertTrue(by_rule['aria-required-attr']['auto_fix_supported'])
        self.assertTrue(by_rule['aria-valid-attr-value']['auto_fix_supported'])
        self.assertTrue(by_rule['td-has-header']['auto_fix_supported'])
        self.assertTrue(by_rule['th-has-data-cells']['auto_fix_supported'])
        self.assertEqual(by_rule['td-has-header']['fixability'], 'auto-fix')
        self.assertEqual(by_rule['th-has-data-cells']['fixability'], 'auto-fix')

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
        self.assertIn("rule_family", finding)
        self.assertIn("downgrade_reason", finding)
        self.assertIn("before_after_targets", finding)
        self.assertIn("risk_level", fix)
        self.assertIn("rule_family", fix)
        self.assertIn("downgrade_reason", fix)
        self.assertIn("fix_blockers", fix)
        self.assertIn("verification_evidence", fix)
        self.assertIn("before_after_targets", fix)
        self.assertIn("fix_blockers", report["summary"])
        self.assertIn("auto_fixed_count", report["summary"])
        self.assertIn("manual_required_count", report["summary"])
        self.assertIn("before_after_targets", report["summary"])
        self.assertIn("verification_evidence", report["run_meta"])

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

    def test_load_json_file_raises_descriptive_error_for_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "broken.json"
            payload.write_text('{"broken": }', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"Invalid JSON in .*broken\.json: .*line 1, column"):
                load_json_file(str(payload))

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

    def test_finding_includes_best_effort_source_location(self) -> None:
        contract = resolve_contract({"target": "https://example.com"})
        axe_data = {
            "violations": [
                {
                    "id": "image-alt",
                    "impact": "serious",
                    "description": "Images must have alternate text",
                    "nodes": [{"target": ["img.hero"], "line": 12, "column": 4}],
                }
            ]
        }
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        self.assertEqual(report["findings"][0]["source_line"], 12)
        self.assertEqual(report["findings"][0]["source_column"], 4)
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
        self.assertEqual(finding["downgrade_reason"], "assisted-remediation-required")
        self.assertEqual(fix["downgrade_reason"], "assisted-remediation-required")
        self.assertIn("assisted-remediation-required", fix["fix_blockers"])
        self.assertEqual(report["summary"]["fix_blockers"][0]["rule_id"], "heading-order")

    def test_assisted_fix_includes_steps_and_verification_rules(self) -> None:
        contract = resolve_contract(
            {
                "target": "https://example.com",
                "execution_mode": "suggest-only",
            }
        )
        axe_data = {
            "violations": [
                {
                    "id": "duplicate-id-aria",
                    "impact": "serious",
                    "description": "IDs used in ARIA and labels must be unique",
                    "nodes": [{"target": ["[id='search-label']"]}],
                }
            ]
        }
        report = normalize_report(contract, axe_data, {"audits": {}}, None, None)
        fix = report["fixes"][0]
        self.assertEqual(fix["fixability"], "assisted")
        self.assertGreater(len(fix["assisted_steps"]), 0)
        self.assertGreater(len(fix["verification_rules"]), 0)
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
                    "skills/libro-wcag/scripts/normalize_report.py",
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
