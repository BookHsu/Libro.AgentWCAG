# WCAG Web Skill

Cross-agent WCAG web accessibility skill for creating or remediating web pages with a shared vendor-neutral contract.

## Repository layout

- `skills/wcag-web-skill`: installable skill payload
- `skills/wcag-web-skill/adapters/openai-codex`: v1 adapter for OpenAI/Codex
- `skills/wcag-web-skill/adapters/claude`: v1 adapter for Claude
- `skills/wcag-web-skill/adapters/gemini`: v2 adapter for Gemini
- `skills/wcag-web-skill/adapters/copilot`: v2 adapter for Copilot

## Install into Codex

After publishing this repository to GitHub, install the skill from the repo path:

```powershell
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo <owner>/<repo> --path skills/wcag-web-skill
```

Restart Codex after installation.

## Use in other AI agents

The platform-neutral contract lives here:

- `skills/wcag-web-skill/SKILL.md`
- `skills/wcag-web-skill/references/core-spec.md`
- `skills/wcag-web-skill/references/adapter-mapping.md`
- `skills/wcag-web-skill/references/framework-patterns-react.md`
- `skills/wcag-web-skill/references/framework-patterns-vue.md`
- `skills/wcag-web-skill/references/framework-patterns-nextjs.md`

Adapters can translate the same core contract into each platform's prompt or tool syntax.

The shared contract supports three execution modes:

- `audit-only`: find issues only
- `suggest-only`: find issues and propose fixes
- `apply-fixes`: apply fixes when the user explicitly requests modification

Language support:

- Markdown summary text and table headers follow `output_language`
- JSON field names remain canonical English keys
- Unsupported languages currently fall back to English

The shared contract also distinguishes task intent:

- `create`: review a draft, generated page, or template before release
- `modify`: audit an existing target first, then propose or apply changes

Current implementation note:

- `apply-fixes` is an execution intent exposed through the contract and report output.
- The actual file modification step is performed by the calling agent or adapter, not by the core Python workflow.
- The core workflow reports `files_modified=false`, but now includes a reusable remediation strategy library with priority, confidence, auto-fix support flags, and framework hints.

Current adapter coverage:

- OpenAI/Codex
- Claude
- Gemini
- Copilot

## Local validation

```powershell
python -m unittest discover -s skills/wcag-web-skill/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/wcag-web-skill
```

## Runtime requirements

- Python 3.12+
- Node.js and `npx`
- `@axe-core/cli` and `lighthouse` available through `npx`
- `PyYAML` for skill validation

## Future directions

- Actual file-rewriting auto-remediation engine for `apply-fixes`
- Release packaging extras such as demos, templates, and issue forms
