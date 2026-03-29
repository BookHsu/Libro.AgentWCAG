#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


class AutomationDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]

    def test_source_checkout_does_not_ship_docs_automations_directory(self) -> None:
        self.assertFalse((self.repo_root / 'docs' / 'automations').exists())

    def test_testing_docs_remain_in_formal_docs_tree(self) -> None:
        self.assertTrue((self.repo_root / 'docs' / 'testing' / 'testing-playbook.md').is_file())
        self.assertTrue((self.repo_root / 'docs' / 'testing' / 'test-matrix.md').is_file())


if __name__ == '__main__':
    unittest.main()
