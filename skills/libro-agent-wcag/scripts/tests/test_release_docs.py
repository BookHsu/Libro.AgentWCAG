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
            self.repo_root / 'docs' / 'release' / 'release-playbook.md',
            self.repo_root / 'docs' / 'release' / 'supported-environments.md',
            self.repo_root / 'docs' / 'release' / 'adoption-smoke-guide.md',
            self.repo_root / 'docs' / 'release' / 'apply-fixes-scope.md',
            self.repo_root / 'docs' / 'release' / 'prompt-invocation-templates.md',
            self.repo_root / 'docs' / 'release' / 'resilient-run-patterns.md',
            self.repo_root / 'docs' / 'release' / 'real-scanner-ci-lane.md',
            self.repo_root / 'docs' / 'release' / 'baseline-governance.md',
            self.repo_root / 'docs' / 'release' / 'advanced-ci-gates.md',
            self.repo_root / 'docs' / 'examples' / 'ci' / 'github-actions-wcag-ci-sample.yml',
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
            self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'artifacts' / 'install-manifest.sample.json',
            self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'artifacts' / 'doctor.sample.json',
            self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'artifacts' / 'artifact-manifest.sample.json',
            self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'artifacts' / 'wcag-report.sample.sarif',
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
        self.assertIn('product_version', content)
        self.assertIn('source_revision', content)
        self.assertIn('docs/release/release-playbook.md', content)
        self.assertIn('docs/release/adoption-smoke-guide.md', content)
        self.assertIn('docs/release/apply-fixes-scope.md', content)
        self.assertIn('docs/release/prompt-invocation-templates.md', content)
        self.assertIn('docs/release/resilient-run-patterns.md', content)
        self.assertIn('docs/examples/ci/github-actions-wcag-ci-sample.yml', content)
        self.assertIn('docs/release/real-scanner-ci-lane.md', content)
        self.assertIn('docs/release/baseline-governance.md', content)
        self.assertIn('docs/release/advanced-ci-gates.md', content)
        self.assertIn('docs/policy-bundles/', content)

    def test_release_playbook_documents_version_and_provenance_sources(self) -> None:
        content = (self.repo_root / 'docs' / 'release' / 'release-playbook.md').read_text(encoding='utf-8')
        self.assertIn('pyproject.toml', content)
        self.assertIn('LIBRO_AGENTWCAG_SOURCE_REVISION', content)
        self.assertIn('fail fast', content.lower())

    def test_adoption_smoke_guide_covers_version_consistency_outputs(self) -> None:
        content = (self.repo_root / 'docs' / 'release' / 'adoption-smoke-guide.md').read_text(encoding='utf-8')
        self.assertIn('version_consistency.verified = true', content)
        self.assertIn('wcag-report.sample.json', content)
        self.assertIn('source_revision', content)

    def test_realistic_sample_artifacts_capture_provenance_metadata(self) -> None:
        smoke = json.loads(
            (self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'artifacts' / 'smoke-summary.json').read_text(
                encoding='utf-8'
            )
        )
        doctor = json.loads(
            (self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'artifacts' / 'doctor.sample.json').read_text(
                encoding='utf-8-sig'
            )
        )
        report = json.loads(
            (self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'artifacts' / 'wcag-report.sample.json').read_text(
                encoding='utf-8'
            )
        )
        self.assertEqual(smoke['installed_product_version'], '0.1.0')
        self.assertTrue(smoke['doctor_version_consistency_verified'])
        self.assertEqual(doctor['installed_product']['product_version'], '0.1.0')
        self.assertTrue(doctor['version_consistency']['verified'])
        self.assertEqual(report['run_meta']['product']['product_version'], '0.1.0')


if __name__ == '__main__':
    unittest.main()
