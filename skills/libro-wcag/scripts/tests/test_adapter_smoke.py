#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AdapterSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.skill_root = cls.repo_root / 'skills' / 'libro-wcag'

    def _read(self, *parts: str) -> str:
        return (self.skill_root.joinpath(*parts)).read_text(encoding='utf-8')

    def test_all_adapters_ship_usage_failure_and_e2e_examples(self) -> None:
        adapter_expectations = {
            'openai-codex': '$libro-wcag',
            'claude': 'project or system prompt',
            'gemini': 'custom instruction',
            'copilot': 'instruction file',
        }
        for adapter, token in adapter_expectations.items():
            with self.subTest(adapter=adapter):
                usage = self._read('adapters', adapter, 'usage-example.md')
                failure = self._read('adapters', adapter, 'failure-guide.md')
                e2e = self._read('adapters', adapter, 'e2e-example.md')
                self.assertIn('## Install', usage)
                self.assertIn('## Smoke Check', usage)
                self.assertIn(token, usage)
                self.assertIn('Recovery Steps', failure)
                self.assertIn('Expected Result', e2e)

    def test_installed_manifest_points_to_adapter_neighbor_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'codex-skill'
            completed = subprocess.run(
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
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            manifest = json.loads((destination / 'install-manifest.json').read_text(encoding='utf-8'))
            self.assertTrue((destination / manifest['usage_example']).exists())
            self.assertTrue((destination / manifest['failure_guide']).exists())
            self.assertTrue((destination / manifest['e2e_example']).exists())
            self.assertEqual(manifest['adapter_prompt'], 'adapters/openai-codex/prompt-template.md')

    def test_adapter_docs_align_with_prompt_templates(self) -> None:
        pairs = [
            ('openai-codex', 'Use $libro-wcag'),
            ('claude', 'Invoke libro-wcag core contract'),
            ('gemini', 'Follow the libro-wcag core contract exactly'),
            ('copilot', 'Use the libro-wcag shared contract'),
        ]
        for adapter, prompt_token in pairs:
            with self.subTest(adapter=adapter):
                prompt = self._read('adapters', adapter, 'prompt-template.md')
                usage = self._read('adapters', adapter, 'usage-example.md')
                failure = self._read('adapters', adapter, 'failure-guide.md')
                e2e = self._read('adapters', adapter, 'e2e-example.md')
                self.assertIn(prompt_token, prompt)
                self.assertIn('task_mode', usage)
                self.assertIn('execution_mode', usage)
                self.assertIn('apply-fixes', failure)
                self.assertIn('canonical', e2e.lower())

    def test_adapter_docs_cover_first_run_snapshots_and_downgrade_examples(self) -> None:
        adapters = ('openai-codex', 'claude', 'gemini', 'copilot')
        for adapter in adapters:
            with self.subTest(adapter=adapter):
                usage = self._read('adapters', adapter, 'usage-example.md')
                failure = self._read('adapters', adapter, 'failure-guide.md')
                e2e = self._read('adapters', adapter, 'e2e-example.md')
                self.assertIn('## First-Run Output Example', usage)
                self.assertIn('remediation_lifecycle', usage)
                self.assertIn('## Output Snapshot', e2e)
                self.assertIn('remediation_lifecycle', e2e)
                self.assertIn('manual_required_count', e2e)
                self.assertIn('## Downgrade And Escalation Example', failure)
                self.assertIn('downgrade_reason', failure)


if __name__ == '__main__':
    unittest.main()
