# Baseline Debt Lifecycle Playbook

Use this playbook to manage baseline-driven accessibility debt with explicit approvals and release evidence.

## Debt states

- `new`: finding is unresolved in current report but not present in the prior baseline.
- `accepted`: finding remains unresolved across current and baseline reports, and has explicit owner/decision to defer.
- `retired`: finding existed unresolved in baseline but is no longer unresolved in current report.

## Approval checkpoints

1. `new` debt triage checkpoint
- Confirm severity, user impact, and owner in the current sprint/release board.
- Decide: remediate now, or explicitly convert to `accepted` with rationale and due date.
- Record reviewer and approval timestamp in the PR/release notes.

2. `accepted` debt continuation checkpoint
- Revalidate that defer rationale is still valid.
- Confirm mitigation/monitoring remains in place.
- Re-approve with updated target milestone when needed.

3. `retired` debt verification checkpoint
- Attach rerun evidence showing the finding is absent from unresolved set.
- Confirm related tests/scanner lane still pass and no equivalent regression was introduced.
- Mark retirement evidence in release notes or debt register.

## Operational runbook

1. Run baseline diff audit:

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target <target> \
  --output-dir out/debt-lifecycle \
  --baseline-report .ci/wcag-baseline.json \
  --summary-only
```

2. Read metadata:
- `run_meta.baseline_diff.debt_transitions.new|accepted|retired`
- finding-level `debt_state` tag in `findings[]`

3. Update baseline only after approvals:
- Refresh committed baseline JSON after triage/approval is complete.
- Keep prior baseline artifact in CI/release evidence for traceability.

4. Release gate expectation:
- Significant remediation releases must include baseline refresh evidence (report paths, reviewer, decision log).
- If baseline is unchanged, document why and who approved carry-forward debt.

