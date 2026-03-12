# Skill Completion TODO

This checklist tracks the remaining work needed to make `libro-agent-wcag` more complete as a production-grade accessibility skill.

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
- [ ] Add React-specific fixtures
- [ ] Add Vue-specific fixtures
- [ ] Add Next.js-specific fixtures
- [ ] Add snapshot baselines for each new fixture family

## M9 Real Scanner Integration

- [x] Expand the real scanner integration matrix to cover more fixtures
- [x] Add WCAG version-specific real scanner baselines
- [x] Add apply-fixes before/after scanner comparison tests
- [x] Add real scanner regression snapshot coverage
- [x] Add conditional CI path for real scanner runs when environment prerequisites are available

## M10 Framework-Aware Remediation

- [ ] Add React JSX rewrite helpers
- [ ] Add Vue template rewrite helpers
- [ ] Add Next.js layout and language rewrite helpers
- [ ] Upgrade framework hints into framework-aware remediation strategies
- [ ] Add framework-specific auto-fix tests
- [ ] Add framework-specific snapshot baselines

## M11 Adapter Maturity

- [x] Add adapter-specific failure recovery transcripts
- [x] Add adapter-specific first-run output examples
- [x] Add adapter-specific end-to-end output snapshots
- [x] Add adapter-specific downgrade and escalation examples
- [x] Add adapter-specific smoke coverage for new remediation lifecycle fields

## M12 Quality Gates

- [ ] Add more idempotency tests for newly supported auto-fix rules
- [ ] Add regression tests for mixed auto-fix plus manual-review reports
- [ ] Add diff artifact validation tests for each rewrite family
- [ ] Add negative tests to ensure unsupported rules do not mutate files
- [ ] Add stability tests for repeated normalize plus apply-fixes runs

## Notes

- Safe auto-fix should remain limited to low-risk deterministic rewrites.
- Assisted remediation should preserve canonical report semantics and clearly signal remaining manual work.
- Framework-aware remediation should only be added once fixture coverage and regression safety are strong enough.


