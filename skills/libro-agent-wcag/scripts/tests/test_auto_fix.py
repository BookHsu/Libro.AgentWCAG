#!/usr/bin/env python3

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from auto_fix import apply_report_fixes, target_to_local_path
from wcag_workflow import normalize_report, resolve_contract


class AutoFixTests(unittest.TestCase):
    def test_target_to_local_path_supports_local_and_file_uri(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'missing-alt.html'
        self.assertEqual(target_to_local_path(str(fixture)), fixture.resolve())
        self.assertEqual(target_to_local_path(fixture.resolve().as_uri()), fixture.resolve())
        self.assertIsNone(target_to_local_path('https://example.com'))

    def test_apply_report_fixes_updates_local_html_and_diff(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'missing-lang-button-label.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'html-has-lang', 'impact': 'moderate', 'description': 'html must have lang', 'nodes': [{'target': ['html']}]},
                    {'id': 'button-name', 'impact': 'serious', 'description': 'Buttons need names', 'nodes': [{'target': ['button.icon-only']}]},
                    {'id': 'label', 'impact': 'serious', 'description': 'Inputs need labels', 'nodes': [{'target': ['input#email']}]},
                ]
            }
            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            updated_html = working.read_text(encoding='utf-8')
            self.assertIn('lang="en"', updated_html)
            self.assertIn('aria-label="Button"', updated_html)
            self.assertIn('aria-label="Email address"', updated_html)
            self.assertTrue(diff_text.startswith('---'))
            self.assertTrue(updated_report['run_meta']['files_modified'])
            self.assertEqual(updated_report['run_meta']['modification_owner'], 'core-workflow')
            self.assertEqual(updated_report['findings'][0]['verification_status'], 'diff-generated')
            self.assertTrue(updated_report['run_meta']['diff_artifacts'])
            self.assertGreaterEqual(updated_report['summary']['fixed_findings'], 1)
            self.assertTrue(updated_report['summary']['diff_summary'])

    def test_apply_report_fixes_supports_link_name_and_meta_viewport(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'empty-link-viewport.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'link-name', 'impact': 'serious', 'description': 'Links need names', 'nodes': [{'target': ['a.cta']}]},
                    {'id': 'meta-viewport', 'impact': 'moderate', 'description': 'Viewport must allow zoom', 'nodes': [{'target': ['meta[name="viewport"]']}]},
                ]
            }
            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            updated_html = working.read_text(encoding='utf-8')
            self.assertIn('aria-label="Link"', updated_html)
            self.assertIn('content="width=device-width, initial-scale=1"', updated_html)
            self.assertIn('aria-label="Link"', diff_text)
            self.assertIn('width=device-width, initial-scale=1', diff_text)
            self.assertEqual(updated_report['summary']['remediation_lifecycle']['implemented'], 2)

    def test_apply_report_fixes_is_idempotent(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'empty-link-viewport.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'link-name', 'impact': 'serious', 'description': 'Links need names', 'nodes': [{'target': ['a.cta']}]},
                    {'id': 'meta-viewport', 'impact': 'moderate', 'description': 'Viewport must allow zoom', 'nodes': [{'target': ['meta[name="viewport"]']}]},
                ]
            }
            first_report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, first_diff = apply_report_fixes(working, first_report)
            second_report, second_diff = apply_report_fixes(working, updated_report)
            self.assertTrue(first_diff)
            self.assertEqual(second_diff, '')
            self.assertIn('No safe auto-fix changes were applied', ' '.join(second_report['run_meta']['notes']))

    def test_apply_report_fixes_noop_when_no_supported_rules_match(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'missing-alt.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'color-contrast', 'impact': 'serious', 'description': 'Contrast issue', 'nodes': [{'target': ['.hero']}]},
                ]
            }
            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            self.assertEqual(diff_text, '')
            self.assertFalse(updated_report['run_meta']['files_modified'])
            self.assertIn('No safe auto-fix changes were applied', ' '.join(updated_report['run_meta']['notes']))


if __name__ == '__main__':
    unittest.main()
