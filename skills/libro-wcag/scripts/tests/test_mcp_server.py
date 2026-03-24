#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def load_module(repo_root: Path, relative_path: str, module_name: str):
    module_path = repo_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class McpServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.audit_page = load_module(cls.repo_root, 'mcp-server/tools/audit_page.py', 'mcp_audit_page')
        cls.suggest_fixes = load_module(cls.repo_root, 'mcp-server/tools/suggest_fixes.py', 'mcp_suggest_fixes')
        cls.normalize_report = load_module(
            cls.repo_root,
            'mcp-server/tools/normalize_report.py',
            'mcp_normalize_report',
        )

    def test_build_audit_command_targets_core_cli(self) -> None:
        output_dir = self.repo_root / '.tmp-test' / 'mcp-audit-output'
        command = self.audit_page.build_audit_command(
            target='./index.html',
            output_dir=output_dir,
            execution_mode='audit-only',
        )
        self.assertIn('run_accessibility_audit.py', command[1])
        self.assertIn('--report-format', command)
        self.assertIn('json', command)
        self.assertIn(str(output_dir), command)

    def test_suggest_from_findings_uses_remediation_library_and_wcag_citations(self) -> None:
        payload = self.suggest_fixes.suggest_from_findings(
            target='./index.html',
            findings=[
                {
                    'id': 'ISSUE-001',
                    'rule_id': 'image-alt',
                    'sc': ['1.1.1'],
                }
            ],
            wcag_version='2.1',
        )
        self.assertEqual(payload['execution_mode'], 'suggest-only')
        suggestion = payload['suggestions'][0]
        self.assertEqual(suggestion['rule_id'], 'image-alt')
        self.assertTrue(suggestion['auto_fix_supported'])
        self.assertIn('1.1.1', suggestion['citations'][0]['sc'])
        self.assertIn('w3.org', suggestion['citations'][0]['url'])

    def test_normalize_wcag_payload_returns_report_and_markdown(self) -> None:
        payload = self.normalize_report.normalize_wcag_payload(
            target='./index.html',
            execution_mode='audit-only',
            raw_report={
                'axe_data': {
                    'violations': [
                        {
                            'id': 'image-alt',
                            'impact': 'serious',
                            'description': 'Images must have alternate text',
                            'nodes': [{'target': ['img.hero']}],
                        }
                    ]
                },
                'lighthouse_data': None,
                'lighthouse_skipped': True,
            },
        )
        self.assertIn('report', payload)
        self.assertIn('markdown', payload)
        self.assertEqual(payload['report']['summary']['total_findings'], 1)
        self.assertIn('ISSUE-001', payload['markdown'])


if __name__ == '__main__':
    unittest.main()
