#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]

    def test_run_accessibility_audit_with_skip_flags_generates_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'index.html'
            output_dir = Path(tmp) / 'out'
            html_path.write_text('<!doctype html><html lang="en"><title>Fixture</title><img src="hero.png"></html>', encoding='utf-8')
            completed = subprocess.run(
                [
                    sys.executable,
                    'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                    '--target',
                    str(html_path),
                    '--output-dir',
                    str(output_dir),
                    '--skip-axe',
                    '--skip-lighthouse',
                    '--output-language',
                    'en',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            markdown = (output_dir / 'wcag-report.md').read_text(encoding='utf-8')
            self.assertEqual(payload['run_meta']['tools']['axe'], 'skipped')
            self.assertEqual(payload['run_meta']['tools']['lighthouse'], 'skipped')
            self.assertIn('Execution mode: suggest-only', markdown)

    def test_run_accessibility_audit_rejects_invalid_target_before_scanning(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                '--target',
                'ftp://example.com/page.html',
                '--output-dir',
                'out-test-invalid',
                '--skip-axe',
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('Unsupported target scheme', completed.stderr + completed.stdout)

    def test_normalize_report_cli_with_both_tool_inputs_dedupes_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            axe_json = Path(tmp) / 'axe.json'
            lighthouse_json = Path(tmp) / 'lighthouse.json'
            output_json = Path(tmp) / 'report.json'
            output_md = Path(tmp) / 'report.md'
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {
                                'id': 'image-alt',
                                'impact': 'serious',
                                'description': 'Images must have alternate text',
                                'nodes': [{'target': ['img.hero']}],
                            }
                        ]
                    }
                ),
                encoding='utf-8',
            )
            lighthouse_json.write_text(
                json.dumps(
                    {
                        'audits': {
                            'image-alt': {
                                'score': 0,
                                'scoreDisplayMode': 'binary',
                                'title': 'Image elements have [alt] attributes',
                                'details': {'items': [{'node': {'selector': 'img.hero'}}]},
                            }
                        }
                    }
                ),
                encoding='utf-8',
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    'skills/libro-agent-wcag/scripts/normalize_report.py',
                    '--target',
                    'https://example.com',
                    '--axe-json',
                    str(axe_json),
                    '--lighthouse-json',
                    str(lighthouse_json),
                    '--output-json',
                    str(output_json),
                    '--output-md',
                    str(output_md),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads(output_json.read_text(encoding='utf-8'))
            self.assertEqual(len(payload['findings']), 1)
            self.assertEqual(payload['findings'][0]['source'], 'axe+lighthouse')

    def test_normalize_report_cli_with_scanner_error_generates_manual_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_json = Path(tmp) / 'report.json'
            output_md = Path(tmp) / 'report.md'
            completed = subprocess.run(
                [
                    sys.executable,
                    'skills/libro-agent-wcag/scripts/normalize_report.py',
                    '--target',
                    'https://example.com',
                    '--axe-error',
                    'scanner crashed',
                    '--output-json',
                    str(output_json),
                    '--output-md',
                    str(output_md),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads(output_json.read_text(encoding='utf-8'))
            self.assertEqual(payload['run_meta']['tools']['axe'], 'error')
            self.assertTrue(any(item['status'] == 'needs-review' for item in payload['findings']))

    def test_run_accessibility_audit_with_mock_scanners_generates_apply_fixes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            lighthouse_json = Path(tmp) / 'lighthouse.json'
            html_path.write_text(
                '<!doctype html><html><head><title></title><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"></head><body><img class="hero" src="hero.png"><button class="icon-only"></button></body></html>',
                encoding='utf-8',
            )
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Images must have alternate text', 'nodes': [{'target': ['img.hero']}]},
                            {'id': 'button-name', 'impact': 'serious', 'description': 'Buttons need names', 'nodes': [{'target': ['button.icon-only']}]},
                        ]
                    }
                ),
                encoding='utf-8',
            )
            lighthouse_json.write_text(
                json.dumps(
                    {
                        'audits': {
                            'meta-viewport': {
                                'score': 0,
                                'scoreDisplayMode': 'binary',
                                'title': 'User-scalable is not disabled',
                                'details': {'items': [{'node': {'selector': 'meta[name="viewport"]'}}]},
                            }
                        }
                    }
                ),
                encoding='utf-8',
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                    '--target',
                    str(html_path),
                    '--output-dir',
                    str(output_dir),
                    '--execution-mode',
                    'apply-fixes',
                    '--output-language',
                    'en',
                    '--mock-axe-json',
                    str(axe_json),
                    '--mock-lighthouse-json',
                    str(lighthouse_json),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            self.assertTrue(payload['run_meta']['files_modified'])
            self.assertTrue((output_dir / 'wcag-fixes.diff').exists())
            self.assertTrue((output_dir / 'wcag-fixed-report.snapshot.json').exists())

    def test_run_accessibility_audit_rejects_conflicting_mock_and_skip_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            axe_json = Path(tmp) / 'axe.json'
            html_path.write_text('<!doctype html><html lang="en"><title>x</title></html>', encoding='utf-8')
            axe_json.write_text(json.dumps({'violations': []}), encoding='utf-8')
            completed = subprocess.run(
                [
                    sys.executable,
                    'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                    '--target',
                    str(html_path),
                    '--output-dir',
                    str(Path(tmp) / 'out'),
                    '--skip-axe',
                    '--mock-axe-json',
                    str(axe_json),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn('--skip-axe cannot be combined with --mock-axe-json', completed.stderr + completed.stdout)
    def test_doctor_reports_broken_install_when_adapter_prompt_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'claude-skill'
            install = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'claude',
                    '--dest',
                    str(destination),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            (destination / 'adapters' / 'claude' / 'prompt-template.md').unlink()
            doctor = subprocess.run(
                [
                    sys.executable,
                    'scripts/doctor-agent.py',
                    '--agent',
                    'claude',
                    '--dest',
                    str(destination),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(doctor.returncode, 0)
            payload = json.loads(doctor.stdout)
            self.assertFalse(payload['ok'])
            self.assertFalse(payload['adapter_prompt'])


if __name__ == '__main__':
    unittest.main()

