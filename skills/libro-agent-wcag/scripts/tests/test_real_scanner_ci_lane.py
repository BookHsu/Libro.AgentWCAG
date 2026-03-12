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
        cls.reusable_workflow = cls.repo_root / '.github' / 'workflows' / 'reusable-real-scanner-lane.yml'
        cls.main_workflow = cls.repo_root / '.github' / 'workflows' / 'test.yml'
        cls.sample_workflow = cls.repo_root / 'docs' / 'release' / 'github-actions-wcag-ci-sample.yml'
        cls.ci_lane_doc = cls.repo_root / 'docs' / 'release' / 'real-scanner-ci-lane.md'

    def test_reusable_lane_defines_live_and_fallback_matrix_contract(self) -> None:
        content = self.reusable_workflow.read_text(encoding='utf-8')
        self.assertIn('workflow_call', content)
        self.assertIn('enabled:', content)
        self.assertIn('lane-mode: [live, fallback]', content)
        self.assertIn('normalized-summary.live.json', content)
        self.assertIn('normalized-summary.fallback.json', content)
        self.assertIn('capability-negotiation.json', content)
        self.assertIn('raw/scanner-unavailable.log', content)

    def test_workflows_call_reusable_lane(self) -> None:
        main_content = self.main_workflow.read_text(encoding='utf-8')
        sample_content = self.sample_workflow.read_text(encoding='utf-8')
        self.assertIn('uses: ./.github/workflows/reusable-real-scanner-lane.yml', main_content)
        self.assertIn('uses: ./.github/workflows/reusable-real-scanner-lane.yml', sample_content)
        self.assertIn("LIBRO_RUN_REAL_SCANNERS == '1'", main_content)

    def test_local_skip_summary_contract_matches_ci_fallback_message(self) -> None:
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

    def test_ci_lane_documentation_covers_evidence_handoff(self) -> None:
        content = self.ci_lane_doc.read_text(encoding='utf-8')
        self.assertIn('Evidence artifact conventions', content)
        self.assertIn('raw/axe.version.log', content)
        self.assertIn('normalized-summary.live.json', content)
        self.assertIn('capability-negotiation.json', content)
        self.assertIn('Triage handoff references', content)


if __name__ == '__main__':
    unittest.main()
