#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class RepoInvocationTests(unittest.TestCase):
    def test_repo_root_discovery_command_succeeds(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "skills/libro-wcag/scripts/tests",
                "-p",
                "test_runner.py",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_pip_check_reports_no_broken_requirements(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "check",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("No broken requirements found", completed.stdout)


if __name__ == "__main__":
    unittest.main()
