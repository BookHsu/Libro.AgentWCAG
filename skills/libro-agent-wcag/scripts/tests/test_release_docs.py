#!/usr/bin/env python3

from __future__ import annotations

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
        ]
        for file_path in expected_files:
            self.assertTrue(file_path.exists(), f'Missing file: {file_path}')

    def test_readme_links_release_readiness(self) -> None:
        content = (self.repo_root / 'README.md').read_text(encoding='utf-8')
        self.assertIn('## Release readiness', content)
        self.assertIn('docs/release/release-checklist.md', content)
        self.assertIn('docs/release/first-run-smoke.md', content)


if __name__ == '__main__':
    unittest.main()
