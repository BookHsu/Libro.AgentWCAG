#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from rewrite_helpers import ensure_css_property, ensure_js_guard, replace_first


class RewriteHelpersTests(unittest.TestCase):
    def test_replace_first_updates_only_first_match(self) -> None:
        updated, changed = replace_first(r'button', 'link', 'button button')
        self.assertTrue(changed)
        self.assertEqual(updated, 'link button')

    def test_ensure_css_property_adds_missing_block(self) -> None:
        updated, changed = ensure_css_property('', '.focus-ring', 'outline', '2px solid #005fcc')
        self.assertTrue(changed)
        self.assertIn('.focus-ring', updated)
        self.assertIn('outline: 2px solid #005fcc;', updated)

    def test_ensure_css_property_updates_existing_value(self) -> None:
        css = '.focus-ring {\n  outline: none;\n}\n'
        updated, changed = ensure_css_property(css, '.focus-ring', 'outline', '2px solid #005fcc')
        self.assertTrue(changed)
        self.assertIn('outline: 2px solid #005fcc;', updated)

    def test_ensure_js_guard_prefixes_guard_once(self) -> None:
        guarded, changed = ensure_js_guard('console.log("ready");\n', '__hasTarget', 'document.querySelector("main")')
        self.assertTrue(changed)
        self.assertIn('const __hasTarget = document.querySelector("main")', guarded)
        second, changed_again = ensure_js_guard(guarded, '__hasTarget', 'document.querySelector("main")')
        self.assertFalse(changed_again)
        self.assertEqual(second, guarded)


if __name__ == '__main__':
    unittest.main()
