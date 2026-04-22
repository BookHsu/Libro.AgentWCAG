#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


class ReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.workflow_path = cls.repo_root / '.github' / 'workflows' / 'release.yml'
        cls.publish_npm_workflow_path = cls.repo_root / '.github' / 'workflows' / 'publish-npm.yml'

    def test_release_workflow_is_tag_only_and_does_not_publish_npm_directly(self) -> None:
        content = self.workflow_path.read_text(encoding='utf-8')
        self.assertIn('name: Release', content)
        self.assertIn('push:', content)
        self.assertIn('tags:', content)
        self.assertIn('- "v*"', content)
        self.assertNotIn('workflow_dispatch:', content)
        self.assertNotIn('publish-npm:', content)

    def test_release_workflow_enforces_validate_package_smoke_publish_gate_order(self) -> None:
        content = self.workflow_path.read_text(encoding='utf-8')
        self.assertIn('validate:', content)
        self.assertIn('package-release:', content)
        self.assertIn('clean-release-smoke:', content)
        self.assertIn('publish-release:', content)
        self.assertIn('needs:\n      - validate', content)
        self.assertIn('needs:\n      - package-release', content)
        self.assertIn('      - clean-release-smoke', content)
        self.assertIn('python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"', content)
        self.assertIn('python scripts/apply-release-version.py --version', content)
        self.assertIn('python scripts/package-release.py --output-dir "${{ env.LIBRO_RELEASE_ARTIFACT_DIR }}" --overwrite', content)
        self.assertIn('python scripts/run-release-adoption-smoke.py', content)

    def test_release_workflow_uploads_retained_artifacts_and_publishes_assets(self) -> None:
        content = self.workflow_path.read_text(encoding='utf-8')
        self.assertIn('actions/upload-artifact@v4', content)
        self.assertIn('actions/download-artifact@v4', content)
        self.assertIn('retention-days: ${{ env.LIBRO_RELEASE_RETENTION_DAYS }}', content)
        self.assertIn('softprops/action-gh-release@v2', content)
        self.assertIn('is_prerelease=${is_prerelease}', content)
        self.assertIn("prerelease: ${{ needs.package-release.outputs.is_prerelease == 'true' }}", content)
        self.assertIn('fail_on_unmatched_files: true', content)
        self.assertIn('${{ env.LIBRO_RELEASE_ARTIFACT_DIR }}/*', content)
        self.assertIn('generate_release_notes: true', content)
        self.assertNotIn('id-token: write', content)
        self.assertNotIn('registry-url: https://registry.npmjs.org', content)
        self.assertNotIn('npm publish', content)

    def test_publish_npm_workflow_uses_oidc_tag_only_and_node24(self) -> None:
        content = self.publish_npm_workflow_path.read_text(encoding='utf-8')
        self.assertIn('name: Publish npm', content)
        self.assertIn('push:', content)
        self.assertIn('tags:', content)
        self.assertIn('- "v*"', content)
        self.assertNotIn('workflow_dispatch:', content)
        self.assertIn('id-token: write', content)
        self.assertIn('contents: read', content)
        self.assertIn('registry-url: https://registry.npmjs.org', content)
        self.assertIn('node-version: "24"', content)
        self.assertIn('python scripts/apply-release-version.py --version', content)
        self.assertIn('python -m pip install pyyaml', content)
        self.assertIn('npm pack', content)
        self.assertIn('npm publish --access public', content)
        self.assertIn('npm_dist_tag=${npm_dist_tag}', content)
        self.assertIn("if: steps.release-meta.outputs.is_prerelease == 'true'", content)
        self.assertIn('npm publish --access public --tag', content)

    def test_publish_npm_workflow_exports_provenance_after_tests(self) -> None:
        content = self.publish_npm_workflow_path.read_text(encoding='utf-8')
        tests_index = content.index('Run automated tests')
        validate_index = content.index('Validate repo skill contract')
        export_index = content.index('Export provenance inputs')
        pack_index = content.index('Pack npm tarball')
        self.assertLess(tests_index, validate_index)
        self.assertLess(validate_index, export_index)
        self.assertLess(export_index, pack_index)

    def test_release_workflow_does_not_modify_real_scanner_required_lane(self) -> None:
        content = self.workflow_path.read_text(encoding='utf-8')
        self.assertNotIn('libro-wcag-real-scanner:', content)
        self.assertNotIn('required check name', content.lower())


if __name__ == '__main__':
    unittest.main()
