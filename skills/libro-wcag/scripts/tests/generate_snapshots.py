#!/usr/bin/env python3
"""Generate .report.json and .report.md snapshot baselines for HTML fixtures.

Usage: python -m skills.libro-wcag.scripts.tests.generate_snapshots
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from wcag_workflow import normalize_report, resolve_contract, to_markdown_table

SNAPSHOTS_DIR = Path(__file__).parent / 'snapshots'

# Map: fixture_name -> (axe_violations, lighthouse_audits)
# Each axe violation: {'id': str, 'impact': str, 'description': str, 'nodes': [{'target': [str]}]}
FIXTURE_VIOLATIONS: dict[str, dict] = {
    'aria-family': {
        'axe': [
            {'id': 'aria-valid-attr-value', 'impact': 'serious', 'description': 'ARIA attribute values must be valid', 'nodes': [{'target': ['#details-toggle']}]},
            {'id': 'aria-required-attr', 'impact': 'serious', 'description': 'Required ARIA attributes must be provided', 'nodes': [{'target': ['div[role="slider"]']}]},
        ],
    },
    'aria-table-auto-fix': {
        'axe': [
            {'id': 'aria-valid-attr-value', 'impact': 'serious', 'description': 'ARIA attribute values must be valid', 'nodes': [{'target': ['div[role="switch"]']}]},
            {'id': 'td-has-header', 'impact': 'serious', 'description': 'Table cells must have associated headers', 'nodes': [{'target': ['table.sales-table td']}]},
        ],
    },
    'aria-title': {
        'axe': [
            {'id': 'document-title', 'impact': 'serious', 'description': 'Documents must have a title', 'nodes': [{'target': ['html']}]},
            {'id': 'aria-required-attr', 'impact': 'serious', 'description': 'Required ARIA attributes must be provided', 'nodes': [{'target': ['div[role="switch"].switch-icon']}]},
            {'id': 'aria-required-attr', 'impact': 'serious', 'description': 'Required ARIA attributes must be provided', 'nodes': [{'target': ['div[role="progressbar"].progress-shell']}]},
        ],
    },
    'create-mode-draft': {
        'axe': [
            {'id': 'button-name', 'impact': 'critical', 'description': 'Buttons must have discernible text', 'nodes': [{'target': ['button[type="button"]']}]},
            {'id': 'image-alt', 'impact': 'critical', 'description': 'Images must have alternate text', 'nodes': [{'target': ['img']}]},
        ],
    },
    'deep-auto-fix': {
        'axe': [
            {'id': 'html-xml-lang-mismatch', 'impact': 'serious', 'description': 'HTML lang and xml:lang must match', 'nodes': [{'target': ['html']}]},
            {'id': 'meta-refresh', 'impact': 'serious', 'description': 'Timed refresh must not exist', 'nodes': [{'target': ['meta[http-equiv="refresh"]']}]},
            {'id': 'valid-lang', 'impact': 'serious', 'description': 'lang attribute must have a valid value', 'nodes': [{'target': ['p[lang="??"]']}]},
            {'id': 'input-image-alt', 'impact': 'critical', 'description': 'Image buttons must have alternate text', 'nodes': [{'target': ['input[type="image"]']}]},
            {'id': 'area-alt', 'impact': 'critical', 'description': 'Area elements must have alternate text', 'nodes': [{'target': ['area']}]},
        ],
    },
    'form-errors': {
        'axe': [
            {'id': 'label', 'impact': 'serious', 'description': 'Form elements must have labels', 'nodes': [{'target': ['#email']}]},
            {'id': 'label', 'impact': 'serious', 'description': 'Form elements must have labels', 'nodes': [{'target': ['#coupon']}]},
            {'id': 'button-name', 'impact': 'critical', 'description': 'Buttons must have discernible text', 'nodes': [{'target': ['button[type="submit"]']}]},
        ],
    },
    'heading-hierarchy': {
        'axe': [
            {'id': 'heading-order', 'impact': 'moderate', 'description': 'Heading levels should increase by one', 'nodes': [{'target': ['h3']}]},
            {'id': 'empty-heading', 'impact': 'serious', 'description': 'Headings must not be empty', 'nodes': [{'target': ['h2']}]},
        ],
    },
    'keyboard-tabindex': {
        'axe': [
            {'id': 'tabindex', 'impact': 'minor', 'description': 'tabindex value should not be greater than 0', 'nodes': [{'target': ['button[tabindex="3"]']}]},
            {'id': 'tabindex', 'impact': 'minor', 'description': 'tabindex value should not be greater than 0', 'nodes': [{'target': ['a[tabindex="2"]']}]},
            {'id': 'tabindex', 'impact': 'minor', 'description': 'tabindex value should not be greater than 0', 'nodes': [{'target': ['div[role="button"][tabindex="5"]']}]},
        ],
    },
    'landmark-region': {
        'axe': [
            {'id': 'region', 'impact': 'moderate', 'description': 'All page content should be contained by landmarks', 'nodes': [{'target': ['div.shell']}]},
        ],
    },
    'list-table-fixes': {
        'axe': [
            {'id': 'list', 'impact': 'serious', 'description': 'Lists must only contain li elements', 'nodes': [{'target': ['ul.plain']}]},
            {'id': 'table-fake-caption', 'impact': 'serious', 'description': 'Data tables should use proper header markup', 'nodes': [{'target': ['table.pricing']}]},
        ],
    },
    'malformed-encoding': {
        'axe': [
            {'id': 'html-has-lang', 'impact': 'critical', 'description': 'html element must have a lang attribute', 'nodes': [{'target': ['html']}]},
            {'id': 'image-alt', 'impact': 'critical', 'description': 'Images must have alternate text', 'nodes': [{'target': ['img.hero']}]},
            {'id': 'list', 'impact': 'serious', 'description': 'Lists must only contain li elements', 'nodes': [{'target': ['ul.plain']}]},
        ],
    },
    'missing-lang-button-label': {
        'axe': [
            {'id': 'html-has-lang', 'impact': 'critical', 'description': 'html element must have a lang attribute', 'nodes': [{'target': ['html']}]},
            {'id': 'button-name', 'impact': 'critical', 'description': 'Buttons must have discernible text', 'nodes': [{'target': ['button.icon-only']}]},
            {'id': 'label', 'impact': 'serious', 'description': 'Form elements must have labels', 'nodes': [{'target': ['#email']}]},
        ],
    },
    'realistic-mixed-findings': {
        'axe': [
            {'id': 'html-has-lang', 'impact': 'critical', 'description': 'html element must have a lang attribute', 'nodes': [{'target': ['html']}]},
            {'id': 'image-alt', 'impact': 'critical', 'description': 'Images must have alternate text', 'nodes': [{'target': ['img.hero']}]},
            {'id': 'button-name', 'impact': 'critical', 'description': 'Buttons must have discernible text', 'nodes': [{'target': ['button.icon-only']}]},
            {'id': 'list', 'impact': 'serious', 'description': 'Lists must only contain li elements', 'nodes': [{'target': ['ul.plain']}]},
            {'id': 'document-title', 'impact': 'serious', 'description': 'Documents must have a title', 'nodes': [{'target': ['html']}]},
        ],
    },
    'table-semantics': {
        'axe': [
            {'id': 'table-fake-caption', 'impact': 'serious', 'description': 'Data tables should use proper header markup', 'nodes': [{'target': ['table']}]},
            {'id': 'td-has-header', 'impact': 'serious', 'description': 'Table cells must have associated headers', 'nodes': [{'target': ['td']}]},
        ],
    },
    'wcag22-focus': {
        'axe': [
            {'id': 'color-contrast', 'impact': 'serious', 'description': 'Elements must meet color contrast requirements', 'nodes': [{'target': ['a.nav-link']}]},
        ],
    },
}


def generate_snapshots() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0
    for fixture_name, data in sorted(FIXTURE_VIOLATIONS.items()):
        json_path = SNAPSHOTS_DIR / f'{fixture_name}.report.json'
        md_path = SNAPSHOTS_DIR / f'{fixture_name}.report.md'
        if json_path.exists():
            print(f'  SKIP {fixture_name} (snapshot exists)')
            continue
        contract = resolve_contract({'target': f'fixtures/{fixture_name}.html', 'output_language': 'en'})
        axe_data = {'violations': data.get('axe', [])}
        lighthouse_data = {'audits': {}}
        report = normalize_report(contract, axe_data, lighthouse_data, None, None)
        report['run_meta']['generated_at'] = '<generated>'
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        md_text = to_markdown_table(report)
        md_path.write_text(md_text, encoding='utf-8')
        generated += 1
        print(f'  GENERATED {fixture_name} ({len(report["findings"])} findings)')
    print(f'\nDone: {generated} snapshots generated, {len(FIXTURE_VIOLATIONS) - generated} skipped.')


if __name__ == '__main__':
    generate_snapshots()
