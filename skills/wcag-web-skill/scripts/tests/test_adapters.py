#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


class AdapterContractTests(unittest.TestCase):
    def _read(self, *parts: str) -> str:
        root = Path(__file__).resolve().parents[2]
        return (root.joinpath(*parts)).read_text(encoding="utf-8")

    def test_v1_adapters_require_same_contract_keys(self) -> None:
        openai_template = self._read("adapters", "openai-codex", "prompt-template.md")
        claude_template = self._read("adapters", "claude", "prompt-template.md")
        required_keys = [
            "task_mode",
            "execution_mode",
            "wcag_version",
            "conformance_level",
            "target",
            "output_language",
        ]
        for key in required_keys:
            self.assertIn(key, openai_template)
            self.assertIn(key, claude_template)

    def test_v1_adapters_require_dual_output(self) -> None:
        openai_template = self._read("adapters", "openai-codex", "prompt-template.md")
        claude_template = self._read("adapters", "claude", "prompt-template.md")
        for token in ["Markdown", "JSON"]:
            self.assertIn(token, openai_template)
            self.assertIn(token, claude_template)

    def test_v2_adapters_require_same_contract_keys(self) -> None:
        gemini_template = self._read("adapters", "gemini", "prompt-template.md")
        copilot_template = self._read("adapters", "copilot", "prompt-template.md")
        required_keys = [
            "task_mode",
            "execution_mode",
            "wcag_version",
            "conformance_level",
            "target",
            "output_language",
        ]
        for key in required_keys:
            self.assertIn(key, gemini_template)
            self.assertIn(key, copilot_template)

    def test_v2_adapters_require_version_matched_citations(self) -> None:
        gemini_template = self._read("adapters", "gemini", "prompt-template.md")
        copilot_template = self._read("adapters", "copilot", "prompt-template.md")
        self.assertIn("W3C citation URL that matches the selected WCAG version", gemini_template)
        self.assertIn("version-matched W3C Understanding links", copilot_template)

    def test_all_adapters_default_to_suggest_only(self) -> None:
        templates = [
            self._read("adapters", "openai-codex", "prompt-template.md"),
            self._read("adapters", "claude", "prompt-template.md"),
            self._read("adapters", "gemini", "prompt-template.md"),
            self._read("adapters", "copilot", "prompt-template.md"),
        ]
        for template in templates:
            self.assertIn("suggest-only", template)
            self.assertIn("apply-fixes", template)
            self.assertIn("audit-only", template)


if __name__ == "__main__":
    unittest.main()
