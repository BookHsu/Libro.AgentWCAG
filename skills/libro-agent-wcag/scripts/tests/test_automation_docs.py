#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


class AutomationDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]

    def test_automation_spec_prioritizes_test_development(self) -> None:
        content = (self.repo_root / 'docs' / 'automations' / 'test-plan-automation.md').read_text(encoding='utf-8')
        self.assertIn('The automation must prefer writing tests over writing documentation.', content)
        self.assertIn('## Automation Targets', content)
        self.assertIn('## Manual-Only Categories', content)
        self.assertIn('adds a new automated test', content)
        self.assertIn('A run is not successful if it only rewrites documentation', content)

    def test_review_policy_rejects_documentation_only_when_automation_gap_exists(self) -> None:
        content = (self.repo_root / 'docs' / 'automations' / 'test-plan-review-policy.md').read_text(encoding='utf-8')
        self.assertIn('added or strengthened actual test code', content)
        self.assertIn('added only documentation while automatable gaps still exist', content)
        self.assertIn('Automatable categories are not left as `Scripted Manual`', content)


if __name__ == '__main__':
    unittest.main()
