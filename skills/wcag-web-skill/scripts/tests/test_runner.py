#!/usr/bin/env python3

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from run_accessibility_audit import _resolve_target_for_scanners


class RunnerTests(unittest.TestCase):
    def test_existing_local_path_is_converted_to_file_uri(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "index.html"
            html_path.write_text("<!doctype html><title>x</title>", encoding="utf-8")
            resolved = _resolve_target_for_scanners(str(html_path))
            self.assertTrue(resolved.startswith("file:///"))

    def test_http_target_is_preserved(self) -> None:
        target = "https://example.com/page"
        self.assertEqual(_resolve_target_for_scanners(target), target)

    def test_existing_file_uri_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "index.html"
            html_path.write_text("<!doctype html><title>x</title>", encoding="utf-8")
            target = html_path.resolve().as_uri()
            self.assertEqual(_resolve_target_for_scanners(target), target)

    def test_invalid_scheme_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _resolve_target_for_scanners("ftp://example.com/file.html")

    def test_missing_local_file_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _resolve_target_for_scanners("missing-file.html")


if __name__ == "__main__":
    unittest.main()
