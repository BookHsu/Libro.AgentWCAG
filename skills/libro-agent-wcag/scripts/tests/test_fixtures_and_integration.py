#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from wcag_workflow import normalize_report, resolve_contract, to_markdown_table


class FixtureAndSnapshotTests(unittest.TestCase):
    def _load_snapshot(self, name: str) -> tuple[dict, str]:
        snapshots = Path(__file__).parent / 'snapshots'
        return (
            json.loads((snapshots / f'{name}.report.json').read_text(encoding='utf-8')),
            (snapshots / f'{name}.report.md').read_text(encoding='utf-8'),
        )

    def test_snapshot_for_missing_alt_fixture_matches_expected_output(self) -> None:
        expected_json, expected_md = self._load_snapshot('missing-alt')
        contract = resolve_contract({'target': 'fixtures/missing-alt.html', 'output_language': 'en'})
        axe_data = {
            'violations': [
                {'id': 'image-alt', 'impact': 'serious', 'description': 'Images must have alternate text', 'nodes': [{'target': ['img.hero']}]}
            ]
        }
        lighthouse_data = {
            'audits': {
                'image-alt': {
                    'score': 0,
                    'scoreDisplayMode': 'binary',
                    'title': 'Image elements have [alt] attributes',
                    'details': {'items': [{'node': {'selector': 'img.hero'}}]},
                }
            }
        }
        report = normalize_report(contract, axe_data, lighthouse_data)
        report['run_meta']['generated_at'] = '<generated>'
        self.assertEqual(report, expected_json)
        self.assertEqual(to_markdown_table(report), expected_md)

    def test_snapshot_for_empty_link_viewport_fixture_matches_expected_output(self) -> None:
        expected_json, expected_md = self._load_snapshot('empty-link-viewport')
        contract = resolve_contract({'target': 'fixtures/empty-link-viewport.html', 'output_language': 'en'})
        axe_data = {
            'violations': [
                {'id': 'link-name', 'impact': 'serious', 'description': 'Links must have discernible text', 'nodes': [{'target': ['a.cta']}]},
                {'id': 'meta-viewport', 'impact': 'moderate', 'description': 'Viewport must not disable zoom', 'nodes': [{'target': ['meta[name="viewport"]']}]},
            ]
        }
        lighthouse_data = {
            'audits': {
                'link-name': {
                    'score': 0,
                    'scoreDisplayMode': 'binary',
                    'title': 'Links have discernible text',
                    'details': {'items': [{'node': {'selector': 'a.cta'}}]},
                },
                'meta-viewport': {
                    'score': 0,
                    'scoreDisplayMode': 'binary',
                    'title': 'User-scalable is not disabled',
                    'details': {'items': [{'node': {'selector': 'meta[name="viewport"]'}}]},
                },
            }
        }
        report = normalize_report(contract, axe_data, lighthouse_data)
        report['run_meta']['generated_at'] = '<generated>'
        self.assertEqual(report, expected_json)
        self.assertEqual(to_markdown_table(report), expected_md)

    def test_snapshot_for_wcag22_manual_review_fixture_matches_expected_output(self) -> None:
        expected_json, expected_md = self._load_snapshot('wcag22-manual-review')
        contract = resolve_contract(
            {'target': 'fixtures/wcag22-manual-review.html', 'output_language': 'en', 'wcag_version': '2.2'}
        )
        report = normalize_report(contract, {'violations': []}, {'audits': {}}, None, None)
        report['run_meta']['generated_at'] = '<generated>'
        self.assertEqual(report, expected_json)
        self.assertEqual(to_markdown_table(report), expected_md)


class FixtureCorpusCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = Path(__file__).parent / 'fixtures'

    def _read_fixture(self, name: str) -> str:
        return (self.fixture_root / name).read_text(encoding='utf-8')

    def test_m8_fixture_families_are_present_with_expected_signals(self) -> None:
        expectations = {
            'aria-family.html': ['aria-expanded="maybe"', 'role="slider"', 'aria-labelledby="missing-label-id"'],
            'form-errors.html': ['aria-invalid="invalid"', '<button type="submit"></button>', '<input id="coupon" type="text">'],
            'heading-hierarchy.html': ['<h1>Accessibility report</h1>', '<h3>Skipped level heading</h3>', '<h2></h2>'],
            'landmark-region.html': ['<div class="shell">', '<section>', '<aside>'],
            'table-semantics.html': ['<table>', '<td>Order ID</td>', '<td>Status</td>'],
            'keyboard-tabindex.html': ['tabindex="3"', 'tabindex="5"', 'role="button" tabindex="5"'],
            'wcag22-focus.html': ['.nav-link:focus', 'outline: none;', 'sticky-banner'],
            'create-mode-draft.html': ['data-task-mode="create"', 'data-draft="true"', 'requires manual WCAG verification'],
        }
        for fixture_name, required_tokens in expectations.items():
            with self.subTest(fixture=fixture_name):
                body = self._read_fixture(fixture_name)
                for token in required_tokens:
                    self.assertIn(token, body)


@unittest.skipUnless(os.environ.get('LIBRO_RUN_REAL_SCANNERS') == '1' and shutil.which('npx'), 'real scanner integration disabled')
class RealScannerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.fixture_root = cls.repo_root / 'skills' / 'libro-agent-wcag' / 'scripts' / 'tests' / 'fixtures'
        cls.snapshot_root = Path(__file__).parent / 'snapshots'

    def _run_real_scan(
        self,
        fixture_name: str,
        *,
        wcag_version: str = '2.1',
        execution_mode: str = 'suggest-only',
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(fixture_name)
            if not fixture.exists():
                fixture = self.fixture_root / fixture_name
            completed = subprocess.run(
                [
                    sys.executable,
                    'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                    '--target',
                    str(fixture),
                    '--output-dir',
                    tmp,
                    '--output-language',
                    'en',
                    '--wcag-version',
                    wcag_version,
                    '--execution-mode',
                    execution_mode,
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report_path = Path(tmp) / 'wcag-report.json'
            return json.loads(report_path.read_text(encoding='utf-8'))

    def test_run_accessibility_audit_executes_real_scanners_on_fixture_matrix(self) -> None:
        baseline = json.loads((self.snapshot_root / 'real-scanner-baselines.json').read_text(encoding='utf-8'))
        for case in baseline['fixture_matrix']:
            fixture_name = case['fixture']
            with self.subTest(fixture=fixture_name):
                report = self._run_real_scan(fixture_name)
                rules = {item['rule_id'] for item in report['findings']}
                self.assertGreaterEqual(len(report['findings']), case['minimum_findings'])
                expected_any = set(case.get('expected_any_rules', []))
                if expected_any:
                    self.assertTrue(expected_any & rules)

    def test_wcag_version_specific_real_scanner_baselines(self) -> None:
        baseline = json.loads((self.snapshot_root / 'real-scanner-baselines.json').read_text(encoding='utf-8'))
        fixture_name = baseline['version_baseline']['fixture']
        for wcag_version in baseline['version_baseline']['versions']:
            with self.subTest(wcag_version=wcag_version):
                report = self._run_real_scan(fixture_name, wcag_version=wcag_version)
                self.assertEqual(report['standard']['wcag_version'], wcag_version)
                manual_rules = [
                    item['rule_id']
                    for item in report['findings']
                    if item['rule_id'].startswith('wcag22-manual-')
                ]
                if wcag_version == '2.2':
                    self.assertGreaterEqual(len(manual_rules), baseline['version_baseline']['wcag22_manual_minimum'])
                else:
                    self.assertEqual(manual_rules, [])

    def test_apply_fixes_before_after_scanner_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_fixture = self.fixture_root / 'empty-link-viewport.html'
            target_fixture = Path(tmp) / 'empty-link-viewport.html'
            target_fixture.write_text(source_fixture.read_text(encoding='utf-8'), encoding='utf-8')

            before = self._run_real_scan(str(target_fixture))
            apply_report = self._run_real_scan(str(target_fixture), execution_mode='apply-fixes')
            self.assertTrue(apply_report['run_meta']['files_modified'])
            self.assertGreater(apply_report['summary']['auto_fixed_count'], 0)

            after = self._run_real_scan(str(target_fixture))
            self.assertLessEqual(len(after['findings']), len(before['findings']))

    def test_real_scanner_regression_snapshot_coverage(self) -> None:
        baseline = json.loads((self.snapshot_root / 'real-scanner-baselines.json').read_text(encoding='utf-8'))
        for case in baseline['regression_snapshot']:
            fixture_name = case['fixture']
            with self.subTest(fixture=fixture_name):
                report = self._run_real_scan(fixture_name)
                tools = report['run_meta']['tools']
                self.assertEqual(tools['axe'], 'ok')
                self.assertEqual(tools['lighthouse'], 'ok')
                self.assertGreaterEqual(len(report['findings']), case['minimum_findings'])
                self.assertIn('summary', report)
                self.assertIn('fixes', report)


if __name__ == '__main__':
    unittest.main()
