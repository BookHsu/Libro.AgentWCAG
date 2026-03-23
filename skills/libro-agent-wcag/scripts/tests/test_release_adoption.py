#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


class ReleaseAdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.workspace_root = cls.repo_root / ".tmp-test" / "release-adoption"

    def _workspace(self, name: str) -> Path:
        workspace = self.workspace_root / name
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def _release_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["LIBRO_AGENTWCAG_SOURCE_REVISION"] = "fedcba9876543210fedcba9876543210fedcba98"
        env["LIBRO_AGENTWCAG_BUILD_TIMESTAMP"] = "2026-03-23T12:00:00Z"
        return env

    def test_release_adoption_smoke_runs_from_packaged_assets(self) -> None:
        workspace = self._workspace("smoke")
        release_dir = workspace / "release"
        summary_path = workspace / "smoke-summary.json"

        package = subprocess.run(
            [
                sys.executable,
                "scripts/package-release.py",
                "--output-dir",
                str(release_dir),
                "--overwrite",
            ],
            cwd=self.repo_root,
            env=self._release_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(package.returncode, 0, package.stdout + package.stderr)

        smoke = subprocess.run(
            [
                sys.executable,
                "scripts/run-release-adoption-smoke.py",
                "--release-dir",
                str(release_dir),
                "--agent",
                "codex",
                "--summary-path",
                str(summary_path),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(smoke.returncode, 0, smoke.stdout + smoke.stderr)

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertTrue(summary["clean_environment_verified"])
        self.assertTrue(summary["checksum_verified"])
        self.assertTrue(summary["doctor_ok"])
        self.assertTrue(summary["doctor_version_consistency_verified"])
        self.assertTrue(summary["doctor_manifest_integrity_verified"])
        self.assertTrue(summary["uninstall_removed_destination"])
        self.assertEqual(summary["installed_product_version"], "0.1.0")
        self.assertEqual(summary["report_product_version"], "0.1.0")
        self.assertEqual(summary["source_revision"], "fedcba9876543210fedcba9876543210fedcba98")

    def test_bootstrap_wrappers_reference_latest_manifest_and_checksum_verification(self) -> None:
        powershell = (self.repo_root / "scripts" / "install-latest.ps1").read_text(encoding="utf-8")
        shell = (self.repo_root / "scripts" / "install-latest.sh").read_text(encoding="utf-8")

        for content in (powershell, shell):
            self.assertIn("latest-release.json", content)
            self.assertIn("release-manifest.json", content)
            self.assertIn("sha256", content.lower())
            self.assertIn("install-agent.py", content)


if __name__ == "__main__":
    unittest.main()
