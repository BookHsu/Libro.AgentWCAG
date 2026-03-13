#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


class ReleaseDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]

    def test_release_docs_exist(self) -> None:
        expected_files = [
            self.repo_root / 'CHANGELOG.md',
            self.repo_root / 'docs' / 'release' / 'release-checklist.md',
            self.repo_root / 'docs' / 'release' / 'release-notes-workflow.md',
            self.repo_root / 'docs' / 'release' / 'supported-environments.md',
            self.repo_root / 'docs' / 'release' / 'first-run-smoke.md',
            self.repo_root / 'docs' / 'release' / 'apply-fixes-scope.md',
            self.repo_root / 'docs' / 'release' / 'demo-package-walkthrough.md',
            self.repo_root / 'docs' / 'release' / 'prompt-invocation-templates.md',
            self.repo_root / 'docs' / 'release' / 'troubleshooting-intake.md',
            self.repo_root / 'docs' / 'release' / 'resilient-run-patterns.md',
            self.repo_root / 'docs' / 'release' / 'release-packaging-extras-placement.md',
            self.repo_root / 'docs' / 'release' / 'real-scanner-ci-lane.md',
            self.repo_root / 'docs' / 'release' / 'baseline-debt-lifecycle.md',
            self.repo_root / 'docs' / 'release' / 'risk-calibration.md',
            self.repo_root / 'docs' / 'release' / 'replay-verification-lane.md',
            self.repo_root / 'docs' / 'release' / 'provenance-verification.md',
            self.repo_root / 'docs' / 'release' / 'install-integrity-verification.md',
            self.repo_root / 'docs' / 'policy-bundles' / 'strict-web-app.json',
            self.repo_root / 'docs' / 'policy-bundles' / 'legacy-content.json',
            self.repo_root / 'docs' / 'policy-bundles' / 'marketing-site.json',
            self.repo_root / '.github' / 'ISSUE_TEMPLATE' / 'installation-failure.yml',
            self.repo_root / '.github' / 'ISSUE_TEMPLATE' / 'remediation-mismatch.yml',
        ]
        for file_path in expected_files:
            self.assertTrue(file_path.exists(), f'Missing file: {file_path}')

    def test_realistic_validation_docs_and_assets_exist(self) -> None:
        expected_files = [
            self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'mixed-findings.html',
            self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'scanner-fixtures' / 'axe.mock.json',
            self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'scanner-fixtures' / 'lighthouse.mock.json',
            self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'artifacts' / 'smoke-summary.json',
            self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'known-limitations.md',
        ]
        for file_path in expected_files:
            self.assertTrue(file_path.exists(), f'Missing file: {file_path}')


    def test_policy_bundle_lock_metadata_is_present_and_hash_stable(self) -> None:
        required_order = [
            'name',
            'description',
            'bundle_version',
            'updated_at',
            'fail_on',
            'include_rules',
            'ignore_rules',
            'bundle_hash',
        ]
        for bundle_path in sorted((self.repo_root / 'docs' / 'policy-bundles').glob('*.json')):
            payload = json.loads(bundle_path.read_text(encoding='utf-8'))
            self.assertEqual(list(payload.keys()), required_order)
            self.assertRegex(payload['bundle_version'], r'^\d+\.\d+\.\d+$')
            self.assertRegex(payload['updated_at'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
            self.assertRegex(payload['bundle_hash'], r'^[0-9a-f]{64}$')

            material = {key: payload[key] for key in required_order if key != 'bundle_hash'}
            canonical = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            expected = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
            self.assertEqual(payload['bundle_hash'], expected)

    def test_readme_links_release_readiness(self) -> None:
        content = (self.repo_root / 'README.md').read_text(encoding='utf-8')
        self.assertIn('## Release readiness', content)
        self.assertIn('docs/release/release-checklist.md', content)
        self.assertIn('docs/release/first-run-smoke.md', content)
        self.assertIn('docs/release/apply-fixes-scope.md', content)
        self.assertIn('docs/release/demo-package-walkthrough.md', content)
        self.assertIn('docs/release/prompt-invocation-templates.md', content)
        self.assertIn('docs/release/troubleshooting-intake.md', content)
        self.assertIn('docs/release/resilient-run-patterns.md', content)
        self.assertIn('docs/release/real-scanner-ci-lane.md', content)
        self.assertIn('docs/release/baseline-debt-lifecycle.md', content)
        self.assertIn('docs/release/risk-calibration.md', content)
        self.assertIn('docs/release/replay-verification-lane.md', content)
        self.assertIn('docs/release/provenance-verification.md', content)
        self.assertIn('docs/release/install-integrity-verification.md', content)
        self.assertIn('docs/policy-bundles/', content)


if __name__ == '__main__':
    unittest.main()

