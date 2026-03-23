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

After installation, check `install-manifest.json` inside the installed folder. It points to the correct adapter prompt for the selected agent and includes `usage_example`, `failure_guide`, and `e2e_example` paths, plus `product_version` and `source_revision` for release provenance.

### Verify installation

```powershell
python .\scripts\doctor-agent.py --agent codex
python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity
python .\scripts\doctor-agent.py --agent all
```

`scripts/install-agent.py`, `scripts/doctor-agent.py`, and `skills/libro-agent-wcag/scripts/report_artifacts.py` now read `product_version` from `pyproject.toml` through a shared helper. `source_revision` resolves from `LIBRO_AGENTWCAG_SOURCE_REVISION` when set, otherwise from the local git `HEAD`. `LIBRO_AGENTWCAG_BUILD_TIMESTAMP` is an optional UTC ISO-8601 override for release packaging lanes. Missing `project.version` or unresolved `source_revision` fail fast instead of emitting partial provenance.

`doctor-agent.py` also emits machine-readable version consistency fields so downstream smoke and release checks can compare the installed manifest against the current repo/package provenance without reparsing `pyproject.toml` in multiple places.

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
- Scanner runtime resilience is configurable via `--scanner-retry-attempts` and `--scanner-retry-backoff-seconds`. See `docs/release/resilient-run-patterns.md` for recommended CI patterns, including the reproducible dependency-audit lane (`pip-audit` + `npm audit`).
- CI policy controls are available via `--report-format (json|sarif)`, `--fail-on`, `--include-rule`, `--ignore-rule`, `--policy-config`, `--policy-preset (strict|balanced|legacy)`, and `--policy-bundle (strict-web-app|legacy-content|marketing-site)` for deterministic gating and per-project rule policy. `--policy-config` now validates unsupported keys up front to avoid silent policy drift; use `--list-policy-config-keys` for machine-readable key discovery in scripts/automation. Use `--list-policy-presets` for preset discovery, and `--strict-rule-overlap` to fail fast when the same rule id appears in both include/ignore lists. `--sort-findings` and `--max-findings` keep output ordering deterministic and report volume manageable for CI triage.
- Baseline diff gating is available via `--baseline-report` and `--fail-on-new-only` to fail only on newly introduced unresolved debt. Signature churn can be tuned with `--baseline-include-target`, `--baseline-target-normalization`, and `--baseline-selector-canonicalization`. Baseline updates now emit debt lifecycle metadata (`run_meta.baseline_diff.debt_transitions` and finding-level `debt_state`) for `new`, `accepted`, and `retired` tracking across refreshes. Debt waivers can be declared in baseline JSON via `debt_waivers[]` (`signature`, `owner`, `approved_at`, `expires_at`, `reason`) with strict schema validation; use `--waiver-expiry-mode (ignore|warn|fail)` to enforce renewal/retirement before release gates. Trend intelligence is available via `--debt-trend-window <N>` and emits `debt-trend.json` plus `summary.debt_trend`/`run_meta.debt_trend` highlights (`new`, `accepted`, `retired`, `regressed`) across the latest baseline window. Use `--baseline-evidence-mode (none|hash|hash-chain)` to verify baseline provenance and fail fast on tampered evidence before debt transitions are applied. Use `--replay-verify-from <report-dir>` to run remediation replay verification and emit `replay-summary.json` / `replay-diff.md` with deterministic high-severity regression gating. Use `--stability-baseline <path>` with `--stability-mode (off|warn|fail)` to emit `scanner-stability.json` and compare per-scanner/per-rule/per-target volatility against approved bounds, including deterministic downgrade messaging when scanner capability drifts. Every run now stages `artifact-manifest.json` with per-artifact `sha256`, size, timestamp, and generator metadata for CI handoff integrity checks; generator metadata includes `product_version`, `source_revision`, and the unchanged report schema version. JSON reports expose the same provenance in `run_meta.product`, Markdown reports append a `Report Metadata` section, and SARIF exports set driver `version` plus provenance properties. `--summary-only` prints a compact JSON gate summary while still writing full artifacts to disk, including scanner capability negotiation metadata (`available_scanners`, `unavailable_scanners`, `available_rule_count`) and minimal product provenance (`product_version`, `source_revision`, `report_schema_version`). Add `--explain-policy` to include the fully merged effective policy in `run_meta.policy_effective` and compact summary output for CI debugging/audits. Use `--write-effective-policy` to persist merged policy (including source provenance) to a standalone JSON artifact. JSON reports now include `report_schema.version` (`1.0.0`) and stage schema artifacts under `out/schemas/wcag-report-1.0.0.schema.json` for CI compatibility checks before parsing.

Current adapter coverage:

- OpenAI/Codex
- Claude
- Gemini
- Copilot

## Local validation

```powershell
python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-agent-wcag --validate-policy-bundles
```

## Runtime requirements

- Python 3.12+
- Node.js and `npx`
- `@axe-core/cli` and `lighthouse` available through `npx`
- `PyYAML` for skill validation
- `pip-audit` for dependency-audit lane and supply-chain gate checks

## Release readiness

- Create versioned release assets from the repo root with `python .\scripts\package-release.py --output-dir .\dist\release --overwrite`.
- Packaging emits deterministic bundle names: `libro-agent-wcag-<version>-codex.zip`, `libro-agent-wcag-<version>-claude.zip`, `libro-agent-wcag-<version>-gemini.zip`, `libro-agent-wcag-<version>-copilot.zip`, and `libro-agent-wcag-<version>-all-in-one.zip`.
- Companion release artifacts are `libro-agent-wcag-<version>-release-manifest.json`, `libro-agent-wcag-<version>-sha256sums.txt`, and `latest-release.json`.
- Release bundles intentionally exclude `skills/libro-agent-wcag/scripts/tests/`, `docs/testing/`, and `docs/archive/`; use the versioned release manifest and checksum file for downstream verification.
- `docs/release/release-playbook.md`: packaging, validation, publish gate checklist, and release-notes workflow
- `CHANGELOG.md`:  versioned release notes baseline
- `docs/release/supported-environments.md`:  supported runtime and toolchain matrix
- `docs/release/adoption-smoke-guide.md`: install, smoke, integrity verification, and troubleshooting guidance
- `docs/release/apply-fixes-scope.md`:  explicit apply-fixes scope, boundaries, and remediation classes
- `docs/release/prompt-invocation-templates.md`:  reusable contract and adapter invocation templates
- `docs/release/resilient-run-patterns.md`:  resilient scanner retry/backoff, policy gates, baseline-diff CLI patterns, and triage workflow checklists for CI handoff
- `docs/examples/ci/github-actions-wcag-ci-sample.yml`:  GitHub Actions sample with artifact retention and SARIF PR annotation
- `docs/release/real-scanner-ci-lane.md`:  formal `libro-agent-wcag-real-scanner` PR gate, evidence artifact conventions, and triage handoff contract
- `docs/release/baseline-governance.md`:  baseline debt governance, waiver lifecycle, and provenance verification
- `docs/release/advanced-ci-gates.md`:  risk calibration, replay verification, and scanner stability gate guidance
- `docs/policy-bundles/*.json`:  reusable policy-bundle templates (`strict-web-app`, `legacy-content`, `marketing-site`) for multi-repo adoption
- Policy bundle governance: `bundle_version`, `bundle_hash`, and `updated_at` are lock metadata fields; validate drift via `python scripts/validate_skill.py skills/libro-agent-wcag --validate-policy-bundles` before merging policy changes.
- `docs/archive/decisions/release-packaging-extras-placement.md`:  archived decision record for extras placement
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

\r\n
