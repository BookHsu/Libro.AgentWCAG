#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RepoScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]

    def _decode_json_stream(self, payload: str) -> list[dict[str, object]]:
        decoder = json.JSONDecoder()
        index = 0
        items: list[dict[str, object]] = []
        while index < len(payload):
            while index < len(payload) and payload[index].isspace():
                index += 1
            if index >= len(payload):
                break
            item, index = decoder.raw_decode(payload, index)
            items.append(item)
        return items

    def test_validate_skill_cli_accepts_skill_directory(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/validate_skill.py',
                'skills/libro-agent-wcag',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn('Skill is valid!', completed.stdout)

    def test_validate_skill_cli_rejects_missing_directory(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/validate_skill.py',
                'skills/missing-skill',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('Missing SKILL.md', completed.stderr + completed.stdout)

    def test_doctor_all_reports_each_supported_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'all',
                    '--dest',
                    tmp,
                ],
                cwd=self.repo_root,
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
                    'all',
                    '--dest',
                    tmp,
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            payloads = self._decode_json_stream(doctor.stdout)
            self.assertEqual([item['agent'] for item in payloads], ['codex', 'claude', 'gemini', 'copilot'])
            self.assertTrue(all(item['ok'] for item in payloads))

    def test_force_reinstall_replaces_existing_installation(self) -> None:
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
            extra_file = destination / 'local.txt'
            extra_file.write_text('stale', encoding='utf-8')
            reinstall = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'codex',
                    '--dest',
                    str(destination),
                    '--force',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(reinstall.returncode, 0, reinstall.stdout + reinstall.stderr)
            self.assertFalse(extra_file.exists())
            self.assertTrue((destination / 'install-manifest.json').exists())

    def test_realistic_validation_smoke_script_exists_and_references_mock_flow(self) -> None:
        script = (self.repo_root / 'scripts' / 'run-realistic-validation-smoke.py').read_text(encoding='utf-8')
        self.assertIn('run_accessibility_audit.py', script)
        self.assertIn('--mock-axe-json', script)
        self.assertIn('--mock-lighthouse-json', script)
        self.assertIn('wcag-fixes.sample.diff', script)
    def test_install_agent_ps1_wrapper_invokes_python_installer(self) -> None:
        wrapper = (self.repo_root / 'scripts' / 'install-agent.ps1').read_text(encoding='utf-8')
        self.assertIn('install-agent.py', wrapper)
        self.assertIn("[ValidateSet('codex','claude','gemini','copilot','all')]", wrapper)
        self.assertIn('python $script @arguments', wrapper)

    def test_install_agent_sh_wrapper_invokes_python_installer(self) -> None:
        wrapper = (self.repo_root / 'scripts' / 'install-agent.sh').read_text(encoding='utf-8')
        self.assertIn('install-agent.py', wrapper)
        self.assertIn('codex|claude|gemini|copilot|all', wrapper)
        self.assertIn('python "$SCRIPT_DIR/install-agent.py" --agent "$AGENT" "$@"', wrapper)


if __name__ == '__main__':
    unittest.main()

