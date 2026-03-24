#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from remediation_library import get_strategy
from wcag_workflow import normalize_report, resolve_contract, to_markdown_table


class MatrixCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]

    def _install(self, agent: str, destination: Path, force: bool = False) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            'scripts/install-agent.py',
            '--agent',
            agent,
            '--dest',
            str(destination),
        ]
        if force:
            command.append('--force')
        return subprocess.run(
            command,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    def _doctor(self, agent: str, destination: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                'scripts/doctor-agent.py',
                '--agent',
                agent,
                '--dest',
                str(destination),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_decision_table_modes_resolve_to_expected_contract(self) -> None:
        cases = [
            ('create', 'audit-only'),
            ('create', 'suggest-only'),
            ('create', 'apply-fixes'),
            ('modify', 'audit-only'),
            ('modify', 'suggest-only'),
            ('modify', 'apply-fixes'),
        ]
        for task_mode, execution_mode in cases:
            with self.subTest(task_mode=task_mode, execution_mode=execution_mode):
                contract = resolve_contract(
                    {
                        'task_mode': task_mode,
                        'execution_mode': execution_mode,
                        'target': 'https://example.com',
                    }
                )
                report = normalize_report(contract, {'violations': []}, {'audits': {}}, None, None)
                self.assertEqual(report['target']['task_mode'], task_mode)
                self.assertEqual(report['run_meta']['execution_mode'], execution_mode)
                self.assertFalse(report['run_meta']['files_modified'])

    def test_language_fallback_defaults_to_english_for_unknown_locale(self) -> None:
        contract = resolve_contract({'target': 'https://example.com', 'output_language': 'fr-FR'})
        report = normalize_report(contract, {'violations': []}, {'audits': {}}, None, None)
        markdown = report['summary']['change_summary']
        self.assertIsInstance(markdown, list)
        table = to_markdown_table(report)
        self.assertIn('Execution mode', table)

    def test_volume_and_stress_like_report_generation_handles_many_findings(self) -> None:
        contract = resolve_contract({'target': 'https://example.com'})
        axe_data = {
            'violations': [
                {
                    'id': 'image-alt',
                    'impact': 'serious',
                    'description': 'Images must have alternate text',
                    'nodes': [{'target': [f'img.item-{index}']}],
                }
                for index in range(250)
            ]
        }
        started = time.perf_counter()
        report = normalize_report(contract, axe_data, {'audits': {}}, None, None)
        elapsed = time.perf_counter() - started
        self.assertEqual(len(report['findings']), 250)
        self.assertLess(elapsed, 5.0)

    def test_endurance_like_repeated_install_doctor_uninstall_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'codex-skill'
            for _ in range(3):
                install = self._install('codex', destination)
                self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
                doctor = self._doctor('codex', destination)
                self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
                uninstall = subprocess.run(
                    [
                        sys.executable,
                        'scripts/uninstall-agent.py',
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
                self.assertEqual(uninstall.returncode, 0, uninstall.stdout + uninstall.stderr)
                self.assertFalse(destination.exists())

    def test_recovery_path_recovers_broken_install_with_force_reinstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'gemini-skill'
            install = self._install('gemini', destination)
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            (destination / 'SKILL.md').unlink()
            unhealthy = self._doctor('gemini', destination)
            self.assertNotEqual(unhealthy.returncode, 0)
            reinstall = self._install('gemini', destination, force=True)
            self.assertEqual(reinstall.returncode, 0, reinstall.stdout + reinstall.stderr)
            healthy = self._doctor('gemini', destination)
            self.assertEqual(healthy.returncode, 0, healthy.stdout + healthy.stderr)

    def test_concurrent_installs_to_independent_destinations_succeed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            def run(agent: str) -> tuple[str, int, Path]:
                destination = base / agent / 'bundle'
                completed = self._install(agent, destination)
                return agent, completed.returncode, destination

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(run, ['claude', 'copilot']))

            for agent, code, destination in results:
                self.assertEqual(code, 0, agent)
                manifest = json.loads((destination / 'install-manifest.json').read_text(encoding='utf-8'))
                self.assertEqual(manifest['agent'], agent)

    def test_configuration_matrix_for_agents_and_force_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for agent in ('codex', 'claude', 'gemini', 'copilot'):
                with self.subTest(agent=agent):
                    destination = Path(tmp) / agent
                    first = self._install(agent, destination)
                    self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
                    second = self._install(agent, destination)
                    self.assertNotEqual(second.returncode, 0)
                    forced = self._install(agent, destination, force=True)
                    self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)

    def test_remediation_library_supports_data_driven_rule_selection(self) -> None:
        expectations = {
            'image-alt': ('high', True),
            'label': ('high', True),
            'color-contrast': ('high', False),
            'unknown-rule': ('medium', False),
            'region': ('medium', False),
            'skip-link': ('high', False),
            'tabindex': ('high', False),
        }
        for rule_id, (priority, auto_fix_supported) in expectations.items():
            with self.subTest(rule_id=rule_id):
                strategy = get_strategy(rule_id)
                self.assertEqual(strategy['priority'], priority)
                self.assertEqual(strategy['auto_fix_supported'], auto_fix_supported)


if __name__ == '__main__':
    unittest.main()

