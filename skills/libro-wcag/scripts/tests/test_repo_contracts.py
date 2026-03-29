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
        self.assertIn('## 專案的用途與說明', content)
        self.assertIn('## 前置需求', content)
        self.assertIn('## 安裝方式', content)
        self.assertIn('## 使用方式', content)
        self.assertIn('python --version', content)
        self.assertIn('brew install python3                         # macOS', content)
        self.assertIn('sudo apt update && sudo apt install python3 # Ubuntu / Debian', content)
        self.assertIn('winget install Python.Python.3.12           # Windows', content)
        self.assertIn('### Claude Marketplace (Claude Code)', content)
        self.assertIn('### npm CLI', content)
        self.assertIn('### Clone + CLI', content)
        self.assertIn('/plugin marketplace add BookHsu/Libro.AgentWCAG', content)
        self.assertIn('/plugin install libro-wcag@libro-wcag-marketplace', content)
        self.assertIn('npm install -g librowcag-cli', content)
        self.assertIn('libro install claude   # Claude Code', content)
        self.assertIn('libro install gemini   # Gemini CLI', content)
        self.assertIn('libro install copilot  # Copilot', content)
        self.assertIn('libro install codex    # Codex', content)
        self.assertIn('libro doctor claude    # verify Claude installation', content)
        self.assertIn('libro.py install claude', content)
        self.assertIn('libro.py doctor claude', content)
        self.assertIn('libro.py remove claude', content)
        self.assertIn('| 模式 | 會找問題 | 會給修正建議 | 會改檔 |', content)
        self.assertIn('| `audit-only` | 是 | 否 | 否 |', content)
        self.assertIn('| `suggest-only` | 是 | 是 | 否 |', content)
        self.assertIn('| `apply-fixes` | 是 | 是 | 是，僅限支援的本機檔案 |', content)
        self.assertIn('使用範例：', content)
        self.assertIn('請用 audit-only 模式檢查 https://example.com，WCAG 2.1 AA。', content)
        self.assertIn('請用 suggest-only 模式檢查 src/page.html，並提供修正建議，但不要改檔。', content)
        self.assertIn('請用 apply-fixes 模式檢查 src/page.html，並在安全範圍內直接修正可處理的問題。', content)
        self.assertIn('## License', content)
        self.assertIn('MIT. See [LICENSE](LICENSE).', content)

    def test_package_json_exposes_global_libro_cli(self) -> None:
        payload = json.loads((self.repo_root / 'package.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['name'], 'librowcag-cli')
        self.assertEqual(payload['version'], tomllib.loads((self.repo_root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
        self.assertEqual(payload['bin']['libro'], 'bin/libro.js')
        self.assertEqual(payload['publishConfig']['access'], 'public')
        self.assertNotIn('provenance', payload['publishConfig'])
        self.assertIn('scripts/*.py', payload['files'])
        self.assertIn('scripts/*.ps1', payload['files'])
        self.assertIn('packaging/templates/workspace/', payload['files'])
        self.assertIn('packaging/templates/claude-plugin/', payload['files'])
        self.assertIn('skills/libro-wcag/scripts/*.py', payload['files'])
        self.assertIn('skills/libro-wcag/scripts/py.typed', payload['files'])

    def test_npmignore_excludes_tests_and_python_cache_from_published_cli(self) -> None:
        content = self._read(self.repo_root / '.npmignore')
        self.assertIn('**/__pycache__/', content)
        self.assertIn('**/*.pyc', content)
        self.assertIn('skills/libro-wcag/scripts/tests/', content)
        self.assertNotIn('.codex/', content)
        self.assertNotIn('.claude/', content)
        self.assertNotIn('.gemini/', content)

    def test_testing_plan_tracks_matrix_mapping_and_gaps(self) -> None:
        content = self._read(self.repo_root / 'docs' / 'testing' / 'test-matrix.md')
        for heading in ['## Test Matrix', '## Repo Mapping', '## Already Implemented', '## Still Worth Adding']:
            self.assertIn(heading, content)
        self.assertIn('Automation Target', content)
        self.assertIn('Coverage Mode', content)
        self.assertIn('Scripted Manual', content)
        self.assertIn('Automated', content)

    def test_claude_workspace_template_exists_and_tracks_core_contract(self) -> None:
        core_skill = self._read(self.skill_root / 'SKILL.md')
        workspace_skill = self._read(self.repo_root / 'packaging' / 'templates' / 'workspace' / 'claude' / 'skills' / 'libro-wcag' / 'SKILL.md')
        self.assertIn('name: libro-wcag', workspace_skill)
        self.assertIn('Claude-specific note', workspace_skill)
        self.assertIn('execution_mode', workspace_skill)
        self.assertIn('safe first-pass remediations', workspace_skill)
        self.assertIn('Use `adapters/claude/prompt-template.md`', workspace_skill)
        self.assertIn('JSON top-level keys', workspace_skill)
        self.assertIn('JSON top-level keys', core_skill)

    def test_gemini_workspace_template_exists_and_tracks_core_contract(self) -> None:
        core_skill = self._read(self.skill_root / 'SKILL.md')
        workspace_skill = self._read(self.repo_root / 'packaging' / 'templates' / 'workspace' / 'gemini' / 'skills' / 'libro-wcag' / 'SKILL.md')
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
        self.assertIn('uses: BookHsu/Libro.AgentWCAG/.github/workflows/install-skill.yml@v1', reusable)
        self.assertIn('gh release download', gh_release)
        self.assertIn('install-agent.py --agent claude', gh_release)

    def test_mcp_samples_exist_for_claude_copilot_and_gemini(self) -> None:
        claude = self._read(self.repo_root / 'docs' / 'examples' / 'claude' / 'mcp.sample.json')
        copilot = self._read(self.repo_root / 'docs' / 'examples' / 'copilot' / 'mcp.sample.json')
        gemini = self._read(self.repo_root / 'docs' / 'examples' / 'gemini' / 'settings.mcp.sample.json')
        self.assertIn('mcp-server/server.py', claude)
        self.assertIn('"servers"', copilot)
        self.assertIn('"mcpServers"', gemini)

    def test_publish_npm_workflow_exists_with_oidc_contract(self) -> None:
        content = self._read(self.repo_root / '.github' / 'workflows' / 'publish-npm.yml')
        self.assertIn('id-token: write', content)
        self.assertIn('contents: read', content)
        self.assertIn('node-version: "24"', content)
        self.assertIn('npm publish --access public', content)
        self.assertIn('apply-release-version.py', content)

    def test_claude_plugin_json_exists_and_has_required_fields(self) -> None:
        payload = json.loads((self.repo_root / 'packaging' / 'templates' / 'claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['name'], 'libro-wcag')
        self.assertEqual(payload['license'], 'MIT')
        self.assertIn('version', payload)
        self.assertIn('description', payload)
        self.assertEqual(payload['repository'], 'https://github.com/BookHsu/Libro.AgentWCAG')
        self.assertIn('mcpServers', payload)
        self.assertIn('libro-wcag', payload['mcpServers'])

    def test_claude_marketplace_json_exists_and_references_plugin(self) -> None:
        payload = json.loads((self.repo_root / 'packaging' / 'templates' / 'claude-plugin' / 'marketplace.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['name'], 'libro-wcag-marketplace')
        self.assertEqual(len(payload['plugins']), 1)
        self.assertEqual(payload['plugins'][0]['name'], 'libro-wcag')
        self.assertEqual(payload['plugins'][0]['source'], './')

    def test_claude_plugin_version_matches_pyproject(self) -> None:
        plugin = json.loads((self.repo_root / 'packaging' / 'templates' / 'claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))
        pyproject = tomllib.loads((self.repo_root / 'pyproject.toml').read_text(encoding='utf-8'))
        self.assertEqual(plugin['version'], pyproject['project']['version'])

    def test_claude_marketplace_version_matches_plugin(self) -> None:
        plugin = json.loads((self.repo_root / 'packaging' / 'templates' / 'claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))
        marketplace = json.loads((self.repo_root / 'packaging' / 'templates' / 'claude-plugin' / 'marketplace.json').read_text(encoding='utf-8'))
        self.assertEqual(marketplace['plugins'][0]['version'], plugin['version'])

    def test_source_checkout_does_not_ship_workspace_product_assets_at_root(self) -> None:
        self.assertFalse((self.repo_root / '.claude' / 'skills' / 'libro-wcag' / 'SKILL.md').exists())
        self.assertFalse((self.repo_root / '.codex' / 'skills' / 'libro-wcag' / 'SKILL.md').exists())
        self.assertFalse((self.repo_root / '.copilot' / 'skills' / 'libro-wcag' / 'SKILL.md').exists())
        self.assertFalse((self.repo_root / '.gemini' / 'skills' / 'libro-wcag' / 'SKILL.md').exists())
        self.assertFalse((self.repo_root / '.codex' / 'environments' / 'environment.toml').exists())
        self.assertFalse((self.repo_root / '.claude-plugin' / 'plugin.json').exists())
        self.assertFalse((self.repo_root / '.claude-plugin' / 'marketplace.json').exists())

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

    def test_skill_script_package_has_explicit_init_and_typed_markers(self) -> None:
        scripts_init = self.skill_root / 'scripts' / '__init__.py'
        tests_init = self.skill_root / 'scripts' / 'tests' / '__init__.py'
        py_typed = self.skill_root / 'scripts' / 'py.typed'
        self.assertTrue(scripts_init.exists())
        self.assertTrue(tests_init.exists())
        self.assertTrue(py_typed.exists())

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

    def test_agent_manifests_point_to_libro_agentwcag_prompt(self) -> None:
        expected_prompts = {
            'openai.yaml': '$libro-wcag',
            'claude.yaml': 'adapters/claude/prompt-template.md',
            'gemini.yaml': 'adapters/gemini/prompt-template.md',
            'copilot.yaml': 'adapters/copilot/prompt-template.md',
        }
        for manifest_name, adapter_hint in expected_prompts.items():
            with self.subTest(manifest_name=manifest_name):
                payload = yaml.safe_load(
                    (self.skill_root / 'agents' / manifest_name).read_text(encoding='utf-8')
                )
                self.assertEqual(payload['interface']['display_name'], 'Libro.AgentWCAG')
                self.assertIn('$libro-wcag', payload['interface']['default_prompt'])
                self.assertIn(adapter_hint, payload['interface']['default_prompt'])

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

    def test_report_schema_defines_core_finding_fix_and_summary_contract_fields(self) -> None:
        payload = json.loads(
            (self.skill_root / 'schemas' / 'wcag-report-1.0.0.schema.json').read_text(encoding='utf-8')
        )
        run_meta = payload['$defs']['runMeta']
        finding = payload['$defs']['finding']
        fix = payload['$defs']['fix']
        summary = payload['$defs']['summary']

        self.assertEqual(
            run_meta['properties']['diff_artifacts']['items']['required'],
            ['path', 'type'],
        )

        self.assertIn('fixability', finding['required'])
        self.assertIn('verification_status', finding['required'])
        self.assertIn('manual_review_required', finding['required'])
        self.assertIn('confidence', finding['required'])
        self.assertIn('sc', finding['required'])
        self.assertEqual(finding['properties']['fixability']['$ref'], '#/$defs/fixability')
        self.assertEqual(
            finding['properties']['verification_status']['$ref'],
            '#/$defs/verificationStatus',
        )

        self.assertIn('remediation_priority', fix['required'])
        self.assertIn('confidence', fix['required'])
        self.assertIn('fixability', fix['required'])
        self.assertIn('verification_status', fix['required'])
        self.assertIn('manual_review_required', fix['required'])
        self.assertIn('framework_hints', fix['required'])
        self.assertEqual(
            fix['properties']['remediation_priority']['$ref'],
            '#/$defs/remediationPriority',
        )
        self.assertEqual(fix['properties']['framework_hints']['type'], 'object')

        self.assertIn('diff_summary', summary['required'])
        self.assertIn('remediation_lifecycle', summary['required'])
        self.assertIn('change_summary', summary['required'])
        self.assertIn('auto_fixed_count', summary['required'])
        self.assertIn('manual_required_count', summary['required'])
        self.assertIn('debt_trend', summary['properties'])
        self.assertEqual(
            summary['properties']['debt_trend']['properties']['latest_counts']['$ref'],
            '#/$defs/debtTrendCounts',
        )

    def test_report_schema_uses_enums_for_status_and_priority_vocabularies(self) -> None:
        payload = json.loads(
            (self.skill_root / 'schemas' / 'wcag-report-1.0.0.schema.json').read_text(encoding='utf-8')
        )
        self.assertEqual(payload['$defs']['fixability']['enum'], ['auto-fix', 'assisted', 'manual'])
        self.assertEqual(
            payload['$defs']['verificationStatus']['enum'],
            ['not-run', 'diff-generated', 'verified', 'manual-review'],
        )
        self.assertEqual(payload['$defs']['remediationPriority']['enum'], ['high', 'medium', 'low'])
        self.assertEqual(
            payload['$defs']['severity']['enum'],
            ['critical', 'serious', 'moderate', 'minor', 'info'],
        )

    def test_framework_pattern_guides_cover_key_rule_families(self) -> None:
        react = self._read(self.skill_root / 'references' / 'framework-patterns-react.md')
        vue = self._read(self.skill_root / 'references' / 'framework-patterns-vue.md')
        nextjs = self._read(self.skill_root / 'references' / 'framework-patterns-nextjs.md')
        self.assertIn('image-alt', react)
        self.assertIn('label', react)
        self.assertIn('button-name', vue)
        self.assertIn('html-has-lang', nextjs)
        self.assertIn('focus', nextjs.lower())

    def test_mcp_tool_defaults_match_skill_md_contract(self) -> None:
        """C5: MCP tool parameter defaults must align with SKILL.md."""
        import ast

        server_src = self._read(self.repo_root / 'mcp-server' / 'server.py')
        skill_md = self._read(self.skill_root / 'SKILL.md')
        tree = ast.parse(server_src)

        # Extract default values from MCP tool function signatures
        mcp_defaults: dict[str, dict[str, str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('libro_wcag_'):
                defaults: dict[str, str] = {}
                args = node.args
                # Match defaults to the last N arguments
                num_defaults = len(args.defaults)
                default_args = args.args[-num_defaults:] if num_defaults else []
                for arg, default in zip(default_args, args.defaults):
                    if isinstance(default, ast.Constant) and isinstance(default.value, str):
                        defaults[arg.arg] = default.value
                mcp_defaults[node.name] = defaults

        self.assertIn('libro_wcag_audit', mcp_defaults)
        self.assertIn('libro_wcag_suggest', mcp_defaults)
        self.assertIn('libro_wcag_normalize', mcp_defaults)

        # SKILL.md contract defaults
        skill_defaults = {
            'wcag_version': '2.1',
            'conformance_level': 'AA',
            'output_language': 'zh-TW',
        }

        # All three MCP tools must share the same core defaults
        for tool_name, defaults in mcp_defaults.items():
            with self.subTest(tool=tool_name):
                for param, expected in skill_defaults.items():
                    self.assertEqual(
                        defaults.get(param),
                        expected,
                        f'{tool_name}.{param} default {defaults.get(param)!r} != SKILL.md {expected!r}',
                    )

        # MCP audit deliberately uses audit-only (not suggest-only) per Batch 6 decision
        self.assertEqual(mcp_defaults['libro_wcag_audit']['execution_mode'], 'audit-only')
        # MCP normalize uses suggest-only (matches SKILL.md default)
        self.assertEqual(mcp_defaults['libro_wcag_normalize']['execution_mode'], 'suggest-only')

        # Verify SKILL.md documents these exact defaults
        self.assertIn('`execution_mode`: `suggest-only`', skill_md)
        self.assertIn('`wcag_version`: `2.1`', skill_md)
        self.assertIn('`conformance_level`: `AA`', skill_md)
        self.assertIn('`output_language`: `zh-TW`', skill_md)

    def test_all_repo_files_have_a_test_or_static_contract_check(self) -> None:
        expected = {
            '.gitattributes',
            '.github/workflows/test.yml',
            '.github/workflows/install-skill.yml',
            '.github/workflows/publish-npm.yml',
            '.gitignore',
            'packaging/templates/workspace/claude/skills/libro-wcag/SKILL.md',
            'packaging/templates/workspace/codex/skills/libro-wcag/SKILL.md',
            'packaging/templates/workspace/codex/environments/environment.toml',
            'packaging/templates/workspace/copilot/skills/libro-wcag/SKILL.md',
            'packaging/templates/workspace/gemini/skills/libro-wcag/SKILL.md',
            'packaging/templates/claude-plugin/plugin.json',
            'packaging/templates/claude-plugin/marketplace.json',
            'mcp-server/server.py',
            'mcp-server/requirements.txt',
            'mcp-server/tools/audit_page.py',
            'mcp-server/tools/suggest_fixes.py',
            'mcp-server/tools/normalize_report.py',
            'bin/libro.js',
            'LICENSE',
            'README.md',
            'docs/testing/test-matrix.md',
            'docs/archive/decisions/markdown-cleanup-20260329.md',
            'docs/examples/claude/mcp.sample.json',
            'docs/examples/claude/settings.add-dir.sample.json',
            'docs/examples/ci/install-skill-consumer-sample.yml',
            'docs/examples/ci/gh-release-download-sample.md',
            'docs/examples/copilot/mcp.sample.json',
            'docs/examples/gemini/settings.mcp.sample.json',
            'docs/testing/testing-playbook.md',
            'package.json',
            'pyproject.toml',
            'scripts/libro.ps1',
            'scripts/libro.py',
            'scripts/libro.sh',
            'scripts/doctor-agent.py',
            'scripts/bootstrap.ps1',
            'scripts/bootstrap.sh',
            'scripts/apply-release-version.py',
            'scripts/install-agent.ps1',
            'scripts/install-agent.py',
            'scripts/install-agent.sh',
            'scripts/uninstall-agent.py',
            'scripts/validate_skill.py',
            'skills/libro-wcag/SKILL.md',
            'skills/libro-wcag/agents/claude.yaml',
            'skills/libro-wcag/agents/copilot.yaml',
            'skills/libro-wcag/agents/gemini.yaml',
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


class WcagUrlSlugTests(unittest.TestCase):
    """Z3: Validate WCAG_UNDERSTANDING_PATHS slugs are well-formed and (optionally) reachable."""

    @classmethod
    def setUpClass(cls) -> None:
        import sys
        scripts_dir = str(Path(__file__).resolve().parents[1])
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from wcag_workflow import WCAG_UNDERSTANDING_PATHS, build_citation_url
        cls.paths = WCAG_UNDERSTANDING_PATHS
        cls.build_url = staticmethod(build_citation_url)

    def test_all_slugs_are_lowercase_hyphenated(self) -> None:
        import re
        slug_pattern = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
        for sc, slug in self.paths.items():
            with self.subTest(sc=sc):
                self.assertRegex(slug, slug_pattern, f'SC {sc} slug {slug!r} is not lowercase-hyphenated')

    def test_all_sc_numbers_are_valid_format(self) -> None:
        import re
        sc_pattern = re.compile(r'^\d+\.\d+\.\d+$')
        for sc in self.paths:
            with self.subTest(sc=sc):
                self.assertRegex(sc, sc_pattern, f'{sc!r} is not a valid SC number format')

    def test_no_duplicate_slugs(self) -> None:
        slugs = list(self.paths.values())
        self.assertEqual(len(slugs), len(set(slugs)), 'Duplicate slugs found')

    def test_build_citation_url_produces_valid_urls_for_all_versions(self) -> None:
        for sc in self.paths:
            for version in ('2.0', '2.1', '2.2'):
                with self.subTest(sc=sc, version=version):
                    url = self.build_url(version, sc)
                    self.assertTrue(url.startswith('https://www.w3.org/WAI/WCAG'))
                    self.assertIn(f'WCAG{version.replace(".", "")}', url)

    @unittest.skipUnless(
        __import__('os').environ.get('LIBRO_RUN_URL_VALIDATION') == '1',
        'WCAG URL HEAD validation disabled (set LIBRO_RUN_URL_VALIDATION=1)',
    )
    def test_all_wcag_understanding_urls_are_reachable(self) -> None:
        import urllib.request
        failures: list[str] = []
        for sc, slug in self.paths.items():
            url = self.build_url('2.2', sc)
            try:
                req = urllib.request.Request(url, method='HEAD')
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status != 200:
                        failures.append(f'{sc} ({slug}): HTTP {resp.status}')
            except Exception as exc:
                failures.append(f'{sc} ({slug}): {exc}')
        self.assertEqual(failures, [], f'Unreachable WCAG URLs:\n' + '\n'.join(failures))


if __name__ == '__main__':
    unittest.main()
