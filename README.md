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

Adapters can translate the same core contract into each platform's prompt or tool syntax.

The shared contract supports three execution modes:

- `audit-only`: find issues only
- `suggest-only`: find issues and propose fixes
- `apply-fixes`: apply fixes when the user explicitly requests modification

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
