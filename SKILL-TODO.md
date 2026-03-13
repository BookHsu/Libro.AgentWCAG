# Skill Completion TODO

This checklist tracks the remaining work needed to make `libro-agent-wcag` more complete as a production-grade accessibility skill.

## Current Execution Order

1. [x] Complete `M32 Baseline Debt Waiver Expiry Automation` to prevent stale accepted debt from silently persisting.
2. [x] Complete `M33 Multi-Agent Install Manifest Integrity` to guarantee installed skill bundles remain adapter-correct and tamper-evident across agents.
3. [ ] Complete `M34 Policy Bundle Governance And Drift Detection` to keep shipped policy bundles audited, explainable, and release-gated against silent drift.

## M21 Post-M20 Validation Closure

- [x] Add Windows scanner command fallback so subprocess calls resolve `npx.cmd` when plain `npx` is not executable.
- [x] Harden scanner subprocess decoding and stderr/stdout handling to avoid runtime crashes on non-UTF-8 tool output.
- [x] Capture rerun evidence for deterministic smoke and real-scanner lanes, including environment blockers and outcomes.

## M5 Safe Auto-Fix Expansion

- [x] Add safe auto-fix support for `aria-valid-attr-value`
- [x] Add safe auto-fix support for `aria-required-attr`
- [x] Add safe auto-fix support for `aria-toggle-field-name`
- [x] Add safe auto-fix support for `aria-tooltip-name`
- [x] Add safe auto-fix support for `aria-progressbar-name`
- [x] Add safe auto-fix support for `aria-meter-name`
- [x] Add safe auto-fix support for `document-title`
- [x] Add safe auto-fix support for `list`
- [x] Add safe auto-fix support for `listitem`
- [x] Add safe auto-fix support for `table-fake-caption`
- [x] Add safe auto-fix support for `td-has-header`
- [x] Add safe auto-fix support for `th-has-data-cells`

## M6 Assisted Remediation

- [x] Add assisted remediation flow for `duplicate-id-aria`
- [x] Add assisted remediation flow for `heading-order`
- [x] Add assisted remediation flow for `region`
- [x] Add assisted remediation flow for `skip-link`
- [x] Add assisted remediation flow for `tabindex`
- [x] Add assisted remediation flow for `presentation-role-conflict`
- [x] Add assisted remediation flow for `nested-interactive`
- [x] Add verification rules for assisted remediation changes
- [x] Add downgrade semantics when assisted remediation cannot be safely applied

## M7 Report And Verification Model

- [x] Add `auto_fixed_count` to report summary
- [x] Add `manual_required_count` to report summary
- [x] Add `verification_evidence` fields to fixes or run metadata
- [x] Add `before_after_targets` evidence for modified findings
- [x] Add `rule_family` classification to findings and fixes
- [x] Add `risk_level` classification to findings and fixes
- [x] Add `downgrade_reason` reporting when fixes fall back to suggest-only or manual review
- [x] Add `fix_blockers` reporting for unsupported remediation cases

## M8 Fixture And Snapshot Corpus

- [x] Add ARIA family fixtures
- [x] Add form error fixtures
- [x] Add heading hierarchy fixtures
- [x] Add landmark and region fixtures
- [x] Add table semantics fixtures
- [x] Add keyboard and tabindex fixtures
- [x] Add WCAG 2.2 focus-related fixtures
- [x] Add `create` mode draft fixtures
- [x] Add React-specific fixtures
- [x] Add Vue-specific fixtures
- [x] Add Next.js-specific fixtures
- [x] Add snapshot baselines for each new fixture family

## M9 Real Scanner Integration

- [x] Expand the real scanner integration matrix to cover more fixtures
- [x] Add WCAG version-specific real scanner baselines
- [x] Add apply-fixes before/after scanner comparison tests
- [x] Add real scanner regression snapshot coverage
- [x] Add conditional CI path for real scanner runs when environment prerequisites are available

## M10 Framework-Aware Remediation

- [x] Add React JSX rewrite helpers
- [x] Add Vue template rewrite helpers
- [x] Add Next.js layout and language rewrite helpers
- [x] Upgrade framework hints into framework-aware remediation strategies
- [x] Add framework-specific auto-fix tests
- [x] Add framework-specific snapshot baselines
  - [x] Add React framework remediation snapshot baselines
  - [x] Add Vue framework remediation snapshot baselines
  - [x] Add Next.js framework remediation snapshot baselines

## M11 Adapter Maturity

- [x] Add adapter-specific failure recovery transcripts
- [x] Add adapter-specific first-run output examples
- [x] Add adapter-specific end-to-end output snapshots
- [x] Add adapter-specific downgrade and escalation examples
- [x] Add adapter-specific smoke coverage for new remediation lifecycle fields

## M12 Quality Gates

- [x] Add more idempotency tests for newly supported auto-fix rules
- [x] Add regression tests for mixed auto-fix plus manual-review reports
- [x] Add diff artifact validation tests for each rewrite family
- [x] Add negative tests to ensure unsupported rules do not mutate files
- [x] Add stability tests for repeated normalize plus apply-fixes runs

## M13 Framework Hint Snapshot Consistency

- [x] Align image-alt framework hints in fixture snapshots with framework-aware remediation wording
- [x] Refresh fixture report snapshots for missing-alt, React, Vue, and Next.js framework fixtures
- [x] Verify fixture integration and remediation strategy tests pass after snapshot updates

## M14 Release Readiness

- [x] Add a release checklist for packaging, validation, and publish readiness
- [x] Add a changelog or release-notes workflow for versioned updates
- [x] Document a supported-environment matrix for Python, Node, and scanner prerequisites
- [x] Add install-plus-doctor smoke instructions for first-run validation

## M15 Broader Real-World Validation

- [x] Add a realistic sample target under `docs/` or test fixtures that exercises mixed auto-fix plus manual-review findings
- [x] Add a scripted smoke scenario that runs install -> invoke -> audit against that realistic sample target
- [x] Add real-scanner assertions for the realistic sample target when `npx @axe-core/cli` and `lighthouse` are available
- [x] Capture representative end-to-end artifacts for that flow, including JSON report, Markdown report, and any diff outputs
- [x] Document known limitations, false-positive boundaries, and manual-review expectations discovered during realistic validation
- [x] Update `TESTING-PLAN.md` coverage assets if realistic validation introduces a new durable test lane

## M16 Apply-Fixes Productization

- [x] Audit `skills/libro-agent-wcag/scripts/auto_fix.py` and `run_accessibility_audit.py` behavior against README wording for `apply-fixes`
- [x] Define the supported `apply-fixes` scope explicitly by rule family, file type, and safety level
- [x] Close the highest-value gaps between safe rewrite support and documented `apply-fixes` capabilities
- [x] Add regression coverage for repeated `apply-fixes` runs on the same target and verify idempotent artifacts remain stable
- [x] Add regression coverage for mixed supported-plus-unsupported findings so unsupported rules never cause overreach
- [x] Clarify in docs which remediation classes remain intentionally `suggest-only` or assisted-only

## M17 Release Packaging Extras

- [x] Add a minimal demo package or walkthrough that can be used to verify the skill outside the test suite
- [x] Add reusable templates for common audit prompts or adapter invocation flows
- [x] Add issue templates or troubleshooting intake docs for installation failures and remediation mismatches
- [x] Decide whether release packaging extras belong inside this repo or in a companion examples repo

## M18 Apply-Fixes Safety And Operability

- [x] Add a preflight scanner/tooling check command that validates `npx`, `@axe-core/cli`, and `lighthouse` availability before runtime
- [x] Add a `--dry-run` mode to `run_accessibility_audit.py` for `apply-fixes` that emits projected diff metadata without mutating files
- [x] Add atomic write plus rollback safeguards for `apply_report_fixes` to prevent partial writes on interruption or I/O failure
- [x] Add rule-level mutation telemetry in `run_meta` (changed file path, rule id, and mutation count) for every successful auto-fix
- [x] Add regression fixtures for malformed HTML and edge encodings to verify regex-based rewrites do not corrupt source structure



## M19 Scanner Runtime Resilience

- [x] Add scanner preflight diagnostics output (`tools`, `versions`, `resolved command`) to `run_meta` for easier environment debugging
- [x] Add explicit error classification for scanner failures (`timeout`, `missing-tool`, `bad-target`, `runtime-error`) and expose them in report summary
- [x] Add partial-success contract tests to ensure single-scanner results stay actionable when `axe` or `lighthouse` individually fail
- [x] Add retry policy hooks for transient scanner failures (configurable attempts with bounded backoff)
- [x] Add CLI docs for resilient run patterns, including CI examples for `audit-only`, `suggest-only`, and `apply-fixes`

## M20 CI Reporting And Policy Control

- [x] Add a structured machine-readable export (`--report-format sarif|json`) so CI can annotate pull requests with precise finding locations
- [x] Add severity threshold gates (`--fail-on critical|serious|moderate`) that map normalized findings to deterministic process exit codes
- [x] Add rule include/ignore controls (`--include-rule`, `--ignore-rule`, optional config file) for project-level policy tuning without code changes
- [x] Add baseline diff mode to compare against a committed prior report and fail only on newly introduced accessibility debt
- [x] Add CI integration docs and sample workflows for GitHub Actions, including artifact retention and PR annotation examples

## M22 Developer Experience And Triage Precision

- [x] Add source line/column enrichment in normalized findings (best-effort mapping from scanner nodes) to improve PR annotation accuracy
- [x] Add `--max-findings` and deterministic sorting controls to keep large reports actionable in CI logs
- [x] Add compact summary mode (`--summary-only`) for quick gate checks while preserving full artifacts
- [x] Add regression coverage for policy gate behavior across mixed severity and baseline-diff combinations
- [x] Add docs for triage workflow (`new`, `persistent`, `resolved`) with sample review checklists and ownership handoff

## M23 Policy Ergonomics And Contract Stability

- [x] Add policy preset profiles (`strict`, `balanced`, `legacy`) that expand into deterministic `fail-on` and rule filter combinations
- [x] Add report schema versioning with JSON schema artifacts so CI consumers can validate compatibility before parsing
- [x] Add scanner capability negotiation output (which scanners/rules were available) and surface it in summary metadata
- [x] Add baseline signature customization hooks (target normalization and selector canonicalization) to reduce noisy churn across environments
- [x] Add regression tests that freeze CLI contract behavior for mixed options (`--summary-only`, `--report-format sarif`, baseline gating, and findings cap)
## M24 Policy Discoverability And Explainability

- [x] Add CLI preset discovery output (`--list-policy-presets`) so automation can inspect available policy profiles without requiring `--target`.
- [x] Add effective-policy explain mode (`--explain-policy`) that emits merged policy controls into `run_meta` and compact summary output.
- [x] Add regression coverage for preset discovery and explain-policy output contracts, plus README usage notes.
## M25 Policy Auditability And Governance

- [x] Add strict `--policy-config` key validation so unsupported keys fail fast with actionable errors.
- [x] Add effective-policy source provenance (`cli`, `policy-config`, `policy-preset`, default) for deterministic audit trails.
- [x] Add `--write-effective-policy` artifact export plus regression tests and README usage notes.


## M26 Policy Conflict Guardrails And Discoverability

- [x] Add machine-readable policy config key discovery output (`--list-policy-config-keys`) so automation can validate allowed config surface before generating files.
- [x] Add effective-policy overlap metadata for include/ignore rule collisions, including deterministic resolution semantics (`ignore-rules-win`) in `run_meta` and summary outputs.
- [x] Add strict overlap enforcement flag (`--strict-rule-overlap`) so ambiguous include/ignore policy combinations fail fast in CI.
## M27 Dependency And Supply-Chain Guardrails

- [x] Add dependency-lock and scanner-tool version capture guidance for Python and Node toolchains used by local and CI runs.
- [x] Add a reproducible dependency-audit lane (`pip-audit` and npm audit equivalent) with documented pass/fail policy and remediation workflow.
- [x] Add regression tests that verify preflight diagnostics include tool version provenance needed for supply-chain triage.

## M28 Real-Scanner CI Lane Productization

- [x] Add reusable workflow templates for optional real-scanner execution with clear skip semantics when scanners are unavailable.
- [x] Add CI evidence artifact conventions (raw scanner logs, normalized summary, capability negotiation) and doc references for triage handoff.
- [x] Add matrix tests that validate fallback behavior and messaging consistency between local runs and CI workflows.

## M29 Baseline Debt Lifecycle Governance

- [x] Add baseline maintenance playbook for `new`, `accepted`, and `retired` accessibility debt states with approval checkpoints.
- [x] Add CLI/report metadata support to tag findings with debt state transitions across baseline updates.
- [x] Add release checklist updates to require baseline refresh evidence before publishing significant remediation changes.
## M30 Policy Bundle Templates And Validation

- [x] Add a `docs/policy-bundles/` template set (`strict-web-app`, `legacy-content`, `marketing-site`) with deterministic include/ignore/fail-on defaults.
- [x] Add `--policy-bundle <name>` support that composes bundle defaults with existing CLI and `--policy-config` override precedence.
- [x] Add bundle validation and contract tests to ensure every shipped bundle resolves to a fully explainable effective policy and stable summary output.

## M31 Scanner Evidence Integrity And Provenance

- [x] Add run artifact manifest output (`artifact-manifest.json`) with file checksums, generator version, and timestamp metadata for every report run.
- [x] Add optional signature/hash-chain mode for baseline reports so CI can detect tampered or stale evidence before applying debt transitions.
- [x] Add docs and regression tests for provenance verification workflow in CI and release readiness checks.

## M32 Baseline Debt Waiver Expiry Automation

- [x] Add baseline debt waiver fields (`owner`, `approved_at`, `expires_at`, `reason`) with strict schema validation.
- [x] Add CLI warning/fail modes for expired waivers to enforce explicit debt renewal or retirement before release gating.
- [x] Add release checklist and triage workflow updates that require waiver-expiry review evidence for accepted debt states.

## M33 Multi-Agent Install Manifest Integrity

- [x] Add manifest integrity verification mode to `scripts/doctor-agent.py` that checks adapter entrypoint hashes and required companion files (`usage-example`, `failure-guide`, `e2e-example`).
- [x] Add installer/uninstaller regression tests for cross-agent matrix (`codex`, `claude`, `gemini`, `copilot`) including custom `--dest` layouts and reinstall idempotency.
- [x] Add release docs for post-install integrity verification workflow and failure remediation playbook for corrupted or partial installations.

## M34 Policy Bundle Governance And Drift Detection

- [ ] Add bundle lock metadata (`bundle_version`, `bundle_hash`, `updated_at`) to each `docs/policy-bundles/*.json` artifact and fail validation when metadata is missing or stale.
- [ ] Add `--validate-policy-bundles` CLI/CI check in `scripts/validate_skill.py` to verify bundle schema, deterministic key ordering, and compatibility with `--explain-policy` output.
- [ ] Add release checklist gate requiring policy-bundle drift evidence (baseline hash diff + reviewer sign-off) before merging policy preset or bundle changes.
## Notes

- Safe auto-fix should remain limited to low-risk deterministic rewrites.
- Assisted remediation should preserve canonical report semantics and clearly signal remaining manual work.
- Framework-aware remediation should only be added once fixture coverage and regression safety are strong enough.

