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
    def test_snapshot_for_missing_alt_fixture_matches_expected_output(self) -> None:
        snapshots = Path(__file__).parent / 'snapshots'
        expected_json = json.loads((snapshots / 'missing-alt.report.json').read_text(encoding='utf-8'))
        expected_md = (snapshots / 'missing-alt.report.md').read_text(encoding='utf-8')
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


@unittest.skipUnless(os.environ.get('LIBRO_RUN_REAL_SCANNERS') == '1' and shutil.which('npx'), 'real scanner integration disabled')
class RealScannerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]

    def test_run_accessibility_audit_executes_real_scanners_on_fixture(self) -> None:
        fixture = self.repo_root / 'skills' / 'libro-agent-wcag' / 'scripts' / 'tests' / 'fixtures' / 'missing-alt.html'
        with tempfile.TemporaryDirectory() as tmp:
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
            self.assertGreaterEqual(report['summary']['total_findings'], 1)
            self.assertTrue(any(item['rule_id'] == 'image-alt' for item in report['findings']))
            self.assertTrue((Path(tmp) / 'wcag-report.md').exists())


if __name__ == '__main__':
    unittest.main()
