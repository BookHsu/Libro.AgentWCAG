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
            self.assertEqual(updated_report['summary']['auto_fixed_count'], updated_report['summary']['fixed_findings'])
            self.assertEqual(updated_report['summary']['manual_required_count'], updated_report['summary']['needs_manual_review'])
            self.assertTrue(updated_report['summary']['diff_summary'])
            self.assertTrue(updated_report['summary']['before_after_targets'])
            self.assertTrue(updated_report['run_meta']['verification_evidence'])
            self.assertTrue(updated_report['fixes'][0]['verification_evidence'])

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

    def test_apply_report_fixes_supports_lang_refresh_and_image_map_rules(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'deep-auto-fix.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'html-xml-lang-mismatch', 'impact': 'moderate', 'description': 'lang and xml:lang should match', 'nodes': [{'target': ['html']}]},
                    {'id': 'valid-lang', 'impact': 'moderate', 'description': 'invalid language code', 'nodes': [{'target': ['p[lang]']}]},
                    {'id': 'meta-refresh', 'impact': 'moderate', 'description': 'refresh should be removed', 'nodes': [{'target': ['meta[http-equiv="refresh"]']}]},
                    {'id': 'input-image-alt', 'impact': 'serious', 'description': 'image input needs alt', 'nodes': [{'target': ['input[type="image"]']}]},
                    {'id': 'area-alt', 'impact': 'serious', 'description': 'area needs alt', 'nodes': [{'target': ['area']}]},
                ]
            }
            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            updated_html = working.read_text(encoding='utf-8')
            self.assertIn('xml:lang="en-US"', updated_html)
            self.assertIn('<p lang="en">', updated_html)
            self.assertNotIn('http-equiv="refresh"', updated_html)
            self.assertIn('<input type="image" src="submit.png" alt="">', updated_html)
            self.assertIn('<area shape="rect" coords="0,0,100,100" href="/promo" alt="">', updated_html)
            self.assertIn('xml:lang', diff_text)
            self.assertIn('http-equiv="refresh"', diff_text)
            self.assertGreaterEqual(updated_report['summary']['remediation_lifecycle']['implemented'], 5)

    def test_apply_report_fixes_supports_document_title_and_aria_name_rules(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'aria-title.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'aria-toggle-field-name', 'impact': 'serious', 'description': 'toggle needs name', 'nodes': [{'target': ['.switch-icon']}]},
                    {'id': 'aria-tooltip-name', 'impact': 'moderate', 'description': 'tooltip needs name', 'nodes': [{'target': ['.tooltip-shell']}]},
                    {'id': 'aria-progressbar-name', 'impact': 'moderate', 'description': 'progressbar needs name', 'nodes': [{'target': ['.progress-shell']}]},
                    {'id': 'aria-meter-name', 'impact': 'moderate', 'description': 'meter needs name', 'nodes': [{'target': ['.meter-shell']}]},
                ]
            }
            lighthouse_data = {
                'audits': {
                    'document-title': {
                        'score': 0,
                        'scoreDisplayMode': 'binary',
                        'title': 'Document has a title',
                        'details': {'items': [{'node': {'selector': 'title'}}]},
                    }
                }
            }
            report = normalize_report(contract, axe_data, lighthouse_data, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            updated_html = working.read_text(encoding='utf-8')
            self.assertIn('<title>Dashboard</title>', updated_html)
            self.assertIn('role="switch" aria-label="Toggle"', updated_html)
            self.assertIn('role="tooltip" aria-label="Tooltip"', updated_html)
            self.assertIn('role="progressbar" aria-label="Progress"', updated_html)
            self.assertIn('role="meter" aria-label="Meter"', updated_html)
            self.assertIn('<title>Dashboard</title>', diff_text)
            self.assertGreaterEqual(updated_report['summary']['remediation_lifecycle']['implemented'], 5)

    def test_apply_report_fixes_supports_aria_and_table_semantic_rules(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'aria-table-auto-fix.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'aria-required-attr', 'impact': 'serious', 'description': 'missing required aria attrs', 'nodes': [{'target': ['.acceptance']}]},
                    {'id': 'aria-valid-attr-value', 'impact': 'moderate', 'description': 'invalid aria attr values', 'nodes': [{'target': ['.status']}]},
                    {'id': 'td-has-header', 'impact': 'moderate', 'description': 'td needs headers', 'nodes': [{'target': ['.sales-table td']}]},
                ]
            }
            lighthouse_data = {
                'audits': {
                    'th-has-data-cells': {
                        'score': 0,
                        'scoreDisplayMode': 'binary',
                        'title': 'th elements should map to data cells',
                        'details': {'items': [{'node': {'selector': '.sales-table th'}}]},
                    }
                }
            }
            report = normalize_report(contract, axe_data, lighthouse_data, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            updated_html = working.read_text(encoding='utf-8')
            self.assertIn('role="checkbox" aria-checked="false"', updated_html)
            self.assertIn('role="switch" aria-checked="false"', updated_html)
            self.assertIn('scope="col"', updated_html)
            self.assertIn('headers="col-1"', updated_html)
            self.assertIn('headers="col-2"', updated_html)
            self.assertIn('aria-checked="false"', diff_text)
            self.assertIn('headers="col-1"', diff_text)
            self.assertGreaterEqual(updated_report['summary']['remediation_lifecycle']['implemented'], 4)


    def test_apply_report_fixes_supports_list_and_table_caption_rules(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'list-table-fixes.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'list', 'impact': 'moderate', 'description': 'Lists must contain li elements', 'nodes': [{'target': ['ul.plain']}]},
                    {'id': 'listitem', 'impact': 'moderate', 'description': 'Listitem must be in list container', 'nodes': [{'target': ['li.orphan']}]},
                    {'id': 'table-fake-caption', 'impact': 'moderate', 'description': 'Caption-like header should use caption', 'nodes': [{'target': ['table.pricing']}]},
                ]
            }
            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            updated_html = working.read_text(encoding='utf-8')
            self.assertIn('<ul class="plain"><li>First item</li></ul>', updated_html)
            self.assertIn('<ul><li class="orphan">Standalone entry</li></ul>', updated_html)
            self.assertIn('<caption>Plan Comparison</caption>', updated_html)
            self.assertNotIn('<th colspan="2">Plan Comparison</th>', updated_html)
            self.assertIn('<caption>Plan Comparison</caption>', diff_text)
            self.assertGreaterEqual(updated_report['summary']['remediation_lifecycle']['implemented'], 3)
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

    def test_apply_report_fixes_idempotent_for_expanded_rule_sets(self) -> None:
        cases = [
            (
                'aria-table-auto-fix.html',
                {
                    'violations': [
                        {'id': 'aria-required-attr', 'impact': 'serious', 'description': 'missing required aria attrs', 'nodes': [{'target': ['.acceptance']}]},
                        {'id': 'aria-valid-attr-value', 'impact': 'moderate', 'description': 'invalid aria attr values', 'nodes': [{'target': ['.status']}]},
                        {'id': 'td-has-header', 'impact': 'moderate', 'description': 'td needs headers', 'nodes': [{'target': ['.sales-table td']}]},
                    ]
                },
                {
                    'audits': {
                        'th-has-data-cells': {
                            'score': 0,
                            'scoreDisplayMode': 'binary',
                            'title': 'th elements should map to data cells',
                            'details': {'items': [{'node': {'selector': '.sales-table th'}}]},
                        }
                    }
                },
            ),
            (
                'list-table-fixes.html',
                {
                    'violations': [
                        {'id': 'list', 'impact': 'moderate', 'description': 'Lists must contain li elements', 'nodes': [{'target': ['ul.plain']}]},
                        {'id': 'listitem', 'impact': 'moderate', 'description': 'Listitem must be in list container', 'nodes': [{'target': ['li.orphan']}]},
                        {'id': 'table-fake-caption', 'impact': 'moderate', 'description': 'Caption-like header should use caption', 'nodes': [{'target': ['table.pricing']}]},
                    ]
                },
                {'audits': {}},
            ),
            (
                'deep-auto-fix.html',
                {
                    'violations': [
                        {'id': 'html-xml-lang-mismatch', 'impact': 'moderate', 'description': 'lang and xml:lang should match', 'nodes': [{'target': ['html']}]},
                        {'id': 'valid-lang', 'impact': 'moderate', 'description': 'invalid language code', 'nodes': [{'target': ['p[lang]']}]},
                        {'id': 'meta-refresh', 'impact': 'moderate', 'description': 'refresh should be removed', 'nodes': [{'target': ['meta[http-equiv="refresh"]']}]},
                        {'id': 'input-image-alt', 'impact': 'serious', 'description': 'image input needs alt', 'nodes': [{'target': ['input[type="image"]']}]},
                        {'id': 'area-alt', 'impact': 'serious', 'description': 'area needs alt', 'nodes': [{'target': ['area']}]},
                    ]
                },
                {'audits': {}},
            ),
        ]

        for fixture_name, axe_data, lighthouse_data in cases:
            with self.subTest(fixture=fixture_name), tempfile.TemporaryDirectory() as tmp:
                fixture = Path(__file__).parent / 'fixtures' / fixture_name
                working = Path(tmp) / fixture.name
                working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
                contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})

                first_report = normalize_report(contract, axe_data, lighthouse_data, None, None)
                patched_report, first_diff = apply_report_fixes(working, first_report)
                second_report, second_diff = apply_report_fixes(working, patched_report)

                self.assertTrue(first_diff)
                self.assertEqual(second_diff, '')
                self.assertIn('No safe auto-fix changes were applied', ' '.join(second_report['run_meta']['notes']))

    def test_apply_report_fixes_preserves_manual_review_items_in_mixed_report(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'missing-lang-button-label.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract(
                {
                    'target': str(working),
                    'execution_mode': 'apply-fixes',
                    'wcag_version': '2.2',
                }
            )
            axe_data = {
                'violations': [
                    {'id': 'button-name', 'impact': 'serious', 'description': 'Buttons need names', 'nodes': [{'target': ['button.icon-only']}]},
                ]
            }

            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)

            self.assertTrue(diff_text)
            self.assertEqual(updated_report['summary']['auto_fixed_count'], 1)
            self.assertGreaterEqual(updated_report['summary']['manual_required_count'], 1)
            self.assertEqual(
                updated_report['summary']['manual_required_count'],
                updated_report['summary']['needs_manual_review'],
            )
            manual_findings = [
                item for item in updated_report['findings'] if item['rule_id'].startswith('wcag22-manual-')
            ]
            self.assertTrue(manual_findings)
            self.assertTrue(all(item['status'] == 'needs-review' for item in manual_findings))

    def test_diff_artifacts_cover_rewrite_families(self) -> None:
        cases = [
            ('aria-table-auto-fix.html', 'aria-required-attr', 'aria-checked="false"'),
            ('deep-auto-fix.html', 'html-xml-lang-mismatch', 'xml:lang="en-US"'),
            ('list-table-fixes.html', 'table-fake-caption', '<caption>Plan Comparison</caption>'),
            ('missing-lang-button-label.html', 'button-name', 'aria-label="Button"'),
            ('empty-link-viewport.html', 'meta-viewport', 'width=device-width, initial-scale=1'),
            ('deep-auto-fix.html', 'meta-refresh', 'http-equiv="refresh"'),
        ]

        for fixture_name, rule_id, expected_token in cases:
            with self.subTest(rule_id=rule_id), tempfile.TemporaryDirectory() as tmp:
                fixture = Path(__file__).parent / 'fixtures' / fixture_name
                working = Path(tmp) / fixture.name
                working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
                contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
                axe_data = {
                    'violations': [
                        {'id': rule_id, 'impact': 'serious', 'description': f'{rule_id} violation', 'nodes': [{'target': ['body']}]},
                    ]
                }

                report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
                updated_report, diff_text = apply_report_fixes(working, report)

                self.assertTrue(updated_report['run_meta']['diff_artifacts'])
                self.assertTrue(updated_report['summary']['diff_summary'])
                self.assertIn(rule_id, [item['rule_id'] for item in updated_report['summary']['diff_summary']])
                self.assertIn(rule_id, [item['rule_id'] for item in updated_report['run_meta']['applied_changes']])
                self.assertIn(expected_token, diff_text)

    def test_apply_report_fixes_noop_for_unsupported_and_manual_only_findings(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'wcag22-manual-review.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract(
                {
                    'target': str(working),
                    'execution_mode': 'apply-fixes',
                    'wcag_version': '2.2',
                }
            )
            axe_data = {
                'violations': [
                    {'id': 'heading-order', 'impact': 'serious', 'description': 'Heading order issue', 'nodes': [{'target': ['h3']}]},
                ]
            }

            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)

            self.assertEqual(diff_text, '')
            self.assertFalse(updated_report['run_meta']['files_modified'])
            self.assertEqual(updated_report['run_meta']['diff_artifacts'], [])
            self.assertIn('No safe auto-fix changes were applied', ' '.join(updated_report['run_meta']['notes']))

    def test_repeated_normalize_and_apply_fixes_runs_remain_stable(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'empty-link-viewport.html'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')

            axe_data = {
                'violations': [
                    {'id': 'link-name', 'impact': 'serious', 'description': 'Links need names', 'nodes': [{'target': ['a.cta']}]},
                    {'id': 'meta-viewport', 'impact': 'moderate', 'description': 'Viewport must allow zoom', 'nodes': [{'target': ['meta[name="viewport"]']}]},
                ]
            }
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})

            diffs = []
            fixed_counts = []
            for _ in range(3):
                report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
                updated_report, diff_text = apply_report_fixes(working, report)
                diffs.append(diff_text)
                fixed_counts.append(updated_report['summary']['auto_fixed_count'])

            self.assertTrue(diffs[0])
            self.assertEqual(diffs[1], '')
            self.assertEqual(diffs[2], '')
            self.assertEqual(fixed_counts, [2, 0, 0])

    def test_apply_report_fixes_supports_react_jsx_image_alt(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'react-specific.jsx'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'image-alt', 'impact': 'serious', 'description': 'Images need alt', 'nodes': [{'target': ['img.hero']}]},
                    {'id': 'button-name', 'impact': 'serious', 'description': 'Buttons need names', 'nodes': [{'target': ['button.icon-only']}]},
                ]
            }
            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            updated_text = working.read_text(encoding='utf-8')
            self.assertIn('alt=""', updated_text)
            self.assertIn('aria-label="Button"', updated_text)
            self.assertTrue(any('framework-aware alt remediation for react' in item['description'] for item in updated_report['summary']['diff_summary']))
            self.assertGreaterEqual(updated_report['summary']['remediation_lifecycle']['implemented'], 2)

    def test_apply_report_fixes_supports_vue_template_image_alt(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'vue-specific.vue'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'image-alt', 'impact': 'serious', 'description': 'Images need alt', 'nodes': [{'target': ['img.hero']}]},
                ]
            }
            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            updated_text = working.read_text(encoding='utf-8')
            self.assertIn('alt=""', updated_text)
            self.assertTrue(any('framework-aware alt remediation for vue' in item['description'] for item in updated_report['summary']['diff_summary']))

    def test_apply_report_fixes_supports_nextjs_layout_lang_and_image_alt(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'nextjs-layout.tsx'
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / fixture.name
            working.write_text(fixture.read_text(encoding='utf-8'), encoding='utf-8')
            contract = resolve_contract({'target': str(working), 'execution_mode': 'apply-fixes'})
            axe_data = {
                'violations': [
                    {'id': 'html-has-lang', 'impact': 'moderate', 'description': 'Document should define language', 'nodes': [{'target': ['Html']}]},
                    {'id': 'image-alt', 'impact': 'serious', 'description': 'Images need alt', 'nodes': [{'target': ['Image']}]},
                ]
            }
            report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
            updated_report, diff_text = apply_report_fixes(working, report)
            updated_text = working.read_text(encoding='utf-8')
            self.assertIn('<Html lang="en">', updated_text)
            self.assertIn('alt=""', updated_text)
            self.assertTrue(any('Next.js Html/html layout root' in item['description'] for item in updated_report['summary']['diff_summary']))
            self.assertGreaterEqual(updated_report['summary']['remediation_lifecycle']['implemented'], 2)

if __name__ == '__main__':
    unittest.main()
