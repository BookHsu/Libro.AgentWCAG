# Skill Completion TODO

This checklist tracks the remaining work needed to make `libro-agent-wcag` more complete as a production-grade accessibility skill.

## Current Execution Order

1. Complete `M15 Broader Real-World Validation` to prove the current workflow on realistic targets, not only synthetic fixtures.
2. Complete `M16 Apply-Fixes Productization` to align actual rewrite behavior with the product promise in docs.
3. Start `M17 Release Packaging Extras` only after the validation and behavior scope are stable.

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

- [ ] Add a preflight scanner/tooling check command that validates `npx`, `@axe-core/cli`, and `lighthouse` availability before runtime
- [ ] Add a `--dry-run` mode to `run_accessibility_audit.py` for `apply-fixes` that emits projected diff metadata without mutating files
- [ ] Add atomic write plus rollback safeguards for `apply_report_fixes` to prevent partial writes on interruption or I/O failure
- [ ] Add rule-level mutation telemetry in `run_meta` (changed file path, rule id, and mutation count) for every successful auto-fix
- [ ] Add regression fixtures for malformed HTML and edge encodings to verify regex-based rewrites do not corrupt source structure

## Notes

- Safe auto-fix should remain limited to low-risk deterministic rewrites.
- Assisted remediation should preserve canonical report semantics and clearly signal remaining manual work.
- Framework-aware remediation should only be added once fixture coverage and regression safety are strong enough.
