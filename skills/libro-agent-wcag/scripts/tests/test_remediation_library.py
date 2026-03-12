#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from remediation_library import get_framework_strategy, get_strategy


class RemediationLibraryTests(unittest.TestCase):
    def test_specific_rule_strategy_overrides_defaults(self) -> None:
        strategy = get_strategy("image-alt")
        self.assertEqual(strategy["priority"], "high")
        self.assertTrue(strategy["auto_fix_supported"])

    def test_new_safe_rules_are_marked_auto_fix_supported(self) -> None:
        for rule_id in ('area-alt', 'meta-refresh', 'html-xml-lang-mismatch', 'valid-lang', 'aria-toggle-field-name', 'aria-tooltip-name', 'aria-progressbar-name', 'aria-meter-name', 'document-title', 'list', 'listitem', 'table-fake-caption'):
            with self.subTest(rule_id=rule_id):
                strategy = get_strategy(rule_id)
                self.assertTrue(strategy['auto_fix_supported'])
                self.assertEqual(strategy['confidence'], 'high')

    def test_unknown_rule_uses_default_strategy(self) -> None:
        strategy = get_strategy("unknown-rule")
        self.assertEqual(strategy["confidence"], "medium")
        self.assertFalse(strategy["auto_fix_supported"])
        self.assertIn("react", strategy["framework_hints"])

    def test_assisted_rules_expose_steps_and_verification_rules(self) -> None:
        for rule_id in ("duplicate-id-aria", "heading-order", "presentation-role-conflict", "region", "skip-link", "tabindex", "nested-interactive"):
            with self.subTest(rule_id=rule_id):
                strategy = get_strategy(rule_id)
                self.assertFalse(strategy["auto_fix_supported"])
                self.assertGreaterEqual(len(strategy["assisted_steps"]), 2)
                self.assertGreaterEqual(len(strategy["verification_rules"]), 2)

    def test_framework_strategies_return_rule_specific_guidance(self) -> None:
        self.assertIn('JSX rewrite helper', get_framework_strategy('image-alt', 'react'))
        self.assertIn('layout.tsx', get_framework_strategy('html-has-lang', 'nextjs'))

    def test_framework_strategy_falls_back_to_hints(self) -> None:
        fallback = get_framework_strategy('unknown-rule', 'vue')
        self.assertIn('templates', fallback)


if __name__ == "__main__":
    unittest.main()
