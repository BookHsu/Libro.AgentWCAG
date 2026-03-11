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
- `scripts/doctor-agent.py`: installation health check for supported agents

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

After installation, check `install-manifest.json` inside the installed folder. It points to the correct adapter prompt for the selected agent and includes `usage_example`, `failure_guide`, and `e2e_example` paths.

### Verify installation

```powershell
python .\scripts\doctor-agent.py --agent codex
python .\scripts\doctor-agent.py --agent all
```

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

- `codex`: `adapters/openai-codex/prompt-template.md`, `usage-example.md`, `failure-guide.md`, and `e2e-example.md`
- `claude`: `adapters/claude/prompt-template.md`, `usage-example.md`, `failure-guide.md`, and `e2e-example.md`
- `gemini`: `adapters/gemini/prompt-template.md`, `usage-example.md`, `failure-guide.md`, and `e2e-example.md`
- `copilot`: `adapters/copilot/prompt-template.md`, `usage-example.md`, `failure-guide.md`, and `e2e-example.md`

### First-use guidance

- `codex`: invoke `$libro-agent-wcag` directly after installation.
- `claude`: load the installed `adapters/claude/prompt-template.md` into your Claude project/system prompt.
- `gemini`: load the installed `adapters/gemini/prompt-template.md` into your Gemini custom instruction or agent wrapper.
- `copilot`: load the installed `adapters/copilot/prompt-template.md` into your Copilot instruction or prompt file.

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
- For supported local HTML targets, the core Python workflow can now apply a safe first-pass remediation pass for language attributes, alt text gaps, simple control naming, ARIA naming widgets, document titles, list semantics (`list`/`listitem`), table caption normalization (`table-fake-caption`), meta refresh removal, and viewport normalization, then emit a diff artifact. Remaining or unsupported changes still belong to the calling agent or adapter.
- The core workflow still reports canonical fix metadata, and now includes a reusable remediation strategy library plus safe local HTML rewrite helpers for supported rules.

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

## Testing Strategy

- See `TESTING-PLAN.md` for the applicable test matrix, repo mapping, and current coverage status.
- See `SKILL-TODO.md` for the remaining skill-completion backlog and implementation checklist.

## Codex Automation

- Use `docs/automations/test-plan-automation.md` as the execution spec for scheduled Codex test-development automation. This lane focuses only on test development, testing-plan updates, commits, and pushes.
- Use `docs/automations/test-plan-review-policy.md` as the review policy before accepting automation-generated changes.

