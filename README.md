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
- For supported local targets (`.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, `.vue`), the core Python workflow applies safe first-pass deterministic rewrites (language attributes, alt text, control naming, ARIA naming/validity, document/title/list/table semantics, and viewport/meta refresh handling), then emits diff artifacts when changes are made.
- Non-local targets, unsupported local file types, and higher-risk remediation classes remain `suggest-only` or assisted/manual by design. See `docs/release/apply-fixes-scope.md` for the explicit scope matrix and boundaries.
- Scanner runtime resilience is configurable via `--scanner-retry-attempts` and `--scanner-retry-backoff-seconds`. See `docs/release/resilient-run-patterns.md` for recommended CI patterns.
- CI policy controls are available via `--report-format (json|sarif)`, `--fail-on`, `--include-rule`, `--ignore-rule`, `--policy-config`, and `--policy-preset (strict|balanced|legacy)` for deterministic gating and per-project rule policy. `--policy-config` now validates unsupported keys up front to avoid silent policy drift. Use `--list-policy-presets` for machine-readable preset discovery in scripts/automation. `--sort-findings` and `--max-findings` keep output ordering deterministic and report volume manageable for CI triage.
- Baseline diff gating is available via `--baseline-report` and `--fail-on-new-only` to fail only on newly introduced unresolved debt. Signature churn can be tuned with `--baseline-include-target`, `--baseline-target-normalization`, and `--baseline-selector-canonicalization`. `--summary-only` prints a compact JSON gate summary while still writing full artifacts to disk, including scanner capability negotiation metadata (`available_scanners`, `unavailable_scanners`, `available_rule_count`). Add `--explain-policy` to include the fully merged effective policy in `run_meta.policy_effective` and compact summary output for CI debugging/audits. Use `--write-effective-policy` to persist merged policy (including source provenance) to a standalone JSON artifact. JSON reports now include `report_schema.version` (`1.0.0`) and stage schema artifacts under `out/schemas/wcag-report-1.0.0.schema.json` for CI compatibility checks before parsing.

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

## Release readiness

- `docs/release/release-checklist.md`:  packaging, validation, and publish gate checklist
- `CHANGELOG.md`:  versioned release notes baseline
- `docs/release/release-notes-workflow.md`:  release-notes update workflow
- `docs/release/supported-environments.md`:  supported runtime and toolchain matrix
- `docs/release/first-run-smoke.md`:  install-plus-doctor first-run smoke guide
- `docs/release/apply-fixes-scope.md`:  explicit apply-fixes scope, boundaries, and remediation classes
- `docs/release/demo-package-walkthrough.md`:  minimal package-style validation walkthrough outside test suite
- `docs/release/prompt-invocation-templates.md`:  reusable contract and adapter invocation templates
- `docs/release/troubleshooting-intake.md`:  triage intake checklist for install and remediation problems
- `docs/release/resilient-run-patterns.md`:  resilient scanner retry/backoff, policy gates, baseline-diff CLI patterns, and triage workflow checklists for CI handoff
- `docs/release/github-actions-wcag-ci-sample.yml`:  GitHub Actions sample with artifact retention and SARIF PR annotation
- `docs/release/release-packaging-extras-placement.md`:  decision record for extras placement
- `.github/ISSUE_TEMPLATE/installation-failure.yml`:  installation failure intake form
- `.github/ISSUE_TEMPLATE/remediation-mismatch.yml`:  remediation mismatch intake form

## Future directions
- Broader safe rewrite coverage after regression baselines prove stability for additional rule families
## Testing Strategy

- See `TESTING-PLAN.md` for the applicable test matrix, repo mapping, and current coverage status.
- See `SKILL-TODO.md` for the remaining skill-completion backlog and implementation checklist.

## Codex Automation

- Use `docs/automations/test-plan-automation.md` as the execution spec for scheduled Codex test-development automation. This lane focuses only on test development, testing-plan updates, commits, and pushes.
- Use `docs/automations/test-plan-review-policy.md` as the review policy before accepting automation-generated changes.
