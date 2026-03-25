#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
import unittest
import zipfile
from pathlib import Path


class ReleasePackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.workspace_root = cls.repo_root / ".tmp-test" / "release-packaging"
        cls.product_version = tomllib.loads((cls.repo_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

    def _workspace(self, name: str) -> Path:
        workspace = self.workspace_root / name
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def _run_packager(self, output_dir: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["LIBRO_AGENTWCAG_SOURCE_REVISION"] = "0123456789abcdef0123456789abcdef01234567"
        env["LIBRO_AGENTWCAG_BUILD_TIMESTAMP"] = "2026-03-23T00:00:00Z"
        return subprocess.run(
            [
                sys.executable,
                "scripts/package-release.py",
                "--output-dir",
                str(output_dir),
                "--overwrite",
            ],
            cwd=self.repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_package_release_emits_expected_assets_and_contract(self) -> None:
        output_dir = self._workspace("package-assets") / "release"
        completed = self._run_packager(output_dir)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

        manifest_path = output_dir / f"libro-wcag-{self.product_version}-release-manifest.json"
        checksum_path = output_dir / f"libro-wcag-{self.product_version}-sha256sums.txt"
        latest_path = output_dir / "latest-release.json"
        self.assertTrue(manifest_path.exists())
        self.assertTrue(checksum_path.exists())
        self.assertTrue(latest_path.exists())

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        asset_names = {asset["filename"] for asset in manifest["assets"]}
        expected_bundles = {
            f"libro-wcag-{self.product_version}-codex.zip",
            f"libro-wcag-{self.product_version}-claude.zip",
            f"libro-wcag-{self.product_version}-gemini.zip",
            f"libro-wcag-{self.product_version}-copilot.zip",
            f"libro-wcag-{self.product_version}-all-in-one.zip",
        }
        self.assertTrue(expected_bundles.issubset(asset_names))
        self.assertIn(f"libro-wcag-{self.product_version}-install-latest.ps1", asset_names)
        self.assertIn(f"libro-wcag-{self.product_version}-install-latest.sh", asset_names)
        self.assertIn(f"libro-wcag-{self.product_version}-run-release-adoption-smoke.py", asset_names)
        self.assertEqual(manifest["checksum_file"], checksum_path.name)
        self.assertEqual(manifest["latest_pointer"], latest_path.name)

        codex_bundle = next(asset for asset in manifest["assets"] if asset["filename"].endswith("-codex.zip"))
        self.assertEqual(codex_bundle["agent"], "codex")
        self.assertEqual(codex_bundle["bundle_root"], f"libro-wcag-{self.product_version}-codex")

        with zipfile.ZipFile(output_dir / f"libro-wcag-{self.product_version}-codex.zip") as archive:
            names = set(archive.namelist())
            self.assertIn(f"libro-wcag-{self.product_version}-codex/scripts/install-agent.py", names)
            self.assertIn(
                f"libro-wcag-{self.product_version}-codex/skills/libro-wcag/adapters/openai-codex/prompt-template.md",
                names,
            )
            self.assertNotIn(
                f"libro-wcag-{self.product_version}-codex/skills/libro-wcag/adapters/claude/prompt-template.md",
                names,
            )
            self.assertFalse(any("/scripts/tests/" in name for name in names))
            self.assertFalse(any(name.startswith(f"libro-wcag-{self.product_version}-codex/docs/testing/") for name in names))
            self.assertFalse(any(name.startswith(f"libro-wcag-{self.product_version}-codex/docs/archive/") for name in names))

        checksums = checksum_path.read_text(encoding="utf-8")
        self.assertIn(f"*libro-wcag-{self.product_version}-release-manifest.json", checksums)
        self.assertIn("*latest-release.json", checksums)

    def test_package_release_is_deterministic_given_fixed_provenance(self) -> None:
        first_output = self._workspace("deterministic-a") / "release"
        second_output = self._workspace("deterministic-b") / "release"
        first = self._run_packager(first_output)
        second = self._run_packager(second_output)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)

        filenames = [
            f"libro-wcag-{self.product_version}-codex.zip",
            f"libro-wcag-{self.product_version}-claude.zip",
            f"libro-wcag-{self.product_version}-gemini.zip",
            f"libro-wcag-{self.product_version}-copilot.zip",
            f"libro-wcag-{self.product_version}-all-in-one.zip",
            f"libro-wcag-{self.product_version}-install-latest.ps1",
            f"libro-wcag-{self.product_version}-install-latest.sh",
            f"libro-wcag-{self.product_version}-run-release-adoption-smoke.py",
            f"libro-wcag-{self.product_version}-release-manifest.json",
            f"libro-wcag-{self.product_version}-sha256sums.txt",
            "latest-release.json",
        ]
        for filename in filenames:
            with self.subTest(filename=filename):
                self.assertEqual(
                    (first_output / filename).read_bytes(),
                    (second_output / filename).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
