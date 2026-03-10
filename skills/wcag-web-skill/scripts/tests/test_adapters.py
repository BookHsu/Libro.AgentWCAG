#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


class AdapterContractTests(unittest.TestCase):
    def test_v1_adapters_require_same_contract_keys(self) -> None:
        root = Path(__file__).resolve().parents[2]
        openai_template = (root / "adapters" / "openai-codex" / "prompt-template.md").read_text(
            encoding="utf-8"
        )
        claude_template = (root / "adapters" / "claude" / "prompt-template.md").read_text(
            encoding="utf-8"
        )
        required_keys = [
            "task_mode",
            "wcag_version",
            "conformance_level",
            "target",
            "output_language",
        ]
        for key in required_keys:
            self.assertIn(key, openai_template)
            self.assertIn(key, claude_template)

    def test_v1_adapters_require_dual_output(self) -> None:
        root = Path(__file__).resolve().parents[2]
        openai_template = (root / "adapters" / "openai-codex" / "prompt-template.md").read_text(
            encoding="utf-8"
        )
        claude_template = (root / "adapters" / "claude" / "prompt-template.md").read_text(
            encoding="utf-8"
        )
        for token in ["Markdown", "JSON"]:
            self.assertIn(token, openai_template)
            self.assertIn(token, claude_template)


if __name__ == "__main__":
    unittest.main()

