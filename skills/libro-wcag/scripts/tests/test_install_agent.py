#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path


class InstallAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.test_workspace_root = cls.repo_root / '.tmp-test' / 'install-agent'
        cls.product_version = tomllib.loads((cls.repo_root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']

    def _workspace(self, name: str) -> Path:
        workspace = self.test_workspace_root / name
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def test_installer_creates_manifest_for_claude(self) -> None:
        destination = self._workspace('claude-install') / 'claude-skill'
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'claude',
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
        self.assertEqual(manifest['agent'], 'claude')
        self.assertEqual(manifest['product_name'], 'Libro.AgentWCAG')
        self.assertEqual(manifest['product_version'], self.product_version)
        self.assertRegex(manifest['source_revision'], r'^[0-9a-f]{40}$')
        self.assertEqual(manifest['adapter_prompt'], 'adapters/claude/prompt-template.md')
        self.assertIn('doctor-agent.py', manifest['doctor_command'])
        self.assertEqual(manifest['manifest_integrity']['algorithm'], 'sha256')
        self.assertIn('adapter_prompt', manifest['manifest_integrity']['entrypoint_hashes'])
        self.assertEqual(manifest['provenance']['version_source'], 'pyproject.toml')

    def test_installer_can_install_all_agents(self) -> None:
        workspace = self._workspace('install-all')
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'all',
                '--dest',
                str(workspace),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        for agent in ('codex', 'claude', 'gemini', 'copilot'):
            self.assertTrue((workspace / agent / 'libro-wcag' / 'install-manifest.json').exists())

    def test_installer_requires_force_to_replace(self) -> None:
        destination = self._workspace('force-required') / 'codex-skill'
        destination.mkdir(parents=True)
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
        self.assertNotEqual(completed.returncode, 0)

    def test_doctor_reports_valid_installation(self) -> None:
        destination = self._workspace('doctor-valid') / 'gemini-skill'
        install = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'gemini',
                '--dest',
                str(destination),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
        doctor = subprocess.run(
            [
                sys.executable,
                'scripts/doctor-agent.py',
                '--agent',
                'gemini',
                '--dest',
                str(destination),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
        payload = json.loads(doctor.stdout)
        self.assertTrue(payload['ok'])
        self.assertTrue(payload['manifest_provenance']['verified'])
        self.assertEqual(payload['expected_product']['product_version'], self.product_version)
        self.assertEqual(payload['installed_product']['product_version'], self.product_version)
        self.assertTrue(payload['version_consistency']['verified'])
        self.assertTrue(payload['version_consistency']['matches']['product_version'])
        self.assertTrue(payload['version_consistency']['matches']['source_revision'])

    def test_installer_can_install_gemini_workspace_skill_layout(self) -> None:
        workspace_root = self._workspace('gemini-workspace-root')
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'gemini',
                '--workspace-root',
                str(workspace_root),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        destination = workspace_root / '.gemini' / 'skills' / 'libro-wcag'
        self.assertTrue((destination / 'SKILL.md').exists())
        manifest = json.loads((destination / 'install-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['agent'], 'gemini')

    def test_installer_rejects_dest_with_workspace_root(self) -> None:
        workspace_root = self._workspace('workspace-root-conflict')
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'gemini',
                '--workspace-root',
                str(workspace_root),
                '--dest',
                str(workspace_root / 'custom'),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('--dest and --workspace-root cannot be used together', completed.stderr + completed.stdout)

    def test_installer_can_emit_workspace_mcp_config(self) -> None:
        workspace_root = self._workspace('emit-gemini-mcp')
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'gemini',
                '--workspace-root',
                str(workspace_root),
                '--emit-mcp-config',
                'gemini',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        settings_path = workspace_root / '.gemini' / 'settings.json'
        payload = json.loads(settings_path.read_text(encoding='utf-8'))
        self.assertIn('mcpServers', payload)
        self.assertIn('libro-wcag', payload['mcpServers'])
        self.assertIn('mcp-server/server.py', payload['mcpServers']['libro-wcag']['args'][0])

    def test_installer_materializes_codex_workspace_extras_from_templates(self) -> None:
        workspace_root = self._workspace('codex-workspace-root')
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'codex',
                '--workspace-root',
                str(workspace_root),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue((workspace_root / '.codex' / 'skills' / 'libro-wcag' / 'SKILL.md').exists())
        self.assertTrue((workspace_root / '.codex' / 'environments' / 'environment.toml').exists())

    def test_installer_uses_templates_even_when_source_checkout_has_no_root_workspace_assets(self) -> None:
        self.assertFalse((self.repo_root / '.claude' / 'skills' / 'libro-wcag' / 'SKILL.md').exists())
        destination = self._workspace('template-backed-claude-install') / 'claude-skill'
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'claude',
                '--dest',
                str(destination),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        content = (destination / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('Claude-specific note', content)

    def test_emit_mcp_config_requires_workspace_root(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'claude',
                '--emit-mcp-config',
                'claude',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('--emit-mcp-config requires --workspace-root', completed.stderr + completed.stdout)

    def test_doctor_fails_when_manifest_provenance_is_missing(self) -> None:
        destination = self._workspace('doctor-missing-provenance') / 'codex-skill'
        install = subprocess.run(
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
        self.assertEqual(install.returncode, 0, install.stdout + install.stderr)

        manifest_path = destination / 'install-manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest.pop('source_revision')
        manifest.pop('provenance')
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

        doctor = subprocess.run(
            [
                sys.executable,
                'scripts/doctor-agent.py',
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
        self.assertEqual(doctor.returncode, 1, doctor.stdout + doctor.stderr)
        payload = json.loads(doctor.stdout)
        self.assertFalse(payload['ok'])
        self.assertIn('source_revision', payload['manifest_provenance']['missing_manifest_fields'])
        self.assertIn('provenance', payload['manifest_provenance']['missing_manifest_fields'])
        self.assertFalse(payload['version_consistency']['verified'])

    def test_uninstall_removes_destination(self) -> None:
        destination = self._workspace('uninstall') / 'codex-skill'
        install = subprocess.run(
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
        self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
        uninstall = subprocess.run(
            [
                sys.executable,
                'scripts/uninstall-agent.py',
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
        self.assertEqual(uninstall.returncode, 0, uninstall.stdout + uninstall.stderr)
        self.assertFalse(destination.exists())

    def test_cross_agent_custom_dest_reinstall_and_uninstall_matrix(self) -> None:
        agents = ('codex', 'claude', 'gemini', 'copilot')
        workspace = self._workspace('cross-agent-matrix')
        for agent in agents:
            with self.subTest(agent=agent):
                destination = workspace / 'matrix-layout' / agent / 'bundle' / 'libro-wcag'

                initial = subprocess.run(
                    [
                        sys.executable,
                        'scripts/install-agent.py',
                        '--agent',
                        agent,
                        '--dest',
                        str(destination),
                    ],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)

                manifest_before = json.loads((destination / 'install-manifest.json').read_text(encoding='utf-8'))
                hash_before = manifest_before['manifest_integrity']['entrypoint_hashes']['adapter_prompt']

                doctor_ok = subprocess.run(
                    [
                        sys.executable,
                        'scripts/doctor-agent.py',
                        '--agent',
                        agent,
                        '--dest',
                        str(destination),
                        '--verify-manifest-integrity',
                    ],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(doctor_ok.returncode, 0, doctor_ok.stdout + doctor_ok.stderr)
                doctor_payload = json.loads(doctor_ok.stdout)
                self.assertTrue(doctor_payload['manifest_integrity']['verified'])
                self.assertTrue(doctor_payload['manifest_provenance']['verified'])

                reinstall = subprocess.run(
                    [
                        sys.executable,
                        'scripts/install-agent.py',
                        '--agent',
                        agent,
                        '--dest',
                        str(destination),
                        '--force',
                    ],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(reinstall.returncode, 0, reinstall.stdout + reinstall.stderr)
                manifest_after = json.loads((destination / 'install-manifest.json').read_text(encoding='utf-8'))
                hash_after = manifest_after['manifest_integrity']['entrypoint_hashes']['adapter_prompt']
                self.assertEqual(hash_before, hash_after)

                uninstall = subprocess.run(
                    [
                        sys.executable,
                        'scripts/uninstall-agent.py',
                        '--agent',
                        agent,
                        '--dest',
                        str(destination),
                    ],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(uninstall.returncode, 0, uninstall.stdout + uninstall.stderr)
                self.assertFalse(destination.exists())

    def test_installer_works_from_packaged_npm_layout_without_git_or_pyproject(self) -> None:
        workspace = self._workspace('npm-packaged-install')
        package_root = workspace / 'node_modules' / 'librowcag-cli'
        package_root.mkdir(parents=True, exist_ok=True)

        files_to_copy = [
            'package.json',
            'scripts/install-agent.py',
            'skills/libro-wcag/SKILL.md',
            'skills/libro-wcag/scripts/shared_constants.py',
        ]
        directories_to_copy = [
            'skills/libro-wcag/adapters',
            'packaging/templates/workspace',
        ]
        for relative in files_to_copy:
            source = self.repo_root / relative
            destination = package_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        for relative in directories_to_copy:
            shutil.copytree(self.repo_root / relative, package_root / relative)

        (package_root / 'package-provenance.json').write_text(
            json.dumps(
                {
                    'product_name': 'Libro.AgentWCAG',
                    'product_version': self.product_version,
                    'source_revision': 'c' * 40,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding='utf-8',
        )

        destination = workspace / 'claude-skill'
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/install-agent.py',
                '--agent',
                'claude',
                '--dest',
                str(destination),
            ],
            cwd=package_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        manifest = json.loads((destination / 'install-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['product_version'], self.product_version)
        self.assertEqual(manifest['source_revision'], 'c' * 40)
        self.assertEqual(manifest['provenance']['version_source'], 'package.json')
        self.assertEqual(manifest['provenance']['source_revision_source'], 'package-provenance.json')


if __name__ == '__main__':
    unittest.main()
