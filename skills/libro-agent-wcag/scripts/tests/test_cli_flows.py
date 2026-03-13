#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
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
            self.assertEqual(payload['run_meta']['preflight']['tools']['runtime']['version_provenance']['source'], 'skipped')
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

    def test_run_accessibility_audit_lists_policy_config_keys_without_target(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                '--list-policy-config-keys',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        key_names = [item['name'] for item in payload['keys']]
        self.assertIn('report_format', key_names)
        self.assertIn('ignore_rules', key_names)

    def test_run_accessibility_audit_strict_rule_overlap_fails_fast(self) -> None:
        workspace = self.repo_root / 'automation-work' / 'm26-cli-overlap-test'
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir(parents=True, exist_ok=True)
        html_path = workspace / 'sample.html'
        output_dir = workspace / 'out'
        axe_json = workspace / 'axe.json'
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
                '--include-rule',
                'image-alt',
                '--ignore-rule',
                'image-alt',
                '--strict-rule-overlap',
                '--mock-axe-json',
                str(axe_json),
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('--strict-rule-overlap detected rule ids', completed.stdout + completed.stderr)
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

    def test_doctor_manifest_integrity_mode_detects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'codex-skill'
            install = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'codex',
                    '--dest',
                    str(destination),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            prompt_path = destination / 'adapters' / 'openai-codex' / 'prompt-template.md'
            prompt_path.write_text(prompt_path.read_text(encoding='utf-8') + '\n<!-- tamper -->\n', encoding='utf-8')

            doctor = subprocess.run(
                [
                    sys.executable,
                    'scripts/doctor-agent.py',
                    '--agent',
                    'codex',
                    '--dest',
                    str(destination),
                    '--verify-manifest-integrity',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(doctor.returncode, 0)
            payload = json.loads(doctor.stdout)
            self.assertFalse(payload['ok'])
            self.assertFalse(payload['manifest_integrity']['verified'])
            self.assertEqual(payload['manifest_integrity']['algorithm'], 'sha256')
            self.assertGreaterEqual(len(payload['manifest_integrity']['hash_mismatches']), 1)

    def test_doctor_manifest_integrity_mode_detects_missing_companion_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'gemini-skill'
            install = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'gemini',
                    '--dest',
                    str(destination),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            (destination / 'adapters' / 'gemini' / 'failure-guide.md').unlink()

            doctor = subprocess.run(
                [
                    sys.executable,
                    'scripts/doctor-agent.py',
                    '--agent',
                    'gemini',
                    '--dest',
                    str(destination),
                    '--verify-manifest-integrity',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(doctor.returncode, 0)
            payload = json.loads(doctor.stdout)
            self.assertFalse(payload['ok'])
            self.assertFalse(payload['manifest_integrity']['verified'])
            self.assertIn('adapters/gemini/failure-guide.md', payload['manifest_integrity']['missing_files'])


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

    def test_run_accessibility_audit_baseline_diff_includes_debt_transition_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            baseline_json = Path(tmp) / 'baseline.json'
            html_path.write_text('<!doctype html><html><body><img class="hero" src="hero.png"><button class="icon"></button></body></html>', encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Image alt missing', 'nodes': [{'target': ['img.hero']}]},
                            {'id': 'button-name', 'impact': 'moderate', 'description': 'Button name missing', 'nodes': [{'target': ['button.icon']}]},
                        ]
                    }
                ),
                encoding='utf-8',
            )
            baseline_json.write_text(
                json.dumps(
                    {
                        'findings': [
                            {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
                            {'rule_id': 'label', 'changed_target': 'input#email', 'status': 'open'},
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
            transitions = payload['run_meta']['baseline_diff']['debt_transitions']
            self.assertEqual(transitions['new']['count'], 1)
            self.assertEqual(transitions['accepted']['count'], 1)
            self.assertEqual(transitions['retired']['count'], 1)
            findings = {item['rule_id']: item for item in payload['findings']}
            self.assertEqual(findings['button-name']['debt_state'], 'new')
            self.assertEqual(findings['image-alt']['debt_state'], 'accepted')
            self.assertEqual(payload['summary']['debt_transitions']['retired']['count'], 1)

    def test_run_accessibility_audit_waiver_expiry_warn_mode_keeps_exit_zero(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm32-waiver-warn'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        html_path = test_dir / 'sample.html'
        output_dir = test_dir / 'out'
        axe_json = test_dir / 'axe.json'
        baseline_json = test_dir / 'baseline.json'
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
                        {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
                    ],
                    'debt_waivers': [
                        {
                            'signature': 'image-alt|img.hero',
                            'owner': 'a11y-owner',
                            'approved_at': '2026-01-01T00:00:00Z',
                            'expires_at': '2026-02-01T00:00:00Z',
                            'reason': 'defer to Q2 redesign',
                        }
                    ],
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
                '--baseline-report',
                str(baseline_json),
                '--waiver-expiry-mode',
                'warn',
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
        self.assertEqual(payload['run_meta']['waiver_gate']['mode'], 'warn')
        self.assertEqual(payload['run_meta']['waiver_gate']['expired_count'], 1)
        self.assertFalse(payload['run_meta']['waiver_gate']['failed'])

    def test_run_accessibility_audit_waiver_expiry_fail_mode_blocks_release_gate(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm32-waiver-fail'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        html_path = test_dir / 'sample.html'
        output_dir = test_dir / 'out'
        axe_json = test_dir / 'axe.json'
        baseline_json = test_dir / 'baseline.json'
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
                        {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
                    ],
                    'debt_waivers': [
                        {
                            'signature': 'image-alt|img.hero',
                            'owner': 'a11y-owner',
                            'approved_at': '2026-01-01T00:00:00Z',
                            'expires_at': '2026-02-01T00:00:00Z',
                            'reason': 'defer to Q2 redesign',
                        }
                    ],
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
                '--baseline-report',
                str(baseline_json),
                '--waiver-expiry-mode',
                'fail',
                '--mock-axe-json',
                str(axe_json),
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 45, completed.stdout + completed.stderr)
        payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
        self.assertTrue(payload['run_meta']['waiver_gate']['failed'])
        self.assertEqual(payload['run_meta']['waiver_gate']['exit_code'], 45)

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

    def test_run_accessibility_audit_fail_on_new_only_ignores_persistent_higher_severity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            baseline_json = Path(tmp) / 'baseline.json'
            html_path.write_text('<!doctype html><html><body><img class="hero" src="hero.png"><button class="icon"></button></body></html>', encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Image alt missing', 'nodes': [{'target': ['img.hero']}]},
                            {'id': 'button-name', 'impact': 'moderate', 'description': 'Button name missing', 'nodes': [{'target': ['button.icon']}]},
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
            self.assertEqual(payload['run_meta']['baseline_diff']['introduced_count'], 1)
            self.assertEqual(payload['run_meta']['policy_gate']['evaluated_findings'], 1)
            self.assertFalse(payload['run_meta']['policy_gate']['failed'])

    def test_run_accessibility_audit_fail_on_new_only_applies_threshold_to_introduced_mix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / 'sample.html'
            output_dir = Path(tmp) / 'out'
            axe_json = Path(tmp) / 'axe.json'
            baseline_json = Path(tmp) / 'baseline.json'
            html_path.write_text('<!doctype html><html><body><img class="hero" src="hero.png"><button class="icon"></button></body></html>', encoding='utf-8')
            axe_json.write_text(
                json.dumps(
                    {
                        'violations': [
                            {'id': 'image-alt', 'impact': 'serious', 'description': 'Image alt missing', 'nodes': [{'target': ['img.hero']}]},
                            {'id': 'button-name', 'impact': 'moderate', 'description': 'Button name missing', 'nodes': [{'target': ['button.icon']}]},
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
                    'moderate',
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
            self.assertEqual(completed.returncode, 44, completed.stdout + completed.stderr)
            payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
            self.assertEqual(payload['run_meta']['baseline_diff']['introduced_signatures'], ['button-name|button.icon'])
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


    def test_run_accessibility_audit_cli_contract_for_summary_sarif_baseline_and_cap(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm23-cli-contract-test'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        html_path = test_dir / 'sample.html'
        output_dir = test_dir / 'out'
        axe_json = test_dir / 'axe.json'
        baseline_json = test_dir / 'baseline.json'
        html_path.write_text('<!doctype html><html><body><img class="hero" src="hero.png"><button class="icon"></button></body></html>', encoding='utf-8')
        axe_json.write_text(
            json.dumps(
                {
                    'violations': [
                        {'id': 'image-alt', 'impact': 'serious', 'description': 'Image alt missing', 'nodes': [{'target': ['img.hero']}]},
                        {'id': 'button-name', 'impact': 'moderate', 'description': 'Button name missing', 'nodes': [{'target': ['button.icon']}]},
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
                '--report-format',
                'sarif',
                '--summary-only',
                '--sort-findings',
                'rule',
                '--max-findings',
                '1',
                '--fail-on',
                'moderate',
                '--fail-on-new-only',
                '--baseline-report',
                str(baseline_json),
                '--baseline-selector-canonicalization',
                'basic',
                '--policy-preset',
                'legacy',
                '--mock-axe-json',
                str(axe_json),
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 44, completed.stdout + completed.stderr)
        compact = json.loads(completed.stdout.strip())
        self.assertEqual(compact['status'], 'failed')
        self.assertEqual(compact['policy_gate']['scope'], 'introduced-only')
        self.assertEqual(compact['policy_gate']['exit_code'], 44)
        self.assertEqual(compact['findings_cap']['truncated'], 1)
        self.assertEqual(compact['baseline_diff']['introduced_count'], 1)
        self.assertEqual(compact['scanner_capabilities']['available_scanners'], ['axe'])
        self.assertEqual(compact['scanner_capabilities']['available_rule_count'], 2)
        self.assertTrue((output_dir / 'schemas' / 'wcag-report-1.0.0.schema.json').exists())
        self.assertTrue((output_dir / 'wcag-report.sarif').exists())
        sarif = json.loads((output_dir / 'wcag-report.sarif').read_text(encoding='utf-8'))
        self.assertEqual(len(sarif['runs'][0]['results']), 1)
        self.assertEqual(sarif['runs'][0]['results'][0]['ruleId'], 'button-name')

    def test_run_accessibility_audit_summary_only_prints_compact_json(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm23-summary-only-test'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        html_path = test_dir / 'sample.html'
        output_dir = test_dir / 'out'
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
        payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['report_schema']['version'], '1.0.0')
        self.assertEqual(payload['run_meta']['report_schema_version'], '1.0.0')
        self.assertTrue((output_dir / 'schemas' / 'wcag-report-1.0.0.schema.json').exists())
        self.assertIn('machine_output', compact)

    def test_run_accessibility_audit_lists_policy_presets_without_target(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm24-policy-presets-test'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        completed = subprocess.run(
            [
                sys.executable,
                'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                '--list-policy-presets',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        names = [item['name'] for item in payload['presets']]
        self.assertIn('strict', names)
        self.assertIn('legacy', names)

    def test_run_accessibility_audit_summary_only_includes_policy_effective_when_requested(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm24-explain-policy-test'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        html_path = test_dir / 'sample.html'
        output_dir = test_dir / 'out'
        axe_json = test_dir / 'axe.json'
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
                '--summary-only',
                '--explain-policy',
                '--policy-preset',
                'legacy',
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
        compact = json.loads(completed.stdout.strip())
        self.assertIn('policy_effective', compact)
        self.assertEqual(compact['policy_effective']['preset'], 'legacy')
        self.assertEqual(compact['policy_effective']['fail_on'], 'serious')
        self.assertEqual(compact['policy_effective']['sources']['fail_on'], 'policy-preset')
        payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
        self.assertIn('policy_effective', payload['run_meta'])

    def test_run_accessibility_audit_policy_bundle_is_reflected_in_effective_policy(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm30-policy-bundle-effective-test'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        html_path = test_dir / 'sample.html'
        output_dir = test_dir / 'out'
        html_path.write_text('<!doctype html><html><body></body></html>', encoding='utf-8')

        completed = subprocess.run(
            [
                sys.executable,
                'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                '--target',
                str(html_path),
                '--output-dir',
                str(output_dir),
                '--summary-only',
                '--explain-policy',
                '--policy-bundle',
                'legacy-content',
                '--skip-axe',
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        compact = json.loads(completed.stdout.strip())
        self.assertEqual(compact['policy_effective']['bundle'], 'legacy-content')
        self.assertEqual(compact['policy_effective']['sources']['fail_on'], 'policy-bundle')
        self.assertEqual(compact['policy_effective']['sources']['ignore_rules']['color-contrast'], 'policy-bundle')
        payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['run_meta']['policy_bundle']['name'], 'legacy-content')

    def test_run_accessibility_audit_policy_config_rejects_unknown_keys(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm25-policy-config-validation-test'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        html_path = test_dir / 'sample.html'
        output_dir = test_dir / 'out'
        policy_json = test_dir / 'policy.json'
        html_path.write_text('<!doctype html><html><body></body></html>', encoding='utf-8')
        policy_json.write_text(
            json.dumps({'fail_on': 'serious', 'unknown_key': True}),
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
                '--policy-config',
                str(policy_json),
                '--skip-axe',
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('unsupported keys: unknown_key', completed.stderr + completed.stdout)

    def test_run_accessibility_audit_writes_effective_policy_artifact(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm25-effective-policy-artifact-test'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        html_path = test_dir / 'sample.html'
        output_dir = test_dir / 'out'
        policy_json = test_dir / 'policy.json'
        html_path.write_text('<!doctype html><html><body></body></html>', encoding='utf-8')
        policy_json.write_text(
            json.dumps({'fail_on': 'moderate', 'ignore_rules': ['color-contrast']}),
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
                '--policy-preset',
                'legacy',
                '--policy-config',
                str(policy_json),
                '--write-effective-policy',
                '--skip-axe',
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        artifact_path = output_dir / 'wcag-effective-policy.json'
        self.assertTrue(artifact_path.exists())
        artifact = json.loads(artifact_path.read_text(encoding='utf-8'))
        self.assertEqual(artifact['fail_on'], 'moderate')
        self.assertEqual(artifact['sources']['fail_on'], 'policy-config')
        self.assertEqual(artifact['sources']['ignore_rules']['meta-viewport'], 'policy-preset')
        self.assertEqual(artifact['sources']['ignore_rules']['color-contrast'], 'policy-config')
        payload = json.loads((output_dir / 'wcag-report.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['run_meta']['effective_policy_artifact'], str(artifact_path))

    def test_run_accessibility_audit_emits_artifact_manifest_with_checksums(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm31-artifact-manifest-test'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        html_path = test_dir / 'sample.html'
        output_dir = test_dir / 'out'
        html_path.write_text('<!doctype html><html><body><img src="hero.png"></body></html>', encoding='utf-8')

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
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        manifest = json.loads((output_dir / 'artifact-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['generator']['name'], 'run_accessibility_audit.py')
        self.assertGreaterEqual(manifest['artifact_count'], 3)
        kinds = [item['kind'] for item in manifest['artifacts']]
        self.assertIn('machine-report-json', kinds)
        self.assertIn('markdown-report', kinds)
        for item in manifest['artifacts']:
            self.assertEqual(len(item['sha256']), 64)
            self.assertGreaterEqual(item['size_bytes'], 1)

    def test_run_accessibility_audit_baseline_hash_chain_verification_passes(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm31-baseline-hash-chain-pass'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        html_path = test_dir / 'sample.html'
        baseline_out = test_dir / 'baseline-out'
        compare_out = test_dir / 'compare-out'
        axe_json = test_dir / 'axe.json'
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

        baseline = subprocess.run(
            [
                sys.executable,
                'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                '--target',
                str(html_path),
                '--output-dir',
                str(baseline_out),
                '--baseline-evidence-mode',
                'hash',
                '--mock-axe-json',
                str(axe_json),
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(baseline.returncode, 0, baseline.stdout + baseline.stderr)

        verify = subprocess.run(
            [
                sys.executable,
                'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                '--target',
                str(html_path),
                '--output-dir',
                str(compare_out),
                '--baseline-report',
                str(baseline_out / 'wcag-report.json'),
                '--baseline-evidence-mode',
                'hash-chain',
                '--mock-axe-json',
                str(axe_json),
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        payload = json.loads((compare_out / 'wcag-report.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['run_meta']['baseline_evidence']['mode'], 'hash-chain')
        self.assertTrue(payload['run_meta']['baseline_evidence']['baseline_verification']['verified'])
        self.assertIn('chain_hash', payload['run_meta']['baseline_evidence'])

    def test_run_accessibility_audit_baseline_hash_verification_rejects_tampered_report(self) -> None:
        test_dir = self.repo_root / 'automation-work' / 'm31-baseline-hash-fail'
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        html_path = test_dir / 'sample.html'
        baseline_out = test_dir / 'baseline-out'
        compare_out = test_dir / 'compare-out'
        axe_json = test_dir / 'axe.json'
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

        baseline = subprocess.run(
            [
                sys.executable,
                'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                '--target',
                str(html_path),
                '--output-dir',
                str(baseline_out),
                '--baseline-evidence-mode',
                'hash',
                '--mock-axe-json',
                str(axe_json),
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(baseline.returncode, 0, baseline.stdout + baseline.stderr)

        tampered_path = baseline_out / 'wcag-report.json'
        tampered_payload = json.loads(tampered_path.read_text(encoding='utf-8'))
        tampered_payload['findings'].append(
            {'rule_id': 'button-name', 'changed_target': 'button.icon', 'status': 'open'}
        )
        tampered_path.write_text(json.dumps(tampered_payload, ensure_ascii=False, indent=2), encoding='utf-8')

        verify = subprocess.run(
            [
                sys.executable,
                'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
                '--target',
                str(html_path),
                '--output-dir',
                str(compare_out),
                '--baseline-report',
                str(tampered_path),
                '--baseline-evidence-mode',
                'hash',
                '--mock-axe-json',
                str(axe_json),
                '--skip-lighthouse',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(verify.returncode, 0)
        self.assertIn('baseline evidence verification failed', verify.stdout + verify.stderr)

if __name__ == '__main__':
    unittest.main()

