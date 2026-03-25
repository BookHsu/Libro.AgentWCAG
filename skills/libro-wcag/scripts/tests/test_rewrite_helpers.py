#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from rewrite_helpers import (
    ensure_css_property,
    ensure_js_guard,
    ensure_nextjs_image_alt,
    ensure_nextjs_layout_lang,
    ensure_react_img_alt,
    ensure_vue_img_alt,
    replace_first,
)


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

    def test_ensure_react_img_alt_patches_first_jsx_img(self) -> None:
        jsx = '<div><img className="hero" src="/hero.png" /></div>'
        updated, changed = ensure_react_img_alt(jsx)
        self.assertTrue(changed)
        self.assertIn('alt=""', updated)

    def test_ensure_vue_img_alt_respects_bound_alt(self) -> None:
        vue = '<template><img :alt="heroAlt" src="/hero.png" /></template>'
        updated, changed = ensure_vue_img_alt(vue)
        self.assertFalse(changed)
        self.assertEqual(updated, vue)

    def test_ensure_nextjs_layout_lang_supports_html_component(self) -> None:
        source = '<Html><Head /></Html>'
        updated, changed = ensure_nextjs_layout_lang(source)
        self.assertTrue(changed)
        self.assertIn('<Html lang="en">', updated)

    def test_ensure_nextjs_image_alt_updates_image_component(self) -> None:
        source = '<Image src="/hero.png" width={1200} height={800} />'
        updated, changed = ensure_nextjs_image_alt(source)
        self.assertTrue(changed)
        self.assertIn('alt=""', updated)


if __name__ == '__main__':
    unittest.main()
