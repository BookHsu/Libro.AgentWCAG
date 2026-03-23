#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


class ReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.workflow_path = cls.repo_root / '.github' / 'workflows' / 'release.yml'

    def test_release_workflow_has_tag_push_and_manual_trigger(self) -> None:
        content = self.workflow_path.read_text(encoding='utf-8')
        self.assertIn('name: Release', content)
        self.assertIn('push:', content)
        self.assertIn('tags:', content)
        self.assertIn('- "v*"', content)
        self.assertIn('workflow_dispatch:', content)
        self.assertIn('release_tag:', content)

    def test_release_workflow_enforces_validate_package_smoke_publish_gate_order(self) -> None:
        content = self.workflow_path.read_text(encoding='utf-8')
        self.assertIn('validate:', content)
        self.assertIn('package-release:', content)
        self.assertIn('clean-release-smoke:', content)
        self.assertIn('publish-release:', content)
        self.assertIn('needs:\n      - validate', content)
        self.assertIn('needs:\n      - package-release', content)
        self.assertIn('      - clean-release-smoke', content)
        self.assertIn('python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"', content)
        self.assertIn('python scripts/package-release.py --output-dir "${{ env.LIBRO_RELEASE_ARTIFACT_DIR }}" --overwrite', content)
        self.assertIn('python scripts/run-release-adoption-smoke.py', content)

    def test_release_workflow_uploads_retained_artifacts_and_publishes_assets(self) -> None:
        content = self.workflow_path.read_text(encoding='utf-8')
        self.assertIn('actions/upload-artifact@v4', content)
        self.assertIn('actions/download-artifact@v4', content)
        self.assertIn('retention-days: ${{ github.event.inputs.retention_days || env.LIBRO_RELEASE_RETENTION_DAYS }}', content)
        self.assertIn('softprops/action-gh-release@v2', content)
        self.assertIn('fail_on_unmatched_files: true', content)
        self.assertIn('${{ env.LIBRO_RELEASE_ARTIFACT_DIR }}/*', content)

    def test_release_workflow_does_not_modify_real_scanner_required_lane(self) -> None:
        content = self.workflow_path.read_text(encoding='utf-8')
        self.assertNotIn('libro-agent-wcag-real-scanner:', content)
        self.assertNotIn('required check name', content.lower())


if __name__ == '__main__':
    unittest.main()
