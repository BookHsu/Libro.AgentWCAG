#!/usr/bin/env python3

from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import yaml


class RepoScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]

    def _decode_json_stream(self, payload: str) -> list[dict[str, object]]:
        decoder = json.JSONDecoder()
        index = 0
        items: list[dict[str, object]] = []
        while index < len(payload):
            while index < len(payload) and payload[index].isspace():
                index += 1
            if index >= len(payload):
                break
            item, index = decoder.raw_decode(payload, index)
            items.append(item)
        return items

    def _archive_fixture(self, workspace: Path) -> Path:
        archive_path = workspace / 'repo.zip'
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in self.repo_root.rglob('*'):
                if not path.is_file():
                    continue
                if '.git' in path.parts or '.tmp-test' in path.parts or '__pycache__' in path.parts:
                    continue
                relative = path.relative_to(self.repo_root)
                archive.write(path, Path('Libro.AgentWCAG-master') / relative)
        return archive_path

    def _git_head_revision(self) -> str:
        completed = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return completed.stdout.strip()

    def test_validate_skill_cli_accepts_skill_directory(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/validate_skill.py',
                'skills/libro-wcag',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn('Skill is valid!', completed.stdout)

    def test_validate_skill_cli_validates_policy_bundles_when_flag_enabled(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/validate_skill.py',
                'skills/libro-wcag',
                '--validate-policy-bundles',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn('Skill is valid!', completed.stdout)
        self.assertIn('Policy bundles are valid!', completed.stdout)

    def test_validate_skill_cli_rejects_missing_directory(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                'scripts/validate_skill.py',
                'skills/missing-skill',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('Missing SKILL.md', completed.stderr + completed.stdout)

    def test_validate_skill_cli_rejects_missing_adapter_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / 'skills' / 'libro-wcag'
            shutil.copytree(self.repo_root / 'skills' / 'libro-wcag', skill_dir)
            (skill_dir / 'adapters' / 'copilot' / 'usage-example.md').unlink()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(self.repo_root / 'scripts' / 'validate_skill.py'),
                    str(skill_dir),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn('missing required adapter files', completed.stderr + completed.stdout)
            self.assertIn('usage-example.md', completed.stderr + completed.stdout)

    def test_validate_skill_cli_rejects_missing_scripts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / 'skills' / 'libro-wcag'
            shutil.copytree(self.repo_root / 'skills' / 'libro-wcag', skill_dir)
            shutil.rmtree(skill_dir / 'scripts')
            completed = subprocess.run(
                [
                    sys.executable,
                    str(self.repo_root / 'scripts' / 'validate_skill.py'),
                    str(skill_dir),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn('Missing scripts directory', completed.stderr + completed.stdout)

    def test_validate_skill_cli_rejects_missing_required_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / 'skills' / 'libro-wcag'
            shutil.copytree(self.repo_root / 'skills' / 'libro-wcag', skill_dir)
            skill_md = skill_dir / 'SKILL.md'
            payload = skill_md.read_text(encoding='utf-8')
            frontmatter = yaml.safe_load(payload.split('---\n', 2)[1])
            frontmatter.pop('description', None)
            body = payload.split('---\n', 2)[2]
            skill_md.write_text(
                '---\n' + yaml.safe_dump(frontmatter, sort_keys=False) + '---\n' + body,
                encoding='utf-8',
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(self.repo_root / 'scripts' / 'validate_skill.py'),
                    str(skill_dir),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn('frontmatter missing required keys', completed.stderr + completed.stdout)
            self.assertIn('description', completed.stderr + completed.stdout)

    def test_apply_release_version_script_targets_repo_version_files(self) -> None:
        script = (self.repo_root / 'scripts' / 'apply-release-version.py').read_text(encoding='utf-8')
        self.assertIn('pyproject.toml', script)
        self.assertIn('package.json', script)
        self.assertIn('.claude-plugin', script)
        self.assertIn('marketplace.json', script)
        self.assertIn('Semantic version', script)

    def test_doctor_all_reports_each_supported_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'all',
                    '--dest',
                    tmp,
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
                    'all',
                    '--dest',
                    tmp,
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            payloads = self._decode_json_stream(doctor.stdout)
            self.assertEqual([item['agent'] for item in payloads], ['codex', 'claude', 'gemini', 'copilot'])
            self.assertTrue(all(item['ok'] for item in payloads))

    def test_doctor_all_with_manifest_integrity_mode_reports_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'all',
                    '--dest',
                    tmp,
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
                    'all',
                    '--dest',
                    tmp,
                    '--verify-manifest-integrity',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            payloads = self._decode_json_stream(doctor.stdout)
            self.assertTrue(all(item['manifest_integrity']['verified'] for item in payloads))

    def test_doctor_check_scanners_reports_toolchain_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, 'codex-skill')
            install = subprocess.run(
                [sys.executable, 'scripts/install-agent.py', '--agent', 'codex', '--dest', dest],
                cwd=self.repo_root, capture_output=True, text=True, check=False,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            doctor = subprocess.run(
                [sys.executable, 'scripts/doctor-agent.py', '--agent', 'codex', '--dest', dest, '--check-scanners'],
                cwd=self.repo_root, capture_output=True, text=True, check=False,
            )
            payload = json.loads(doctor.stdout)
            self.assertIn('scanner_toolchain', payload)
            self.assertIn('ok', payload['scanner_toolchain'])
            self.assertIn('tools', payload['scanner_toolchain'])
            for tool_name in ('npx', '@axe-core/cli', 'lighthouse'):
                self.assertIn(tool_name, payload['scanner_toolchain']['tools'])
                self.assertIn('status', payload['scanner_toolchain']['tools'][tool_name])

    def test_libro_audit_preflight_only_returns_json(self) -> None:
        result = subprocess.run(
            [sys.executable, 'scripts/libro.py', 'audit', '--preflight-only'],
            cwd=self.repo_root, capture_output=True, text=True, check=False,
        )
        payload = json.loads(result.stdout)
        self.assertIn('ok', payload)
        self.assertIn('checks', payload)

    def test_force_reinstall_replaces_existing_installation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'codex-skill'
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
            extra_file = destination / 'local.txt'
            extra_file.write_text('stale', encoding='utf-8')
            reinstall = subprocess.run(
                [
                    sys.executable,
                    'scripts/install-agent.py',
                    '--agent',
                    'codex',
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
            self.assertFalse(extra_file.exists())
            self.assertTrue((destination / 'install-manifest.json').exists())

    def test_realistic_validation_smoke_script_exists_and_references_mock_flow(self) -> None:
        script = (self.repo_root / 'scripts' / 'run-realistic-validation-smoke.py').read_text(encoding='utf-8')
        self.assertIn('run_accessibility_audit.py', script)
        self.assertIn('--mock-axe-json', script)
        self.assertIn('--mock-lighthouse-json', script)
        self.assertIn('wcag-fixes.sample.diff', script)

    def _load_realistic_validation_smoke_module(self):
        module_path = self.repo_root / 'scripts' / 'run-realistic-validation-smoke.py'
        spec = importlib.util.spec_from_file_location('run_realistic_validation_smoke', module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _load_uninstall_agent_module(self):
        module_path = self.repo_root / 'scripts' / 'uninstall-agent.py'
        spec = importlib.util.spec_from_file_location('uninstall_agent', module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_realistic_validation_smoke_helper_reports_malformed_json(self) -> None:
        smoke = self._load_realistic_validation_smoke_module()
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / 'wcag-report.json'
            report_path.write_text('{"summary": }', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, r'Audit report is not valid JSON: .*wcag-report\.json'):
                smoke._load_json_artifact(report_path, 'Audit report')

    def test_realistic_validation_smoke_main_reports_missing_report_file(self) -> None:
        smoke = self._load_realistic_validation_smoke_module()
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            artifact_dir = temp_root / 'artifacts'
            output_dir = temp_root / 'audit-output'
            output_dir.mkdir(parents=True, exist_ok=True)

            def fake_run(command: list[str], cwd: Path) -> tuple[int, str]:
                return 0, ''

            original_argv = sys.argv
            sys.argv = [
                'run-realistic-validation-smoke.py',
                '--sample',
                str(self.repo_root / 'skills' / 'libro-wcag' / 'scripts' / 'tests' / 'fixtures' / 'missing-alt.html'),
                '--axe-mock',
                str(self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'scanner-fixtures' / 'axe.mock.json'),
                '--lighthouse-mock',
                str(self.repo_root / 'docs' / 'testing' / 'realistic-sample' / 'scanner-fixtures' / 'lighthouse.mock.json'),
                '--artifact-dir',
                str(artifact_dir),
            ]
            try:
                smoke.REPO_ROOT = temp_root
                smoke.DEFAULT_SAMPLE = Path(sys.argv[2])
                smoke.DEFAULT_AXE_MOCK = Path(sys.argv[4])
                smoke.DEFAULT_LIGHTHOUSE_MOCK = Path(sys.argv[6])
                smoke.DEFAULT_ARTIFACT_DIR = artifact_dir
                smoke._run = fake_run
                with self.assertRaisesRegex(FileNotFoundError, r'Audit report is missing: .*wcag-report\.json'):
                    smoke.main()
            finally:
                sys.argv = original_argv

    def test_uninstall_agent_reports_friendly_error_for_non_directory_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'installed-skill.txt'
            destination.write_text('not a directory', encoding='utf-8')
            completed = subprocess.run(
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
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn('Failed to remove installation at', completed.stderr)
            self.assertIn(str(destination), completed.stderr)

    def test_uninstall_agent_wraps_permission_errors(self) -> None:
        uninstall_agent = self._load_uninstall_agent_module()
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'codex-skill'
            destination.mkdir()
            with mock.patch.object(
                uninstall_agent.shutil,
                'rmtree',
                side_effect=PermissionError('Access is denied'),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    r'Failed to remove installation at .*permission denied',
                ):
                    uninstall_agent.uninstall(destination)
    def test_install_agent_ps1_wrapper_invokes_python_installer(self) -> None:
        wrapper = (self.repo_root / 'scripts' / 'install-agent.ps1').read_text(encoding='utf-8')
        self.assertIn('install-agent.py', wrapper)
        self.assertIn("[ValidateSet('codex','claude','gemini','copilot','all')]", wrapper)
        self.assertIn('python $script @arguments', wrapper)

    def test_install_agent_sh_wrapper_invokes_python_installer(self) -> None:
        wrapper = (self.repo_root / 'scripts' / 'install-agent.sh').read_text(encoding='utf-8')
        self.assertIn('install-agent.py', wrapper)
        self.assertIn('codex|claude|gemini|copilot|all', wrapper)
        self.assertIn('python "$SCRIPT_DIR/install-agent.py" --agent "$AGENT" "$@"', wrapper)

    def test_libro_ps1_wrapper_invokes_unified_cli(self) -> None:
        wrapper = (self.repo_root / 'scripts' / 'libro.ps1').read_text(encoding='utf-8')
        self.assertIn("[ValidateSet('install','doctor','remove','audit')]", wrapper)
        self.assertIn("Join-Path $PSScriptRoot 'libro.py'", wrapper)
        self.assertIn('python $script @arguments', wrapper)

    def test_libro_sh_wrapper_invokes_unified_cli(self) -> None:
        wrapper = (self.repo_root / 'scripts' / 'libro.sh').read_text(encoding='utf-8')
        self.assertIn('<install|doctor|remove|audit>', wrapper)
        self.assertIn('python "$SCRIPT_DIR/libro.py" "$COMMAND" "$@"', wrapper)

    def test_npm_cli_wrapper_invokes_bundled_python_entrypoint(self) -> None:
        wrapper = (self.repo_root / 'bin' / 'libro.js').read_text(encoding='utf-8')
        self.assertIn('scripts", "libro.py"', wrapper)
        self.assertIn('python3', wrapper)
        self.assertIn('command: "py"', wrapper)
        self.assertIn('args: ["-3"]', wrapper)
        self.assertIn('process.argv.slice(2)', wrapper)

    def test_npm_cli_wrapper_can_run_help(self) -> None:
        completed = subprocess.run(
            [
                'node',
                'bin/libro.js',
                '--help',
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn('Unified CLI for installing and validating Libro.AgentWCAG', completed.stdout)

    def test_libro_cli_wraps_install_doctor_and_remove(self) -> None:
        cli = (self.repo_root / 'scripts' / 'libro.py').read_text(encoding='utf-8')
        self.assertIn('subparsers.add_parser("install"', cli)
        self.assertIn('subparsers.add_parser("doctor"', cli)
        self.assertIn('subparsers.add_parser("remove"', cli)
        self.assertIn('install-agent.py', cli)
        self.assertIn('doctor-agent.py', cli)
        self.assertIn('uninstall-agent.py', cli)
        self.assertIn('workspace_root', cli)

    def test_libro_cli_can_install_doctor_and_remove_workspace_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            install = subprocess.run(
                [
                    sys.executable,
                    'scripts/libro.py',
                    'install',
                    'claude',
                    '--workspace-root',
                    str(workspace),
                    '--force',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            skill_root = workspace / '.claude' / 'skills' / 'libro-wcag'
            self.assertTrue((skill_root / 'install-manifest.json').exists())

            doctor = subprocess.run(
                [
                    sys.executable,
                    'scripts/libro.py',
                    'doctor',
                    'claude',
                    '--workspace-root',
                    str(workspace),
                    '--verify-manifest-integrity',
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            self.assertIn('"ok": true', doctor.stdout.lower())

            remove = subprocess.run(
                [
                    sys.executable,
                    'scripts/libro.py',
                    'remove',
                    'claude',
                    '--workspace-root',
                    str(workspace),
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(remove.returncode, 0, remove.stdout + remove.stderr)
            self.assertFalse(skill_root.exists())

    def test_bootstrap_ps1_downloads_repo_archive_and_runs_install_and_doctor(self) -> None:
        wrapper = (self.repo_root / 'scripts' / 'bootstrap.ps1').read_text(encoding='utf-8')
        self.assertIn("BookHsu/Libro.AgentWCAG", wrapper)
        self.assertIn("archive/$Ref.zip", wrapper)
        self.assertIn('Resolve-SourceRevision', wrapper)
        self.assertIn('LIBRO_AGENTWCAG_SOURCE_REVISION', wrapper)
        self.assertIn('install-agent.py', wrapper)
        self.assertIn('doctor-agent.py', wrapper)
        self.assertIn('Read-Host', wrapper)
        self.assertIn("python 3.12+ is required", wrapper)
        self.assertIn('doctor verification passed', wrapper)

    def test_bootstrap_sh_downloads_repo_archive_and_runs_install_and_doctor(self) -> None:
        wrapper = (self.repo_root / 'scripts' / 'bootstrap.sh').read_text(encoding='utf-8')
        self.assertIn('BookHsu/Libro.AgentWCAG', wrapper)
        self.assertIn('archive/{ref}.zip', wrapper)
        self.assertIn('--archive-path', wrapper)
        self.assertIn('LIBRO_AGENTWCAG_SOURCE_REVISION', wrapper)
        self.assertIn('install-agent.py', wrapper)
        self.assertIn('doctor-agent.py', wrapper)
        self.assertIn('required=True', wrapper)
        self.assertIn('python 3.12+ is required', wrapper)
        self.assertIn('doctor verification passed', wrapper)

    @unittest.skipUnless(shutil.which('sh'), 'POSIX shell is unavailable')
    def test_bootstrap_sh_can_install_from_local_archive_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            archive_path = self._archive_fixture(workspace)
            destination = workspace / 'claude-skill'
            env = os.environ.copy()
            env['LIBRO_AGENTWCAG_SOURCE_REVISION'] = self._git_head_revision()
            completed = subprocess.run(
                [
                    'sh',
                    'scripts/bootstrap.sh',
                    '--agent',
                    'claude',
                    '--archive-path',
                    str(archive_path),
                    '--dest',
                    str(destination),
                    '--force',
                ],
                cwd=self.repo_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue((destination / 'install-manifest.json').exists())

    def test_bootstrap_ps1_can_install_from_local_archive_override(self) -> None:
        pwsh = shutil.which('pwsh') or shutil.which('powershell')
        self.assertIsNotNone(pwsh)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            archive_path = self._archive_fixture(workspace)
            destination = workspace / 'copilot-skill'
            env = os.environ.copy()
            env['LIBRO_AGENTWCAG_SOURCE_REVISION'] = self._git_head_revision()
            completed = subprocess.run(
                [
                    str(pwsh),
                    '-File',
                    'scripts/bootstrap.ps1',
                    '-Agent',
                    'copilot',
                    '-ArchivePath',
                    str(archive_path),
                    '-Dest',
                    str(destination),
                    '-Force',
                ],
                cwd=self.repo_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue((destination / 'install-manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
