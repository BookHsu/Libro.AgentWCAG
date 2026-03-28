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
from report_renderers import render_markdown, render_terminal


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
