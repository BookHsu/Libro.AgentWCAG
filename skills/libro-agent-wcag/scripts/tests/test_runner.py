#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from run_accessibility_audit import (
    DEFAULT_TIMEOUT_SECONDS,
    _resolve_target_for_scanners,
    _run_command,
    _try_run_axe,
    _try_run_lighthouse,
    parse_args,
    run_preflight_checks,
)


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

    def test_cli_has_timeout_default(self) -> None:
        original = sys.argv
        sys.argv = ["run_accessibility_audit.py", "--target", "https://example.com"]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.timeout, DEFAULT_TIMEOUT_SECONDS)

    def test_cli_accepts_mock_scanner_json_arguments(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--mock-axe-json",
            "axe.json",
            "--mock-lighthouse-json",
            "lighthouse.json",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.mock_axe_json, "axe.json")
        self.assertEqual(args.mock_lighthouse_json, "lighthouse.json")

    def test_cli_accepts_dry_run_and_preflight_flags(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--execution-mode",
            "apply-fixes",
            "--dry-run",
            "--preflight-only",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertTrue(args.dry_run)
        self.assertTrue(args.preflight_only)

    @patch("run_accessibility_audit.subprocess.run")
    def test_run_command_returns_stdout_on_success(self, mock_run) -> None:
        mock_run.return_value = type("Result", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        ok, result = _run_command(["npx", "tool"], timeout_seconds=30)
        self.assertTrue(ok)
        self.assertEqual(result, "ok")

    @patch("run_accessibility_audit.subprocess.run")
    def test_run_command_returns_stderr_on_failure(self, mock_run) -> None:
        mock_run.return_value = type("Result", (), {"returncode": 1, "stdout": "out", "stderr": "boom"})()
        ok, result = _run_command(["npx", "tool"], timeout_seconds=30)
        self.assertFalse(ok)
        self.assertEqual(result, "boom")

    @patch("run_accessibility_audit.subprocess.run")
    def test_run_command_returns_timeout_message(self, mock_run) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["npx", "tool"], timeout=7)
        ok, result = _run_command(["npx", "tool"], timeout_seconds=7)
        self.assertFalse(ok)
        self.assertEqual(result, "command timed out after 7 seconds")

    def test_try_run_axe_returns_error_when_output_missing(self) -> None:
        output_dir = Path(__file__).parent / "fixtures"
        with patch("run_accessibility_audit._run_command", return_value=(True, "")):
            payload, err = _try_run_axe("https://example.com", output_dir, timeout_seconds=15)
        self.assertIsNone(payload)
        self.assertEqual(err, "axe did not generate output json")

    def test_try_run_lighthouse_returns_error_when_output_missing(self) -> None:
        output_dir = Path(__file__).parent / "fixtures"
        with patch("run_accessibility_audit._run_command", return_value=(True, "")):
            payload, err = _try_run_lighthouse("https://example.com", output_dir, timeout_seconds=15)
        self.assertIsNone(payload)
        self.assertEqual(err, "lighthouse did not generate output json")

    @patch("run_accessibility_audit._tool_available", return_value=True)
    @patch("run_accessibility_audit._run_command")
    def test_preflight_returns_ok_when_all_checks_pass(self, mock_run_command, _mock_tool_available) -> None:
        mock_run_command.return_value = (True, "v")
        result = run_preflight_checks(timeout_seconds=5)
        self.assertTrue(result["ok"])
        self.assertTrue(all(item["status"] == "ok" for item in result["checks"]))

    @patch("run_accessibility_audit._tool_available")
    def test_preflight_reports_missing_binary(self, mock_tool_available) -> None:
        mock_tool_available.side_effect = [False, True, True]
        with patch("run_accessibility_audit._run_command", return_value=(True, "v")):
            result = run_preflight_checks(timeout_seconds=5)
        self.assertFalse(result["ok"])
        self.assertEqual(result["checks"][0]["status"], "error")
        self.assertIn("PATH", result["checks"][0]["message"])


if __name__ == "__main__":
    unittest.main()

