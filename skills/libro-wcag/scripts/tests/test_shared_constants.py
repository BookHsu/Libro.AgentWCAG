#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import sys
import tomllib
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import shared_constants


class SharedConstantsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.product_version = tomllib.loads((cls.repo_root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
        cls.test_root = cls.repo_root / '.tmp-test' / 'shared-constants'

    def _workspace(self, name: str) -> Path:
        workspace = self.test_root / name
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def test_product_version_is_loaded_from_pyproject(self) -> None:
        self.assertEqual(shared_constants.get_product_version(), self.product_version)

    def test_source_revision_falls_back_to_git_head(self) -> None:
        revision = shared_constants.get_source_revision()
        self.assertRegex(revision, r'^[0-9a-f]{40}$')

    def test_build_timestamp_normalizes_utc_env_override(self) -> None:
        timestamp = shared_constants.get_build_timestamp(
            env={shared_constants.BUILD_TIMESTAMP_ENV_VAR: '2026-03-23T08:15:30+00:00'}
        )
        self.assertEqual(timestamp, '2026-03-23T08:15:30Z')

    def test_build_timestamp_rejects_non_utc_values(self) -> None:
        with self.assertRaisesRegex(RuntimeError, 'UTC timezone'):
            shared_constants.get_build_timestamp(
                env={shared_constants.BUILD_TIMESTAMP_ENV_VAR: '2026-03-23T08:15:30+08:00'},
                require=True,
            )

    def test_product_provenance_prefers_env_source_revision_override(self) -> None:
        provenance = shared_constants.get_product_provenance(
            env={shared_constants.SOURCE_REVISION_ENV_VAR: 'a' * 40}
        )
        self.assertEqual(provenance['product_name'], 'Libro.AgentWCAG')
        self.assertEqual(provenance['product_version'], self.product_version)
        self.assertEqual(provenance['source_revision'], 'a' * 40)
        self.assertEqual(
            provenance['source_revision_source'],
            shared_constants.SOURCE_REVISION_ENV_VAR,
        )

    def test_product_version_falls_back_to_package_json_when_pyproject_is_missing(self) -> None:
        repo_root = self._workspace('package-json-version-fallback')
        (repo_root / 'package.json').write_text(
            json.dumps({'version': '9.9.9'}, ensure_ascii=False),
            encoding='utf-8',
        )
        self.assertEqual(shared_constants.get_product_version(repo_root), '9.9.9')

    def test_product_provenance_falls_back_to_packaged_metadata_without_git_checkout(self) -> None:
        repo_root = self._workspace('packaged-provenance-fallback')
        (repo_root / 'package.json').write_text(
            json.dumps({'version': '8.8.8'}, ensure_ascii=False),
            encoding='utf-8',
        )
        (repo_root / shared_constants.PACKAGE_PROVENANCE_FILE).write_text(
            json.dumps(
                {
                    'product_name': 'Libro.AgentWCAG',
                    'product_version': '8.8.8',
                    'source_revision': 'b' * 40,
                    'build_timestamp': '2026-03-23T08:15:30Z',
                },
                ensure_ascii=False,
            ),
            encoding='utf-8',
        )

        provenance = shared_constants.get_product_provenance(repo_root)
        self.assertEqual(provenance['product_version'], '8.8.8')
        self.assertEqual(provenance['version_source'], 'package.json')
        self.assertEqual(provenance['source_revision'], 'b' * 40)
        self.assertEqual(provenance['source_revision_source'], shared_constants.PACKAGE_PROVENANCE_FILE)
        self.assertEqual(provenance['build_timestamp'], '2026-03-23T08:15:30Z')
        self.assertEqual(provenance['build_timestamp_source'], shared_constants.PACKAGE_PROVENANCE_FILE)


if __name__ == '__main__':
    unittest.main()
