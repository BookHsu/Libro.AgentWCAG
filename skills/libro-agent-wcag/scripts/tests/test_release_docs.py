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
            self.repo_root / 'docs' / 'release' / 'ga-definition.md',
            self.repo_root / 'docs' / 'release' / 'ga-release-workflow.md',
            self.repo_root / 'docs' / 'release' / 'rollback-playbook.md',
            self.repo_root / 'docs' / 'release' / 'release-note-template.md',
            self.repo_root / 'docs' / 'release' / 'hotfix-release-note-template.md',
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
        self.assertIn('package-release.py', content)
        self.assertIn('libro-agent-wcag-<version>-all-in-one.zip', content)
        self.assertIn('libro-agent-wcag-<version>-sha256sums.txt', content)
        self.assertIn('install-latest.ps1', content)
        self.assertIn('run-release-adoption-smoke.py', content)
        self.assertIn('docs/release/ga-release-workflow.md', content)
        self.assertIn('docs/release/ga-definition.md', content)
        self.assertIn('docs/release/rollback-playbook.md', content)
        self.assertIn('doctor-agent.py --verify-manifest-integrity', content)
        self.assertIn('Release-consumer shortest path', content)
        self.assertIn('Release-consumer quickstart', content)
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
        self.assertIn('package-release.py', content)
        self.assertIn('sha256sums.txt', content)
        self.assertIn('release-note-template.md', content)
        self.assertIn('hotfix-release-note-template.md', content)
        self.assertIn('Post-Publish Verification', content)

    def test_adoption_smoke_guide_covers_version_consistency_outputs(self) -> None:
        content = (self.repo_root / 'docs' / 'release' / 'adoption-smoke-guide.md').read_text(encoding='utf-8')
        self.assertIn('version_consistency.verified = true', content)
        self.assertIn('wcag-report.sample.json', content)
        self.assertIn('source_revision', content)
        self.assertIn('package-release.py', content)
        self.assertIn('latest-release.json', content)
        self.assertIn('install-latest.ps1', content)
        self.assertIn('smoke-summary.json', content)
        self.assertIn('Repo-native smoke vs release-consumer smoke', content)

    def test_supported_environments_document_clean_release_consumer_requirements(self) -> None:
        content = (self.repo_root / 'docs' / 'release' / 'supported-environments.md').read_text(encoding='utf-8')
        self.assertIn('Windows', content)
        self.assertIn('macOS', content)
        self.assertIn('Linux', content)
        self.assertIn('temporary-directory write access', content)

    def test_ga_and_rollback_docs_define_operator_contracts(self) -> None:
        ga_definition = (self.repo_root / 'docs' / 'release' / 'ga-definition.md').read_text(encoding='utf-8')
        ga_workflow = (self.repo_root / 'docs' / 'release' / 'ga-release-workflow.md').read_text(encoding='utf-8')
        rollback = (self.repo_root / 'docs' / 'release' / 'rollback-playbook.md').read_text(encoding='utf-8')
        self.assertIn('GA Quality Gates', ga_definition)
        self.assertIn('Blocker', ga_definition)
        self.assertIn('there is no separate pre-announcement window', ga_definition)
        self.assertIn('validate', ga_workflow)
        self.assertIn('clean-release-smoke', ga_workflow)
        self.assertIn('Release title format', ga_workflow)
        self.assertIn('checksum verification guidance', ga_workflow)
        self.assertIn('Version Bump Flow', ga_workflow)
        self.assertIn('Post-Publish Verification', ga_workflow)
        self.assertIn('release-note-template.md', ga_workflow)
        self.assertIn('hotfix-release-note-template.md', ga_workflow)
        self.assertIn('Never rewrite or force-move an existing published tag.', rollback)
        self.assertIn('withdrawn/unsafe for new installs', rollback)
        self.assertIn('hotfix', rollback.lower())

    def test_release_note_templates_cover_install_and_checksum_sections(self) -> None:
        release_template = (self.repo_root / 'docs' / 'release' / 'release-note-template.md').read_text(encoding='utf-8')
        hotfix_template = (self.repo_root / 'docs' / 'release' / 'hotfix-release-note-template.md').read_text(encoding='utf-8')
        self.assertIn('## Highlights', release_template)
        self.assertIn('## Checksum Verification', release_template)
        self.assertIn('install-latest.ps1', release_template)
        self.assertIn('## Replaces', hotfix_template)
        self.assertIn('## User Action Required', hotfix_template)
        self.assertIn('doctor-agent.py --agent codex --verify-manifest-integrity', hotfix_template)

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
