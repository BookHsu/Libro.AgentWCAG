#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


class AutomationDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]

    def test_automation_spec_is_testing_lane_only(self) -> None:
        content = (self.repo_root / 'docs' / 'automations' / 'test-plan-automation.md').read_text(encoding='utf-8')
        self.assertIn('## Testing Lane Only', content)
        self.assertIn('It must not take ownership of feature development.', content)
        self.assertIn('commit and push completed testing increments', content)
        self.assertIn('take ownership of feature development', content)

    def test_review_policy_rejects_feature_development_in_testing_lane(self) -> None:
        content = (self.repo_root / 'docs' / 'automations' / 'test-plan-review-policy.md').read_text(encoding='utf-8')
        self.assertIn('The automation stayed inside the testing lane.', content)
        self.assertIn('did not take ownership of product feature development', content)
        self.assertIn('took ownership of feature development instead of staying in the testing lane', content)


if __name__ == '__main__':
    unittest.main()
