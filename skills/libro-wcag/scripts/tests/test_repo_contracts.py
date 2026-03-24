#!/usr/bin/env python3

from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

import yaml


class RepoContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.skill_root = cls.repo_root / 'skills' / 'libro-wcag'

    def _read(self, path: Path) -> str:
        return path.read_text(encoding='utf-8')

    def test_readme_covers_installation_validation_and_testing_plan(self) -> None:
        content = self._read(self.repo_root / 'README.md')
        self.assertIn('install-agent.py --agent codex', content)
        self.assertIn('doctor-agent.py --agent codex', content)
        self.assertIn('uninstall-agent.py --agent codex', content)
        self.assertIn('TESTING-PLAN.md', content)
        self.assertIn('$libro-wcag', content)
        self.assertIn('scripts/bootstrap.sh', content)
        self.assertIn('scripts/bootstrap.ps1', content)
        self.assertIn('/plugin install libro-wcag@libro-wcag-marketplace', content)
        self.assertIn('--workspace-root', content)

    def test_testing_plan_tracks_matrix_mapping_and_gaps(self) -> None:
        content = self._read(self.repo_root / 'TESTING-PLAN.md')
        for heading in ['## Test Matrix', '## Repo Mapping', '## Already Implemented', '## Still Worth Adding']:
            self.assertIn(heading, content)
        self.assertIn('Automation Target', content)
        self.assertIn('Coverage Mode', content)
        self.assertIn('Scripted Manual', content)
        self.assertIn('Automated', content)

    def test_agent_installation_expansion_todo_tracks_workspace_plugin_and_mcp_paths(self) -> None:
        content = self._read(self.repo_root / 'docs' / 'automations' / 'agent-installation-expansion-todo.md')
        self.assertIn('.gemini/skills/libro-wcag/SKILL.md', content)
        self.assertIn('.claude-plugin/plugin.json', content)
        self.assertIn('.claude-plugin/marketplace.json', content)
        self.assertIn('mcp-server/server.py', content)
        self.assertIn('.github/workflows/install-skill.yml', content)
        self.assertIn('vscode-extension/package.json', content)

    def test_gemini_workspace_skill_exists_and_tracks_core_contract(self) -> None:
        core_skill = self._read(self.skill_root / 'SKILL.md')
        workspace_skill = self._read(self.repo_root / '.gemini' / 'skills' / 'libro-wcag' / 'SKILL.md')
        self.assertIn('name: libro-wcag', workspace_skill)
        self.assertIn('Gemini-specific note', workspace_skill)
        self.assertIn('execution_mode', workspace_skill)
        self.assertIn('safe first-pass remediations', workspace_skill)
        self.assertIn('Use `adapters/gemini/prompt-template.md`', workspace_skill)
        self.assertIn('JSON top-level keys', workspace_skill)
        self.assertIn('JSON top-level keys', core_skill)

    def test_reusable_install_workflow_exists_and_calls_installer_and_doctor(self) -> None:
        content = self._read(self.repo_root / '.github' / 'workflows' / 'install-skill.yml')
        self.assertIn('workflow_call', content)
        self.assertIn('actions/checkout@v4', content)
        self.assertIn('actions/setup-python@v5', content)
        self.assertIn('python scripts/install-agent.py', content)
        self.assertIn('python scripts/doctor-agent.py', content)
        self.assertIn('--verify-manifest-integrity', content)

    def test_mcp_server_scaffold_exists_with_stdio_transport_and_wrapped_tools(self) -> None:
        server = self._read(self.repo_root / 'mcp-server' / 'server.py')
        requirements = self._read(self.repo_root / 'mcp-server' / 'requirements.txt')
        audit_tool = self._read(self.repo_root / 'mcp-server' / 'tools' / 'audit_page.py')
        suggest_tool = self._read(self.repo_root / 'mcp-server' / 'tools' / 'suggest_fixes.py')
        normalize_tool = self._read(self.repo_root / 'mcp-server' / 'tools' / 'normalize_report.py')
        self.assertIn('FastMCP("libro-wcag")', server)
        self.assertIn('@mcp.tool()', server)
        self.assertIn('libro_wcag_audit', server)
        self.assertIn('libro_wcag_suggest', server)
        self.assertIn('libro_wcag_normalize', server)
        self.assertIn('mcp>=', requirements)
        self.assertIn('run_accessibility_audit.py', audit_tool)
        self.assertIn('get_strategy', suggest_tool)
        self.assertIn('normalize_report', normalize_tool)

    def test_examples_cover_add_dir_reusable_workflow_and_gh_release_download(self) -> None:
        add_dir = self._read(self.repo_root / 'docs' / 'examples' / 'claude' / 'settings.add-dir.sample.json')
        reusable = self._read(self.repo_root / 'docs' / 'examples' / 'ci' / 'install-skill-consumer-sample.yml')
        gh_release = self._read(self.repo_root / 'docs' / 'examples' / 'ci' / 'gh-release-download-sample.md')
        self.assertIn('.vendor/libro-wcag', add_dir)
        self.assertIn('uses: BookHsu/Libro.AgentWCAG.clean/.github/workflows/install-skill.yml@v1', reusable)
        self.assertIn('gh release download', gh_release)
        self.assertIn('install-agent.py --agent claude', gh_release)

    def test_mcp_samples_exist_for_claude_copilot_and_gemini(self) -> None:
        claude = self._read(self.repo_root / 'docs' / 'examples' / 'claude' / 'mcp.sample.json')
        copilot = self._read(self.repo_root / 'docs' / 'examples' / 'copilot' / 'mcp.sample.json')
        gemini = self._read(self.repo_root / 'docs' / 'examples' / 'gemini' / 'settings.mcp.sample.json')
        self.assertIn('mcp-server/server.py', claude)
        self.assertIn('"servers"', copilot)
        self.assertIn('"mcpServers"', gemini)

    def test_claude_plugin_json_exists_and_has_required_fields(self) -> None:
        payload = json.loads((self.repo_root / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['name'], 'libro-wcag')
        self.assertEqual(payload['license'], 'MIT')
        self.assertIn('version', payload)
        self.assertIn('description', payload)
        self.assertEqual(payload['repository'], 'https://github.com/BookHsu/Libro.AgentWCAG.clean')
        self.assertIn('mcpServers', payload)
        self.assertIn('libro-wcag', payload['mcpServers'])

    def test_claude_marketplace_json_exists_and_references_plugin(self) -> None:
        payload = json.loads((self.repo_root / '.claude-plugin' / 'marketplace.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['name'], 'libro-wcag-marketplace')
        self.assertEqual(len(payload['plugins']), 1)
        self.assertEqual(payload['plugins'][0]['name'], 'libro-wcag')
        self.assertEqual(payload['plugins'][0]['source'], './')

    def test_claude_plugin_version_matches_pyproject(self) -> None:
        plugin = json.loads((self.repo_root / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))
        pyproject = tomllib.loads((self.repo_root / 'pyproject.toml').read_text(encoding='utf-8'))
        self.assertEqual(plugin['version'], pyproject['project']['version'])

    def test_claude_marketplace_version_matches_plugin(self) -> None:
        plugin = json.loads((self.repo_root / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))
        marketplace = json.loads((self.repo_root / '.claude-plugin' / 'marketplace.json').read_text(encoding='utf-8'))
        self.assertEqual(marketplace['plugins'][0]['version'], plugin['version'])

    def test_manual_testing_assets_exist_for_non_automated_matrix_types(self) -> None:
        playbook = self._read(self.repo_root / 'docs' / 'testing' / 'testing-playbook.md')
        self.assertIn('Acceptance Test / UAT', playbook)
        self.assertIn('Beta Test', playbook)
        self.assertIn('Decision Table', playbook)
        self.assertIn('End-to-End Test', playbook)
        self.assertIn('Performance Test', playbook)
        self.assertIn('Concurrency Test', playbook)

    def test_pyproject_declares_repo_metadata_and_test_path(self) -> None:
        content = self._read(self.repo_root / 'pyproject.toml')
        self.assertIn('name = "Libro.AgentWCAG"', content)
        self.assertIn('requires-python = ">=3.12"', content)
        self.assertIn('skills/libro-wcag/scripts/tests', content)

    def test_license_is_mit_and_credits_book_hsu(self) -> None:
        content = self._read(self.repo_root / 'LICENSE')
        self.assertIn('MIT License', content)
        self.assertIn('Book Hsu', content)

    def test_repository_support_files_define_line_endings_ignores_and_ci_paths(self) -> None:
        gitattributes = self._read(self.repo_root / '.gitattributes')
        gitignore = self._read(self.repo_root / '.gitignore')
        workflow = self._read(self.repo_root / '.github' / 'workflows' / 'test.yml')
        self.assertIn('* text=auto eol=lf', gitattributes)
        self.assertIn('*.ps1 text eol=crlf', gitattributes)
        self.assertIn('__pycache__/', gitignore)
        self.assertIn('node_modules/', gitignore)
        self.assertIn('skills/libro-wcag/scripts/tests', workflow)
        self.assertIn('skills/libro-wcag', workflow)

    def test_skill_frontmatter_and_usage_contract_exist(self) -> None:
        content = self._read(self.skill_root / 'SKILL.md')
        self.assertIn('name: libro-wcag', content)
        self.assertIn('execution_mode', content)
        self.assertIn('task_mode', content)
        self.assertIn('local file path or URL', content)
        self.assertIn('safe first-pass remediations', content)
        self.assertIn('usage-example.md', content)
        self.assertIn('failure-guide.md', content)
        self.assertIn('e2e-example.md', content)

    def test_openai_agent_yaml_points_to_libro_agentwcag_prompt(self) -> None:
        payload = yaml.safe_load((self.skill_root / 'agents' / 'openai.yaml').read_text(encoding='utf-8'))
        self.assertEqual(payload['interface']['display_name'], 'Libro.AgentWCAG')
        self.assertIn('$libro-wcag', payload['interface']['default_prompt'])

    def test_core_spec_and_adapter_mapping_define_contract_boundaries(self) -> None:
        core_spec = self._read(self.skill_root / 'references' / 'core-spec.md')
        adapter_mapping = self._read(self.skill_root / 'references' / 'adapter-mapping.md')
        self.assertIn('audit-only | suggest-only | apply-fixes', core_spec)
        self.assertIn('core-workflow', core_spec)
        self.assertIn('safe first-pass fixes', core_spec)
        self.assertIn('fixability', core_spec)
        self.assertIn('usage-example.md', adapter_mapping)
        self.assertIn('failure-guide.md', adapter_mapping)
        self.assertIn('e2e-example.md', adapter_mapping)
        self.assertIn('apply-fixes', adapter_mapping)
        self.assertIn('create', adapter_mapping)
        self.assertIn('modify', adapter_mapping)

    def test_wcag_citations_reference_all_supported_versions_and_merge_policy(self) -> None:
        content = self._read(self.skill_root / 'references' / 'wcag-citations.md')
        self.assertIn('WCAG 2.0', content)
        self.assertIn('WCAG 2.1', content)
        self.assertIn('WCAG 2.2', content)
        self.assertIn('2.4.11 Focus Not Obscured (Minimum)', content)
        self.assertIn('merge them into one finding and preserve both sources', content)

    def test_framework_pattern_guides_cover_key_rule_families(self) -> None:
        react = self._read(self.skill_root / 'references' / 'framework-patterns-react.md')
        vue = self._read(self.skill_root / 'references' / 'framework-patterns-vue.md')
        nextjs = self._read(self.skill_root / 'references' / 'framework-patterns-nextjs.md')
        self.assertIn('image-alt', react)
        self.assertIn('label', react)
        self.assertIn('button-name', vue)
        self.assertIn('html-has-lang', nextjs)
        self.assertIn('focus', nextjs.lower())

    def test_all_repo_files_have_a_test_or_static_contract_check(self) -> None:
        expected = {
            '.gitattributes',
            '.github/workflows/test.yml',
            '.github/workflows/install-skill.yml',
            '.gitignore',
            '.claude-plugin/plugin.json',
            '.claude-plugin/marketplace.json',
            '.gemini/skills/libro-wcag/SKILL.md',
            'mcp-server/server.py',
            'mcp-server/requirements.txt',
            'mcp-server/tools/audit_page.py',
            'mcp-server/tools/suggest_fixes.py',
            'mcp-server/tools/normalize_report.py',
            'LICENSE',
            'README.md',
            'SKILL-TODO.md',
            'TESTING-PLAN.md',
            'docs/automations/test-plan-automation.md',
            'docs/automations/test-plan-review-policy.md',
            'docs/automations/agent-installation-expansion-todo.md',
            'docs/examples/claude/mcp.sample.json',
            'docs/examples/claude/settings.add-dir.sample.json',
            'docs/examples/ci/install-skill-consumer-sample.yml',
            'docs/examples/ci/gh-release-download-sample.md',
            'docs/examples/copilot/mcp.sample.json',
            'docs/examples/gemini/settings.mcp.sample.json',
            'docs/testing/testing-playbook.md',
            'pyproject.toml',
            'scripts/doctor-agent.py',
            'scripts/bootstrap.ps1',
            'scripts/bootstrap.sh',
            'scripts/install-agent.ps1',
            'scripts/install-agent.py',
            'scripts/install-agent.sh',
            'scripts/uninstall-agent.py',
            'scripts/validate_skill.py',
            'skills/libro-wcag/SKILL.md',
            'skills/libro-wcag/agents/openai.yaml',
            'skills/libro-wcag/adapters/claude/e2e-example.md',
            'skills/libro-wcag/adapters/claude/failure-guide.md',
            'skills/libro-wcag/adapters/claude/prompt-template.md',
            'skills/libro-wcag/adapters/claude/usage-example.md',
            'skills/libro-wcag/adapters/copilot/e2e-example.md',
            'skills/libro-wcag/adapters/copilot/failure-guide.md',
            'skills/libro-wcag/adapters/copilot/prompt-template.md',
            'skills/libro-wcag/adapters/copilot/usage-example.md',
            'skills/libro-wcag/adapters/gemini/e2e-example.md',
            'skills/libro-wcag/adapters/gemini/failure-guide.md',
            'skills/libro-wcag/adapters/gemini/prompt-template.md',
            'skills/libro-wcag/adapters/gemini/usage-example.md',
            'skills/libro-wcag/adapters/openai-codex/e2e-example.md',
            'skills/libro-wcag/adapters/openai-codex/failure-guide.md',
            'skills/libro-wcag/adapters/openai-codex/prompt-template.md',
            'skills/libro-wcag/adapters/openai-codex/usage-example.md',
            'skills/libro-wcag/references/adapter-mapping.md',
            'skills/libro-wcag/references/core-spec.md',
            'skills/libro-wcag/references/framework-patterns-nextjs.md',
            'skills/libro-wcag/references/framework-patterns-react.md',
            'skills/libro-wcag/references/framework-patterns-vue.md',
            'skills/libro-wcag/references/wcag-citations.md',
            'skills/libro-wcag/scripts/auto_fix.py',
            'skills/libro-wcag/scripts/rewrite_helpers.py',
            'skills/libro-wcag/scripts/normalize_report.py',
            'skills/libro-wcag/scripts/remediation_library.py',
            'skills/libro-wcag/scripts/run_accessibility_audit.py',
            'skills/libro-wcag/scripts/wcag_workflow.py',
            '.codex/environments/environment.toml',
        }
        actual = {
            str(path.relative_to(self.repo_root)).replace('\\', '/')
            for path in self.repo_root.rglob('*')
            if path.is_file()
            and '.git' not in path.parts
            and '__pycache__' not in path.parts
            and '.tmp' not in path.parts
            and 'out-test-invalid' not in path.parts
            and '.tmp-test' not in path.parts
            and 'scripts/tests' not in str(path).replace('\\', '/')
        }
        self.assertTrue(expected.issubset(actual))


if __name__ == '__main__':
    unittest.main()
