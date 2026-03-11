#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


class RepoContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.skill_root = cls.repo_root / 'skills' / 'libro-agent-wcag'

    def _read(self, path: Path) -> str:
        return path.read_text(encoding='utf-8')

    def test_readme_covers_installation_validation_and_testing_plan(self) -> None:
        content = self._read(self.repo_root / 'README.md')
        self.assertIn('install-agent.py --agent codex', content)
        self.assertIn('doctor-agent.py --agent codex', content)
        self.assertIn('uninstall-agent.py --agent codex', content)
        self.assertIn('TESTING-PLAN.md', content)
        self.assertIn('$libro-agent-wcag', content)

    def test_testing_plan_tracks_matrix_mapping_and_gaps(self) -> None:
        content = self._read(self.repo_root / 'TESTING-PLAN.md')
        for heading in ['## Test Matrix', '## Repo Mapping', '## Already Implemented', '## Still Worth Adding']:
            self.assertIn(heading, content)
        self.assertIn('Automation Target', content)
        self.assertIn('Coverage Mode', content)
        self.assertIn('Scripted Manual', content)
        self.assertIn('Automated', content)

    def test_manual_testing_assets_exist_for_non_automated_matrix_types(self) -> None:
        manual = self._read(self.repo_root / 'docs' / 'testing' / 'manual-checklists.md')
        scenarios = self._read(self.repo_root / 'docs' / 'testing' / 'scenario-assets.md')
        nonfunctional = self._read(self.repo_root / 'docs' / 'testing' / 'nonfunctional-checks.md')
        self.assertIn('Acceptance Test / UAT', manual)
        self.assertIn('Beta Test', manual)
        self.assertIn('Decision Table', scenarios)
        self.assertIn('End-to-End Test', scenarios)
        self.assertIn('Performance Test', nonfunctional)
        self.assertIn('Concurrency Test', nonfunctional)

    def test_pyproject_declares_repo_metadata_and_test_path(self) -> None:
        content = self._read(self.repo_root / 'pyproject.toml')
        self.assertIn('name = "Libro.AgentWCAG"', content)
        self.assertIn('requires-python = ">=3.12"', content)
        self.assertIn('skills/libro-agent-wcag/scripts/tests', content)

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
        self.assertIn('skills/libro-agent-wcag/scripts/tests', workflow)
        self.assertIn('skills/libro-agent-wcag', workflow)

    def test_skill_frontmatter_and_usage_contract_exist(self) -> None:
        content = self._read(self.skill_root / 'SKILL.md')
        self.assertIn('name: libro-agent-wcag', content)
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
        self.assertIn('$libro-agent-wcag', payload['interface']['default_prompt'])

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
            '.gitignore',
            'LICENSE',
            'README.md',
            'SKILL-TODO.md',
            'TESTING-PLAN.md',
            'docs/automations/test-plan-automation.md',
            'docs/automations/test-plan-review-policy.md',
            'docs/testing/manual-checklists.md',
            'docs/testing/nonfunctional-checks.md',
            'docs/testing/scenario-assets.md',
            'pyproject.toml',
            'scripts/doctor-agent.py',
            'scripts/install-agent.ps1',
            'scripts/install-agent.py',
            'scripts/install-agent.sh',
            'scripts/uninstall-agent.py',
            'scripts/validate_skill.py',
            'skills/libro-agent-wcag/SKILL.md',
            'skills/libro-agent-wcag/agents/openai.yaml',
            'skills/libro-agent-wcag/adapters/claude/e2e-example.md',
            'skills/libro-agent-wcag/adapters/claude/failure-guide.md',
            'skills/libro-agent-wcag/adapters/claude/prompt-template.md',
            'skills/libro-agent-wcag/adapters/claude/usage-example.md',
            'skills/libro-agent-wcag/adapters/copilot/e2e-example.md',
            'skills/libro-agent-wcag/adapters/copilot/failure-guide.md',
            'skills/libro-agent-wcag/adapters/copilot/prompt-template.md',
            'skills/libro-agent-wcag/adapters/copilot/usage-example.md',
            'skills/libro-agent-wcag/adapters/gemini/e2e-example.md',
            'skills/libro-agent-wcag/adapters/gemini/failure-guide.md',
            'skills/libro-agent-wcag/adapters/gemini/prompt-template.md',
            'skills/libro-agent-wcag/adapters/gemini/usage-example.md',
            'skills/libro-agent-wcag/adapters/openai-codex/e2e-example.md',
            'skills/libro-agent-wcag/adapters/openai-codex/failure-guide.md',
            'skills/libro-agent-wcag/adapters/openai-codex/prompt-template.md',
            'skills/libro-agent-wcag/adapters/openai-codex/usage-example.md',
            'skills/libro-agent-wcag/references/adapter-mapping.md',
            'skills/libro-agent-wcag/references/core-spec.md',
            'skills/libro-agent-wcag/references/framework-patterns-nextjs.md',
            'skills/libro-agent-wcag/references/framework-patterns-react.md',
            'skills/libro-agent-wcag/references/framework-patterns-vue.md',
            'skills/libro-agent-wcag/references/wcag-citations.md',
            'skills/libro-agent-wcag/scripts/auto_fix.py',
            'skills/libro-agent-wcag/scripts/rewrite_helpers.py',
            'skills/libro-agent-wcag/scripts/normalize_report.py',
            'skills/libro-agent-wcag/scripts/remediation_library.py',
            'skills/libro-agent-wcag/scripts/run_accessibility_audit.py',
            'skills/libro-agent-wcag/scripts/wcag_workflow.py',
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
            and 'scripts/tests' not in str(path).replace('\\', '/')
        }
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
