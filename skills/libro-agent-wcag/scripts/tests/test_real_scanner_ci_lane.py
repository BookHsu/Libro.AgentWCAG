#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class RealScannerCiLaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.real_scanner_workflow = cls.repo_root / '.github' / 'workflows' / 'libro-agent-wcag-real-scanner.yml'
        cls.main_workflow = cls.repo_root / '.github' / 'workflows' / 'test.yml'
        cls.sample_workflow = cls.repo_root / 'docs' / 'examples' / 'ci' / 'github-actions-wcag-ci-sample.yml'
        cls.ci_lane_doc = cls.repo_root / 'docs' / 'release' / 'real-scanner-ci-lane.md'

    def test_real_scanner_workflow_defines_required_gate_contract(self) -> None:
        content = self.real_scanner_workflow.read_text(encoding='utf-8')
        self.assertIn('name: libro-agent-wcag-real-scanner', content)
        self.assertIn('pull_request:', content)
        self.assertIn('workflow_dispatch:', content)
        self.assertIn('libro-agent-wcag-real-scanner:', content)
        self.assertIn('runs-on: ubuntu-latest', content)
        self.assertIn('retention-days: 14', content)
        self.assertIn('docs/testing/realistic-sample/mixed-findings.html', content)
        self.assertIn('wcag-report.sarif', content)
        self.assertIn('if: always()', content)
        self.assertNotIn('workflow_call', content)
        self.assertNotIn('lane-mode: [live, fallback]', content)
        self.assertNotIn('normalized-summary.fallback.json', content)

    def test_main_workflow_does_not_wrap_or_rename_real_scanner_gate(self) -> None:
        main_content = self.main_workflow.read_text(encoding='utf-8')
        sample_content = self.sample_workflow.read_text(encoding='utf-8')
        self.assertNotIn('reusable-real-scanner-lane.yml', main_content)
        self.assertNotIn('reusable-real-scanner-lane.yml', sample_content)
        self.assertNotIn('real-scanner-lane:', main_content)

    def test_local_skip_summary_contract_still_matches_expected_scanner_capability_shape(self) -> None:
        output_dir = self.repo_root / 'out-test-invalid' / 'm28-local-summary'
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
            '--target',
            'docs/testing/realistic-sample/mixed-findings.html',
            '--execution-mode',
            'suggest-only',
            '--output-language',
            'en',
            '--output-dir',
            str(output_dir.resolve()),
            '--skip-axe',
            '--skip-lighthouse',
            '--summary-only',
        ]
        completed = subprocess.run(
            command,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        compact = json.loads(completed.stdout.strip())
        self.assertEqual(
            compact['scanner_capabilities']['unavailable_scanners'],
            ['axe', 'lighthouse'],
        )
        payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
        preflight_checks = payload['run_meta']['preflight']['checks']
        self.assertEqual(preflight_checks[0]['status'], 'skipped')
        self.assertEqual(
            preflight_checks[0]['message'],
            'scanner tooling preflight skipped due to mock or skip flags',
        )

    def test_ci_lane_documentation_covers_required_check_and_artifacts(self) -> None:
        content = self.ci_lane_doc.read_text(encoding='utf-8')
        self.assertIn('Workflow contract', content)
        self.assertIn('libro-agent-wcag-real-scanner', content)
        self.assertIn('Required check name for branch protection', content)
        self.assertIn('ubuntu-latest', content)
        self.assertIn('retain artifacts for `14` days', content)
        self.assertIn('live/wcag-report.sarif', content)
        self.assertIn('fails immediately', content)


if __name__ == '__main__':
    unittest.main()
