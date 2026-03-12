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

    def test_run_accessibility_audit_apply_fixes_dry_run_keeps_target_unmodified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            original = '<!doctype html><html><head><title>Fixture</title></head><body><img class="hero" src="hero.png"></body></html>'
            html_path.write_text(original, encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Images must have alternate text', 'nodes': [{'target': ['img.hero']}]},
                        ]
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
                    '--dry-run',
                    '--output-language',
                    'en',
                    '--mock-axe-json',
                    str(axe_json),
                    '--skip-lighthouse',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            self.assertEqual(html_path.read_text(encoding='utf-8'), original)
            self.assertTrue((output_dir / 'wcag-fixes.dry-run.diff').exists())
            self.assertIn('projected_mutation_telemetry', payload['run_meta'])
            self.assertIn('retry_policy', payload['run_meta'])
            self.assertIn('--dry-run', ' '.join(payload['run_meta']['notes']))
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
    def test_run_accessibility_audit_apply_fixes_second_run_cleans_stale_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            html_path.write_text(
                '<!doctype html><html><head><title>Fixture</title><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"></head><body><img class="hero" src="hero.png"></body></html>',
                encoding='utf-8',
            )
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Images must have alternate text', 'nodes': [{'target': ['img.hero']}]},
                            {'id': 'meta-viewport', 'impact': 'moderate', 'description': 'Viewport must allow zoom', 'nodes': [{'target': ['meta[name="viewport"]']}]},
                        ]
                    }
                ),
                encoding='utf-8',
            )

            command = [
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
                '--skip-lighthouse',
            ]

            first = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertTrue((output_dir / 'wcag-fixes.diff').exists())
            self.assertTrue((output_dir / 'wcag-fixed-report.snapshot.json').exists())

            second = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            self.assertFalse((output_dir / 'wcag-fixes.diff').exists())
            self.assertFalse((output_dir / 'wcag-fixed-report.snapshot.json').exists())
            self.assertIn('No safe auto-fix changes were applied', ' '.join(payload['run_meta']['notes']))

    def test_run_accessibility_audit_apply_fixes_skips_unsupported_local_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_path = Path(tmp) / 'notes.md'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            target_path.write_text('# note\n\n![hero](hero.png)\n', encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Images must have alternate text', 'nodes': [{'target': ['img.hero']}]},
                        ]
                    }
                ),
                encoding='utf-8',
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                    '--target',
                    str(target_path),
                    '--output-dir',
                    str(output_dir),
                    '--execution-mode',
                    'apply-fixes',
                    '--output-language',
                    'en',
                    '--mock-axe-json',
                    str(axe_json),
                    '--skip-lighthouse',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            self.assertFalse(payload['run_meta']['files_modified'])
            self.assertIn('apply-fixes skipped: unsupported local target extension ".md".', ' '.join(payload['run_meta']['notes']))
            self.assertFalse((output_dir / 'wcag-fixes.diff').exists())
            self.assertFalse((output_dir / 'wcag-fixed-report.snapshot.json').exists())

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


    def test_run_accessibility_audit_with_sarif_and_rule_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            html_path.write_text('<!doctype html><html><body><img class="hero" src="hero.png"><button class="icon"></button></body></html>', encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Image alt missing', 'nodes': [{'target': ['img.hero']}]},
                            {'id': 'button-name', 'impact': 'serious', 'description': 'Button name missing', 'nodes': [{'target': ['button.icon']}]},
                        ]
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
                    '--report-format',
                    'sarif',
                    '--include-rule',
                    'image-alt',
                    '--mock-axe-json',
                    str(axe_json),
                    '--skip-lighthouse',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue((output_dir / 'wcag-report.sarif').exists())
            payload = json.loads((output_dir / 'wcag-report.sarif').read_text(encoding='utf-8'))
            rules = payload['runs'][0]['tool']['driver']['rules']
            self.assertEqual(len(rules), 1)
            self.assertEqual(rules[0]['id'], 'image-alt')

    def test_run_accessibility_audit_fail_on_returns_deterministic_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            html_path.write_text('<!doctype html><html><body><img class="hero" src="hero.png"></body></html>', encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Image alt missing', 'nodes': [{'target': ['img.hero']}]},
                        ]
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
                    '--fail-on',
                    'serious',
                    '--mock-axe-json',
                    str(axe_json),
                    '--skip-lighthouse',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 43, completed.stdout + completed.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            self.assertTrue(payload['run_meta']['policy_gate']['failed'])

    def test_run_accessibility_audit_fail_on_new_only_does_not_fail_for_baseline_debt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            baseline_json = Path(tmp) / 'baseline.json'
            html_path.write_text('<!doctype html><html><body><img class="hero" src="hero.png"></body></html>', encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Image alt missing', 'nodes': [{'target': ['img.hero']}]},
                        ]
                    }
                ),
                encoding='utf-8',
            )
            baseline_json.write_text(
                json.dumps(
                    {
                        'findings': [
                            {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'}
                        ]
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
                    '--fail-on',
                    'serious',
                    '--fail-on-new-only',
                    '--baseline-report',
                    str(baseline_json),
                    '--mock-axe-json',
                    str(axe_json),
                    '--skip-lighthouse',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            self.assertEqual(payload['run_meta']['baseline_diff']['introduced_count'], 0)
            self.assertFalse(payload['run_meta']['policy_gate']['failed'])
            self.assertEqual(payload['run_meta']['policy_gate']['scope'], 'introduced-only')

    def test_run_accessibility_audit_fail_on_new_only_fails_for_introduced_debt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            baseline_json = Path(tmp) / 'baseline.json'
            html_path.write_text('<!doctype html><html><body><img class="hero" src="hero.png"></body></html>', encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Image alt missing', 'nodes': [{'target': ['img.hero']}]},
                        ]
                    }
                ),
                encoding='utf-8',
            )
            baseline_json.write_text(
                json.dumps(
                    {
                        'findings': [
                            {'rule_id': 'label', 'changed_target': 'input#email', 'status': 'open'}
                        ]
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
                    '--fail-on',
                    'serious',
                    '--fail-on-new-only',
                    '--baseline-report',
                    str(baseline_json),
                    '--mock-axe-json',
                    str(axe_json),
                    '--skip-lighthouse',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 43, completed.stdout + completed.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            self.assertEqual(payload['run_meta']['baseline_diff']['introduced_count'], 1)
            self.assertTrue(payload['run_meta']['policy_gate']['failed'])
            self.assertEqual(payload['run_meta']['policy_gate']['scope'], 'introduced-only')

    def test_run_accessibility_audit_max_findings_caps_sorted_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            html_path.write_text('<!doctype html><html><body><img class="hero" src="hero.png"><button class="icon"></button></body></html>', encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Image alt missing', 'nodes': [{'target': ['img.hero']}]},
                            {'id': 'button-name', 'impact': 'serious', 'description': 'Button name missing', 'nodes': [{'target': ['button.icon']}]},
                        ]
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
                    '--mock-axe-json',
                    str(axe_json),
                    '--skip-lighthouse',
                    '--sort-findings',
                    'rule',
                    '--max-findings',
                    '1',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            self.assertEqual(len(payload['findings']), 1)
            self.assertEqual(payload['findings'][0]['rule_id'], 'button-name')
            self.assertEqual(payload['run_meta']['findings_cap']['truncated'], 1)

    def test_run_accessibility_audit_summary_only_prints_compact_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            html_path.write_text('<!doctype html><html><title>Fixture</title><body></body></html>', encoding='utf-8')
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
                    '--summary-only',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            compact = json.loads(completed.stdout.strip())
            self.assertEqual(compact['status'], 'ok')
            self.assertTrue((output_dir / 'wcag-report.json').exists())
            self.assertTrue((output_dir / 'wcag-report.md').exists())
            self.assertIn('machine_output', compact)
if __name__ == '__main__':
    unittest.main()


