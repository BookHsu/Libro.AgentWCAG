# Libro.AgentWCAG

Libro.AgentWCAG is a cross-agent WCAG web accessibility skill repository for creating or remediating web pages with a shared vendor-neutral contract.

## Repository layout

- `skills/libro-agent-wcag`: installable skill payload
- `skills/libro-agent-wcag/adapters/openai-codex`: v1 adapter for OpenAI/Codex
- `skills/libro-agent-wcag/adapters/claude`: v1 adapter for Claude
- `skills/libro-agent-wcag/adapters/gemini`: v2 adapter for Gemini
- `skills/libro-agent-wcag/adapters/copilot`: v2 adapter for Copilot
- `scripts/install-agent.py`: repo-native installer for supported agents
- `scripts/uninstall-agent.py`: repo-native uninstaller for supported agents

## Install

Recommended installation uses the repo-native installer instead of a Codex-internal helper path.

### Install a single agent bundle

```powershell
python .\scripts\install-agent.py --agent codex
python .\scripts\install-agent.py --agent claude
python .\scripts\install-agent.py --agent gemini
python .\scripts\install-agent.py --agent copilot
```

### Install all supported agent bundles at once

```powershell
python .\scripts\install-agent.py --agent all
```

### Wrapper scripts

```powershell
pwsh -File .\scripts\install-agent.ps1 -Agent codex
pwsh -File .\scripts\install-agent.ps1 -Agent all
```

```sh
sh ./scripts/install-agent.sh codex
sh ./scripts/install-agent.sh all
```

### Default destinations

- `codex`: `~/.codex/skills/libro-agent-wcag`
- `claude`: `~/.claude/skills/libro-agent-wcag`
- `gemini`: `~/.gemini/skills/libro-agent-wcag`
- `copilot`: `~/.copilot/skills/libro-agent-wcag`

Use `--dest <path>` to override, and `--force` to replace an existing installation.
When `--agent all` is combined with `--dest`, the installer creates `codex/`, `claude/`, `gemini/`, and `copilot/` subdirectories under that base path.

After installation, check `install-manifest.json` inside the installed folder. It points to the correct adapter prompt for the selected agent.

### Uninstall

```powershell
python .\scripts\uninstall-agent.py --agent codex
python .\scripts\uninstall-agent.py --agent all
```

## Use in AI agents

The platform-neutral contract lives here:

- `skills/libro-agent-wcag/SKILL.md`
- `skills/libro-agent-wcag/references/core-spec.md`
- `skills/libro-agent-wcag/references/adapter-mapping.md`
- `skills/libro-agent-wcag/references/framework-patterns-react.md`
- `skills/libro-agent-wcag/references/framework-patterns-vue.md`
- `skills/libro-agent-wcag/references/framework-patterns-nextjs.md`

Adapters can translate the same core contract into each platform's prompt or tool syntax.

### Agent-specific entrypoints

- `codex`: `adapters/openai-codex/prompt-template.md`
- `claude`: `adapters/claude/prompt-template.md`
- `gemini`: `adapters/gemini/prompt-template.md`
- `copilot`: `adapters/copilot/prompt-template.md`

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
python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-agent-wcag
```

## Runtime requirements

- Python 3.12+
- Node.js and `npx`
- `@axe-core/cli` and `lighthouse` available through `npx`
- `PyYAML` for skill validation

## Future directions

- Actual file-rewriting auto-remediation engine for `apply-fixes`
- Release packaging extras such as demos, templates, and issue forms
