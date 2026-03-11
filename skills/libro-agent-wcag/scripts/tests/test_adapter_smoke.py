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
        cls.skill_root = cls.repo_root / 'skills' / 'libro-agent-wcag'

    def _read(self, *parts: str) -> str:
        return (self.skill_root.joinpath(*parts)).read_text(encoding='utf-8')

    def test_all_adapters_ship_usage_examples(self) -> None:
        adapter_expectations = {
            'openai-codex': '$libro-agent-wcag',
            'claude': 'project or system prompt',
            'gemini': 'custom instruction',
            'copilot': 'instruction file',
        }
        for adapter, token in adapter_expectations.items():
            with self.subTest(adapter=adapter):
                content = self._read('adapters', adapter, 'usage-example.md')
                self.assertIn('## Install', content)
                self.assertIn('## Smoke Check', content)
                self.assertIn(token, content)

    def test_installed_manifest_points_to_adapter_usage_example_neighbor(self) -> None:
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
            usage_example = destination / 'adapters' / 'openai-codex' / 'usage-example.md'
            self.assertTrue(usage_example.exists())
            self.assertEqual(manifest['adapter_prompt'], 'adapters/openai-codex/prompt-template.md')

    def test_adapter_usage_examples_align_with_prompt_templates(self) -> None:
        pairs = [
            ('openai-codex', 'Use $libro-agent-wcag'),
            ('claude', 'Invoke libro-agent-wcag core contract'),
            ('gemini', 'Follow the libro-agent-wcag core contract exactly'),
            ('copilot', 'Use the libro-agent-wcag shared contract'),
        ]
        for adapter, prompt_token in pairs:
            with self.subTest(adapter=adapter):
                prompt = self._read('adapters', adapter, 'prompt-template.md')
                example = self._read('adapters', adapter, 'usage-example.md')
                self.assertIn(prompt_token, prompt)
                self.assertIn('task_mode', example)
                self.assertIn('execution_mode', example)


if __name__ == '__main__':
    unittest.main()
