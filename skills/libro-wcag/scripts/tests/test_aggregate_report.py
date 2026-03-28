#!/usr/bin/env python3
"""Tests for aggregate_report.py and report_renderers.py (P0 items A1-A4, B1-B3, C1)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from aggregate_report import (
    build_aggregate_report,
    load_report,
    load_reports,
    write_aggregate_json,
)
from report_renderers import render_badge, render_csv, render_markdown, render_terminal


def _make_finding(
    rule_id: str = "image-alt",
    severity: str = "serious",
    fixability: str = "auto-fix",
    status: str = "open",
) -> dict:
    return {
        "id": f"F-{rule_id}-001",
        "source": "axe",
        "sources": ["axe"],
        "rule_id": rule_id,
        "severity": severity,
        "confidence": "high",
        "sc": ["1.1.1"],
        "current": "<img src='photo.jpg'>",
        "changed_target": "<img src='photo.jpg' alt='Photo'>",
        "status": status,
        "fixability": fixability,
        "verification_status": "not-run",
        "manual_review_required": False,
    }


def _make_report(
    target: str = "src/index.html",
    findings: list[dict] | None = None,
    wcag_version: str = "2.1",
    conformance_level: str = "AA",
) -> dict:
    if findings is None:
        findings = [_make_finding()]
    return {
        "report_schema": {
            "name": "libro-wcag-report",
            "version": "1.0.0",
            "artifact": "wcag-report.json",
            "compatibility": ">=1.0.0",
        },
        "run_meta": {
            "generated_at": "2026-03-28T12:00:00Z",
            "workflow_version": "1.0.0",
            "execution_mode": "suggest-only",
            "output_language": "zh-TW",
            "files_modified": False,
            "modification_owner": "agent-or-adapter",
            "diff_artifacts": [],
            "verification_evidence": [],
            "tools": {"axe": "ok", "lighthouse": "ok"},
            "notes": [],
            "report_schema_version": "1.0.0",
        },
        "target": {"value": target, "task_mode": "modify"},
        "standard": {
            "wcag_version": wcag_version,
            "conformance_level": conformance_level,
        },
        "findings": findings,
        "fixes": [],
        "citations": [],
        "summary": {
            "total_findings": len(findings),
            "fixed_findings": 0,
            "auto_fixed_count": 0,
            "needs_manual_review": 0,
            "manual_required_count": 0,
            "change_summary": [],
            "diff_summary": [],
            "before_after_targets": [],
            "remediation_lifecycle": {
                "planned": len(findings),
                "implemented": 0,
                "verified": 0,
                "manual_review_required": 0,
            },
            "fix_blockers": [],
        },
    }


class TestLoadReport(unittest.TestCase):
    def test_load_valid_report(self) -> None:
        report = _make_report()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(report, f, ensure_ascii=False)
            f.flush()
            loaded = load_report(Path(f.name))
        self.assertEqual(loaded["target"]["value"], "src/index.html")

    def test_load_missing_findings_raises(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"target": {}}, f)
            f.flush()
            with self.assertRaises(ValueError):
                load_report(Path(f.name))


class TestBuildAggregateReport(unittest.TestCase):
    def test_single_report_aggregation(self) -> None:
        report = _make_report(findings=[
            _make_finding(severity="critical"),
            _make_finding(rule_id="button-name", severity="serious"),
        ])
        agg = build_aggregate_report([report])

        self.assertEqual(agg["report_type"], "aggregate")
        self.assertEqual(agg["standard"]["wcag_version"], "2.1")

        # A1: scope
        scope = agg["scope"]
        self.assertEqual(scope["total_targets"], 1)
        self.assertEqual(scope["targets_with_issues"], 1)
        self.assertEqual(scope["clean_targets"], 0)
        self.assertEqual(scope["total_findings"], 2)
        self.assertEqual(scope["verdict"], "fail")  # has critical

    def test_clean_target_yields_pass(self) -> None:
        report = _make_report(findings=[])
        agg = build_aggregate_report([report])
        self.assertEqual(agg["scope"]["verdict"], "pass")
        self.assertEqual(agg["scope"]["compliance_rate"], 1.0)

    def test_multiple_reports_aggregation(self) -> None:
        r1 = _make_report(
            target="page1.html",
            findings=[
                _make_finding(severity="serious"),
                _make_finding(rule_id="link-name", severity="moderate"),
            ],
        )
        r2 = _make_report(
            target="page2.html",
            findings=[_make_finding(severity="minor")],
        )
        r3 = _make_report(target="page3.html", findings=[])

        agg = build_aggregate_report([r1, r2, r3])
        scope = agg["scope"]
        self.assertEqual(scope["total_targets"], 3)
        self.assertEqual(scope["targets_with_issues"], 2)
        self.assertEqual(scope["clean_targets"], 1)
        self.assertEqual(scope["total_findings"], 3)
        self.assertEqual(scope["verdict"], "needs-review")

    def test_severity_breakdown(self) -> None:
        report = _make_report(findings=[
            _make_finding(severity="critical"),
            _make_finding(severity="critical"),
            _make_finding(severity="serious"),
            _make_finding(severity="moderate"),
            _make_finding(severity="info"),
        ])
        agg = build_aggregate_report([report])
        sev = agg["severity"]
        self.assertEqual(sev["critical"]["count"], 2)
        self.assertEqual(sev["serious"]["count"], 1)
        self.assertEqual(sev["moderate"]["count"], 1)
        self.assertEqual(sev["minor"]["count"], 0)
        self.assertEqual(sev["info"]["count"], 1)
        self.assertAlmostEqual(sev["critical"]["percentage"], 40.0)

    def test_fixability_analysis(self) -> None:
        report = _make_report(findings=[
            _make_finding(fixability="auto-fix"),
            _make_finding(fixability="auto-fix"),
            _make_finding(fixability="assisted"),
            _make_finding(fixability="manual"),
        ])
        agg = build_aggregate_report([report])
        fix = agg["fixability"]
        self.assertEqual(fix["auto-fix"]["count"], 2)
        self.assertEqual(fix["assisted"]["count"], 1)
        self.assertEqual(fix["manual"]["count"], 1)
        self.assertAlmostEqual(fix["fix_coverage"], 0.5)

    def test_per_target_sorted_by_findings(self) -> None:
        r1 = _make_report(target="few.html", findings=[_make_finding()])
        r2 = _make_report(target="many.html", findings=[
            _make_finding(),
            _make_finding(),
            _make_finding(),
        ])
        agg = build_aggregate_report([r1, r2])
        targets = agg["targets"]
        self.assertEqual(targets[0]["target"], "many.html")
        self.assertEqual(targets[1]["target"], "few.html")

    def test_empty_reports_list(self) -> None:
        agg = build_aggregate_report([])
        self.assertEqual(agg["scope"]["total_targets"], 0)
        self.assertEqual(agg["scope"]["verdict"], "pass")

    def test_remediation_lifecycle_aggregation(self) -> None:
        r1 = _make_report(findings=[_make_finding()])
        r1["summary"]["remediation_lifecycle"]["planned"] = 3
        r1["summary"]["remediation_lifecycle"]["implemented"] = 1
        r2 = _make_report(findings=[_make_finding()])
        r2["summary"]["remediation_lifecycle"]["planned"] = 2
        r2["summary"]["remediation_lifecycle"]["verified"] = 1

        agg = build_aggregate_report([r1, r2])
        lifecycle = agg["remediation_lifecycle"]
        self.assertEqual(lifecycle["planned"], 5)
        self.assertEqual(lifecycle["implemented"], 1)
        self.assertEqual(lifecycle["verified"], 1)


class TestWriteAggregateJson(unittest.TestCase):
    def test_write_creates_file(self) -> None:
        report = _make_report(findings=[])
        agg = build_aggregate_report([report])
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "output" / "aggregate.json"
            write_aggregate_json(agg, out)
            self.assertTrue(out.exists())
            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["report_type"], "aggregate")


class TestTerminalRenderer(unittest.TestCase):
    def test_render_includes_sections(self) -> None:
        report = _make_report(findings=[_make_finding(severity="critical")])
        agg = build_aggregate_report([report])
        output = render_terminal(agg, language="zh-TW")
        self.assertIn("WCAG 彙總報告", output)
        self.assertIn("嚴重度分級", output)
        self.assertIn("可修正性分析", output)
        self.assertIn("各目標明細", output)

    def test_render_english(self) -> None:
        report = _make_report(findings=[_make_finding()])
        agg = build_aggregate_report([report])
        output = render_terminal(agg, language="en")
        self.assertIn("WCAG Aggregate Report", output)
        self.assertIn("Severity Breakdown", output)

    def test_render_empty_report(self) -> None:
        agg = build_aggregate_report([])
        output = render_terminal(agg)
        self.assertIn("0", output)


class TestMarkdownRenderer(unittest.TestCase):
    def test_render_includes_tables(self) -> None:
        r1 = _make_report(
            target="index.html",
            findings=[
                _make_finding(severity="critical"),
                _make_finding(severity="serious", fixability="assisted"),
            ],
        )
        r2 = _make_report(target="about.html", findings=[])
        agg = build_aggregate_report([r1, r2])
        output = render_markdown(agg, language="zh-TW")
        self.assertIn("# WCAG 彙總報告", output)
        self.assertIn("|", output)
        self.assertIn("<details>", output)
        self.assertIn("index.html", output)

    def test_render_english_markdown(self) -> None:
        report = _make_report(findings=[_make_finding()])
        agg = build_aggregate_report([report])
        output = render_markdown(agg, language="en")
        self.assertIn("# WCAG Aggregate Report", output)
        self.assertIn("Scope", output)


class TestWcagPrincipleCoverage(unittest.TestCase):
    """A5: WCAG SC Coverage Analysis."""

    def test_principles_grouped_correctly(self) -> None:
        report = _make_report(findings=[
            _make_finding(rule_id="image-alt"),          # sc=["1.1.1"] → perceivable
            _make_finding(rule_id="button-name"),        # sc=["1.1.1"] → perceivable
            _make_finding(rule_id="link-name"),          # sc=["1.1.1"] → perceivable
        ])
        # Override SCs for diversity
        report["findings"][1]["sc"] = ["4.1.2"]  # robust
        report["findings"][2]["sc"] = ["2.4.4"]  # operable

        agg = build_aggregate_report([report])
        principles = agg["wcag_principles"]
        self.assertEqual(principles["perceivable"]["count"], 1)
        self.assertIn("1.1.1", principles["perceivable"]["sc"])
        self.assertEqual(principles["operable"]["count"], 1)
        self.assertIn("2.4.4", principles["operable"]["sc"])
        self.assertEqual(principles["robust"]["count"], 1)
        self.assertIn("4.1.2", principles["robust"]["sc"])
        self.assertEqual(principles["understandable"]["count"], 0)

    def test_empty_findings_all_zeros(self) -> None:
        agg = build_aggregate_report([])
        for p in ("perceivable", "operable", "understandable", "robust"):
            self.assertEqual(agg["wcag_principles"][p]["count"], 0)
            self.assertEqual(agg["wcag_principles"][p]["sc"], [])


class TestTopRules(unittest.TestCase):
    """A6: Top Issues Analysis."""

    def test_rules_ranked_by_frequency(self) -> None:
        report = _make_report(findings=[
            _make_finding(rule_id="image-alt"),
            _make_finding(rule_id="image-alt"),
            _make_finding(rule_id="image-alt"),
            _make_finding(rule_id="button-name"),
            _make_finding(rule_id="link-name"),
        ])
        agg = build_aggregate_report([report])
        top = agg["top_rules"]
        self.assertEqual(top[0]["rule_id"], "image-alt")
        self.assertEqual(top[0]["count"], 3)
        self.assertEqual(len(top), 3)

    def test_empty_findings_no_rules(self) -> None:
        agg = build_aggregate_report([])
        self.assertEqual(agg["top_rules"], [])


class TestAutoFixOpportunityEnhanced(unittest.TestCase):
    """A7: Enhanced auto-fix opportunity with framework groups."""

    def test_framework_groups_from_fix_hints(self) -> None:
        report = _make_report(findings=[_make_finding()])
        report["fixes"] = [
            {
                "id": "FIX-001",
                "finding_id": "F-image-alt-001",
                "description": "Add alt",
                "changed_target": "",
                "status": "planned",
                "remediation_priority": "high",
                "confidence": "high",
                "auto_fix_supported": True,
                "fixability": "auto-fix",
                "verification_status": "not-run",
                "manual_review_required": False,
                "framework_hints": {"react": {"component": "Image"}},
            },
        ]
        agg = build_aggregate_report([report])
        auto_fix = agg["auto_fix_opportunity"]
        self.assertIn("framework_groups", auto_fix)
        self.assertEqual(auto_fix["framework_groups"][0]["framework"], "react")


class TestRendererP1Sections(unittest.TestCase):
    """Verify A5 and A6 appear in terminal and markdown renderers."""

    def test_terminal_includes_principles_and_top_issues(self) -> None:
        report = _make_report(findings=[_make_finding()])
        agg = build_aggregate_report([report])
        output = render_terminal(agg, language="zh-TW")
        self.assertIn("WCAG 原則涵蓋分析", output)
        self.assertIn("熱點分析", output)

    def test_markdown_includes_principles_and_top_issues(self) -> None:
        report = _make_report(findings=[_make_finding()])
        agg = build_aggregate_report([report])
        output = render_markdown(agg, language="en")
        self.assertIn("WCAG Principle Coverage", output)
        self.assertIn("Top Issues", output)
        self.assertIn("image-alt", output)


class TestBaselineDiff(unittest.TestCase):
    """A9: Trend / Baseline Diff."""

    def test_baseline_diff_detects_changes(self) -> None:
        baseline = [_make_report(
            target="page.html",
            findings=[
                _make_finding(rule_id="image-alt"),
                _make_finding(rule_id="button-name"),
            ],
        )]
        current = [_make_report(
            target="page.html",
            findings=[
                _make_finding(rule_id="image-alt"),    # persistent
                _make_finding(rule_id="link-name"),     # new
            ],
        )]
        agg = build_aggregate_report(current, baseline_reports=baseline)
        diff = agg["baseline_diff"]
        self.assertIsNotNone(diff)
        self.assertEqual(diff["new_count"], 1)       # link-name
        self.assertEqual(diff["resolved_count"], 1)  # button-name
        self.assertEqual(diff["persistent_count"], 1) # image-alt

    def test_no_baseline_returns_none(self) -> None:
        agg = build_aggregate_report([_make_report()])
        self.assertIsNone(agg["baseline_diff"])


class TestCsvRenderer(unittest.TestCase):
    """B5: CSV Output."""

    def test_csv_header_and_rows(self) -> None:
        r1 = _make_report(
            target="index.html",
            findings=[
                _make_finding(rule_id="image-alt", severity="critical"),
                _make_finding(rule_id="button-name", severity="serious"),
            ],
        )
        r2 = _make_report(target="about.html", findings=[_make_finding()])
        output = render_csv([r1, r2])
        lines = output.strip().split("\n")
        self.assertEqual(lines[0], "target,rule_id,severity,fixability,sc,status,source,current,changed_target")
        self.assertEqual(len(lines), 4)  # header + 3 findings
        self.assertIn("index.html", lines[1])
        self.assertIn("about.html", lines[3])

    def test_csv_escapes_commas(self) -> None:
        finding = _make_finding()
        finding["current"] = '<img src="a,b">'
        report = _make_report(findings=[finding])
        output = render_csv([report])
        # Value with comma should be quoted
        self.assertIn('"', output)

    def test_csv_empty_reports(self) -> None:
        output = render_csv([])
        lines = output.strip().split("\n")
        self.assertEqual(len(lines), 1)  # header only


class TestMarkdownBaselineDiff(unittest.TestCase):
    """Verify baseline diff appears in Markdown output."""

    def test_markdown_includes_baseline_when_present(self) -> None:
        baseline = [_make_report(findings=[_make_finding(rule_id="old-rule")])]
        current = [_make_report(findings=[_make_finding(rule_id="new-rule")])]
        agg = build_aggregate_report(current, baseline_reports=baseline)
        output = render_markdown(agg, language="en")
        self.assertIn("Baseline Diff", output)
        self.assertIn("New findings", output)

    def test_markdown_omits_baseline_when_absent(self) -> None:
        agg = build_aggregate_report([_make_report()])
        output = render_markdown(agg, language="en")
        self.assertNotIn("Baseline Diff", output)


class TestScannerHealth(unittest.TestCase):
    """A10: Scanner Health Status."""

    def test_all_ok(self) -> None:
        report = _make_report(findings=[_make_finding()])
        agg = build_aggregate_report([report])
        health = agg["scanner_health"]
        self.assertEqual(health["tools"]["axe"], "ok")
        self.assertEqual(health["tools"]["lighthouse"], "ok")
        self.assertEqual(health["scanner_failures"], [])

    def test_scanner_failure_collected(self) -> None:
        report = _make_report(findings=[])
        report["run_meta"]["scanner_failures"] = [
            {"tool": "axe", "message": "timeout", "classification": "transient"},
        ]
        report["run_meta"]["tools"]["axe"] = "error"
        agg = build_aggregate_report([report])
        health = agg["scanner_health"]
        self.assertEqual(health["tools"]["axe"], "error")
        self.assertEqual(len(health["scanner_failures"]), 1)


class TestBadgeRenderer(unittest.TestCase):
    """B6: Badge Output."""

    def test_badge_green_for_high_compliance(self) -> None:
        report = _make_report(target="clean.html", findings=[])
        agg = build_aggregate_report([report])
        output = render_badge(agg)
        data = json.loads(output)
        self.assertEqual(data["schemaVersion"], 1)
        self.assertEqual(data["label"], "WCAG")
        self.assertEqual(data["color"], "brightgreen")

    def test_badge_red_for_low_compliance(self) -> None:
        reports = [
            _make_report(target=f"page{i}.html", findings=[_make_finding(severity="critical")])
            for i in range(5)
        ]
        agg = build_aggregate_report(reports)
        output = render_badge(agg)
        data = json.loads(output)
        self.assertEqual(data["color"], "red")

    def test_badge_yellow_for_moderate_compliance(self) -> None:
        reports = [
            _make_report(target="ok.html", findings=[]),
            _make_report(target="bad.html", findings=[_make_finding()]),
        ]
        agg = build_aggregate_report(reports)
        output = render_badge(agg)
        data = json.loads(output)
        self.assertEqual(data["color"], "yellow")


class TestLoadReports(unittest.TestCase):
    def test_load_multiple_files(self) -> None:
        reports_data = [
            _make_report(target="a.html"),
            _make_report(target="b.html"),
        ]
        paths: list[Path] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, data in enumerate(reports_data):
                p = Path(tmpdir) / f"report_{i}.json"
                p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                paths.append(p)
            loaded = load_reports(paths)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["target"]["value"], "a.html")
        self.assertEqual(loaded[1]["target"]["value"], "b.html")


if __name__ == "__main__":
    unittest.main()
