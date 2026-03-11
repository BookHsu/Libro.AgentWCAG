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


@unittest.skipUnless(os.environ.get('LIBRO_RUN_REAL_SCANNERS') == '1' and shutil.which('npx'), 'real scanner integration disabled')
class RealScannerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.fixture_root = cls.repo_root / 'skills' / 'libro-agent-wcag' / 'scripts' / 'tests' / 'fixtures'

    def test_run_accessibility_audit_executes_real_scanners_on_fixture_matrix(self) -> None:
        matrix = [
            ('missing-alt.html', {'image-alt'}),
            ('empty-link-viewport.html', {'link-name', 'meta-viewport'}),
        ]
        for fixture_name, expected_rules in matrix:
            with self.subTest(fixture=fixture_name), tempfile.TemporaryDirectory() as tmp:
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
                    ],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                report = json.loads((Path(tmp) / 'wcag-report.json').read_text(encoding='utf-8'))
                rules = {item['rule_id'] for item in report['findings']}
                self.assertTrue(expected_rules & rules)
                self.assertTrue((Path(tmp) / 'wcag-report.md').exists())


if __name__ == '__main__':
    unittest.main()
