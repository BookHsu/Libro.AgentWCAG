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

    def test_snapshot_for_framework_fixtures_matches_expected_output(self) -> None:
        matrix = [
            ('react-specific', 'img.hero'),
            ('vue-specific', 'img.hero'),
            ('nextjs-specific', 'img.hero'),
        ]
        for fixture_name, selector in matrix:
            with self.subTest(fixture=fixture_name):
                expected_json, expected_md = self._load_snapshot(fixture_name)
                contract = resolve_contract({'target': f'fixtures/{fixture_name}.html', 'output_language': 'en'})
                axe_data = {
                    'violations': [
                        {
                            'id': 'image-alt',
                            'impact': 'serious',
                            'description': 'Images must have alternate text',
                            'nodes': [{'target': [selector]}],
                        }
                    ]
                }
                lighthouse_data = {
                    'audits': {
                        'image-alt': {
                            'score': 0,
                            'scoreDisplayMode': 'binary',
                            'title': 'Image elements have [alt] attributes',
                            'details': {'items': [{'node': {'selector': selector}}]},
                        }
                    }
                }
                report = normalize_report(contract, axe_data, lighthouse_data)
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
            'react-specific.html': ['data-reactroot', 'data-testid="react-state"', 'aria-label={ctaLabel}'],
            'vue-specific.html': ['data-v-app', 'v-bind:aria-label="submitLabel"', '@click="submitForm"'],
            'nextjs-specific.html': ['data-nextjs-root', 'data-next-layout="app-router"', 'export const metadata'],
            'realistic-mixed-findings.html': ['class="hero"', 'class="icon-only"', 'class="plain"'],
        }
        for fixture_name, required_tokens in expectations.items():
            with self.subTest(fixture=fixture_name):
                body = self._read_fixture(fixture_name)
                for token in required_tokens:
                    self.assertIn(token, body)


class RealScannerSnapshotContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = Path(__file__).parent / 'fixtures'
        cls.regression_path = Path(__file__).parent / 'snapshots' / 'real-scanner-regression.snapshot.json'
        cls.baselines_path = Path(__file__).parent / 'snapshots' / 'real-scanner-baselines.json'
        cls.repo_root = Path(__file__).resolve().parents[4]

    def _resolve_fixture(self, fixture_name: str) -> Path:
        direct = self.repo_root / fixture_name
        if direct.exists():
            return direct
        return self.fixture_root / fixture_name

    def test_real_scanner_regression_snapshot_is_present_and_references_existing_fixtures(self) -> None:
        snapshot = json.loads(self.regression_path.read_text(encoding='utf-8'))
        self.assertIn('integration_matrix', snapshot)
        self.assertIn('wcag_version_baseline', snapshot)
        self.assertIn('apply_fixes_regression', snapshot)

        matrix = snapshot['integration_matrix']
        self.assertGreaterEqual(len(matrix), 4)
        for entry in matrix:
            self.assertTrue(self._resolve_fixture(entry['fixture']).exists())
            self.assertIsInstance(entry['expected_rules'], list)
            self.assertTrue(entry['expected_rules'])

        version_baseline = snapshot['wcag_version_baseline']
        self.assertTrue(self._resolve_fixture(version_baseline['fixture']).exists())
        self.assertIn(version_baseline['rule_id'], {'image-alt', 'label', 'link-name'})
        self.assertEqual(version_baseline['versions'], ['2.0', '2.1', '2.2'])

        apply_fixes = snapshot['apply_fixes_regression']
        self.assertTrue(self._resolve_fixture(apply_fixes['fixture']).exists())
        self.assertIsInstance(apply_fixes['fixable_rules'], list)
        self.assertGreaterEqual(len(apply_fixes['fixable_rules']), 3)

    def test_real_scanner_baselines_manifest_is_present_and_references_existing_fixtures(self) -> None:
        baseline = json.loads(self.baselines_path.read_text(encoding='utf-8'))
        self.assertIn('fixture_matrix', baseline)
        self.assertIn('version_baseline', baseline)
        self.assertIn('regression_snapshot', baseline)

        for entry in baseline['fixture_matrix']:
            self.assertTrue(self._resolve_fixture(entry['fixture']).exists())
            self.assertGreaterEqual(entry['minimum_findings'], 1)

        version_baseline = baseline['version_baseline']
        self.assertTrue(self._resolve_fixture(version_baseline['fixture']).exists())
        self.assertEqual(version_baseline['versions'], ['2.0', '2.1', '2.2'])
        self.assertGreaterEqual(version_baseline['wcag22_manual_minimum'], 1)

        for entry in baseline['regression_snapshot']:
            self.assertTrue(self._resolve_fixture(entry['fixture']).exists())
            self.assertGreaterEqual(entry['minimum_findings'], 1)
            self.assertIn(entry.get('allow_lighthouse_error', False), {True, False})


@unittest.skipUnless(os.environ.get('LIBRO_RUN_REAL_SCANNERS') == '1' and shutil.which('npx'), 'real scanner integration disabled')
class RealScannerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.fixture_root = cls.repo_root / 'skills' / 'libro-wcag' / 'scripts' / 'tests' / 'fixtures'
        cls.regression_snapshot = json.loads(
            (
                cls.repo_root
                / 'skills'
                / 'libro-wcag'
                / 'scripts'
                / 'tests'
                / 'snapshots'
                / 'real-scanner-regression.snapshot.json'
            ).read_text(encoding='utf-8')
        )
        cls.baselines = json.loads(
            (
                cls.repo_root
                / 'skills'
                / 'libro-wcag'
                / 'scripts'
                / 'tests'
                / 'snapshots'
                / 'real-scanner-baselines.json'
            ).read_text(encoding='utf-8')
        )

    def _run_audit(
        self,
        fixture_name: str,
        tmp_dir: str,
        *,
        wcag_version: str = '2.1',
        execution_mode: str = 'suggest-only',
    ) -> tuple[dict, Path]:
        source_fixture = Path(fixture_name)
        if not source_fixture.exists():
            source_fixture = self.fixture_root / fixture_name
        if execution_mode == 'apply-fixes':
            target_path = Path(tmp_dir) / source_fixture.name
            target_path.write_text(source_fixture.read_text(encoding='utf-8'), encoding='utf-8')
        else:
            target_path = source_fixture
        completed = subprocess.run(
            [
                sys.executable,
                'skills/libro-wcag/scripts/run_accessibility_audit.py',
                '--target',
                str(target_path),
                '--output-dir',
                tmp_dir,
                '--output-language',
                'en',
                '--execution-mode',
                execution_mode,
                '--wcag-version',
                wcag_version,
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return json.loads((Path(tmp_dir) / 'wcag-report.json').read_text(encoding='utf-8')), target_path

    def test_run_accessibility_audit_executes_real_scanners_on_fixture_matrix(self) -> None:
        cases = list(self.regression_snapshot['integration_matrix']) + list(self.baselines['fixture_matrix'])
        seen: set[str] = set()
        for item in cases:
            fixture_name = item['fixture']
            if fixture_name in seen:
                continue
            seen.add(fixture_name)
            expected_rules = set(item.get('expected_rules', [])) | set(item.get('expected_any_rules', []))
            with self.subTest(fixture=fixture_name), tempfile.TemporaryDirectory() as tmp:
                report, _ = self._run_audit(fixture_name, tmp)
                rules = {entry['rule_id'] for entry in report['findings']}
                minimum_findings = item.get('minimum_findings', 1)
                self.assertGreaterEqual(len(report['findings']), minimum_findings)
                if expected_rules:
                    self.assertTrue(expected_rules & rules)
                self.assertTrue((Path(tmp) / 'wcag-report.md').exists())

    def test_wcag_version_specific_real_scanner_baselines_keep_selected_version_in_citations(self) -> None:
        baseline = self.regression_snapshot['wcag_version_baseline']
        fixture_name = baseline['fixture']
        rule_id = baseline['rule_id']
        for version in baseline['versions']:
            with self.subTest(wcag_version=version), tempfile.TemporaryDirectory() as tmp:
                report, _ = self._run_audit(fixture_name, tmp, wcag_version=version)
                findings = [entry for entry in report['findings'] if entry['rule_id'] == rule_id]
                self.assertTrue(findings)
                expected_token = f'/WCAG{version.replace(".", "")}/'
                urls = [citation['url'] for citation in findings[0].get('citations', [])]
                self.assertTrue(any(expected_token in url for url in urls))

    def test_wcag22_manual_review_baseline_from_secondary_manifest(self) -> None:
        baseline = self.baselines['version_baseline']
        fixture_name = baseline['fixture']
        for wcag_version in baseline['versions']:
            with self.subTest(wcag_version=wcag_version), tempfile.TemporaryDirectory() as tmp:
                report, _ = self._run_audit(fixture_name, tmp, wcag_version=wcag_version)
                self.assertEqual(report['standard']['wcag_version'], wcag_version)
                manual_rules = [
                    item['rule_id']
                    for item in report['findings']
                    if item['rule_id'].startswith('wcag22-manual-')
                ]
                if wcag_version == '2.2':
                    self.assertGreaterEqual(len(manual_rules), baseline['wcag22_manual_minimum'])
                else:
                    self.assertEqual(manual_rules, [])

    def test_realistic_sample_real_scanner_assertions(self) -> None:
        fixture_name = 'realistic-mixed-findings.html'
        expected_rules = {'image-alt', 'button-name', 'list', 'link-name'}
        with tempfile.TemporaryDirectory() as tmp:
            report, _ = self._run_audit(fixture_name, tmp, wcag_version='2.2', execution_mode='apply-fixes')
            rules = {entry['rule_id'] for entry in report['findings']}
            self.assertTrue(expected_rules & rules)
            self.assertTrue(report['run_meta']['files_modified'])
            self.assertGreaterEqual(report['summary']['manual_required_count'], 1)
            self.assertTrue((Path(tmp) / 'wcag-fixes.diff').exists())
            self.assertTrue((Path(tmp) / 'wcag-fixed-report.snapshot.json').exists())
    def test_apply_fixes_before_after_real_scanner_comparison_reduces_fixable_rule_coverage(self) -> None:
        baseline = self.regression_snapshot['apply_fixes_regression']
        fixture_name = baseline['fixture']
        fixable_rules = set(baseline['fixable_rules'])
        with (
            tempfile.TemporaryDirectory() as before_tmp,
            tempfile.TemporaryDirectory() as apply_tmp,
            tempfile.TemporaryDirectory() as after_tmp,
        ):
            before_report, _ = self._run_audit(fixture_name, before_tmp, execution_mode='suggest-only')
            apply_report, applied_target = self._run_audit(fixture_name, apply_tmp, execution_mode='apply-fixes')
            after_report, _ = self._run_audit(str(applied_target), after_tmp, execution_mode='suggest-only')

            before_rules = {entry['rule_id'] for entry in before_report['findings']} & fixable_rules
            after_rules = {entry['rule_id'] for entry in after_report['findings']} & fixable_rules

            self.assertTrue(before_rules)
            self.assertLess(len(after_rules), len(before_rules))
            self.assertTrue(apply_report['run_meta']['files_modified'])
            self.assertTrue((Path(apply_tmp) / 'wcag-fixes.diff').exists())
            self.assertTrue((Path(apply_tmp) / 'wcag-fixed-report.snapshot.json').exists())

    def test_real_scanner_regression_snapshot_coverage(self) -> None:
        for case in self.baselines['regression_snapshot']:
            fixture_name = case['fixture']
            with self.subTest(fixture=fixture_name), tempfile.TemporaryDirectory() as tmp:
                report, _ = self._run_audit(fixture_name, tmp)
                tools = report['run_meta']['tools']
                self.assertEqual(tools['axe'], 'ok')
                if case.get('allow_lighthouse_error'):
                    self.assertIn(tools['lighthouse'], {'ok', 'error'})
                else:
                    self.assertEqual(tools['lighthouse'], 'ok')
                self.assertGreaterEqual(len(report['findings']), case['minimum_findings'])
                self.assertIn('summary', report)
                self.assertIn('fixes', report)


if __name__ == '__main__':
    unittest.main()


