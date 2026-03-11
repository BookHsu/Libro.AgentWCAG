#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class InstallAgentTests(unittest.TestCase):
    def test_installer_creates_manifest_for_claude(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'claude-skill'
            completed = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'claude',
                    '--dest',
                    str(destination),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            manifest = json.loads((destination / 'install-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['agent'], 'claude')
            self.assertEqual(manifest['adapter_prompt'], 'adapters/claude/prompt-template.md')
            self.assertIn('doctor-agent.py', manifest['doctor_command'])

    def test_installer_can_install_all_agents(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'all',
                    '--dest',
                    tmp,
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            for agent in ('codex', 'claude', 'gemini', 'copilot'):
                self.assertTrue((Path(tmp) / agent / 'libro-agent-wcag' / 'install-manifest.json').exists())

    def test_installer_requires_force_to_replace(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'codex-skill'
            destination.mkdir(parents=True)
            completed = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'codex',
                    '--dest',
                    str(destination),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)

    def test_doctor_reports_valid_installation(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
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
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            doctor = subprocess.run(
                [
                    sys.executable,
                    'scripts/doctor-agent.py',
                    '--agent',
                    'gemini',
                    '--dest',
                    str(destination),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            payload = json.loads(doctor.stdout)
            self.assertTrue(payload['ok'])

    def test_uninstall_removes_destination(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
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
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            uninstall = subprocess.run(
                [
                    sys.executable,
                    'scripts/uninstall-agent.py',
                    '--agent',
                    'codex',
                    '--dest',
                    str(destination),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(uninstall.returncode, 0, uninstall.stdout + uninstall.stderr)
            self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
