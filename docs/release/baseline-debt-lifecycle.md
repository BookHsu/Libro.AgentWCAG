# Baseline Debt Lifecycle Playbook

Use this playbook to manage baseline-driven accessibility debt with explicit approvals and release evidence.

## Debt states

- `new`: finding is unresolved in current report but not present in the prior baseline.
- `accepted`: finding remains unresolved across current and baseline reports, and has explicit owner/decision to defer.
- `retired`: finding existed unresolved in baseline but is no longer unresolved in current report.

## Debt waiver schema (`debt_waivers`)

When baseline debt is intentionally carried forward, store waiver metadata in baseline JSON:

```json
{
  "debt_waivers": [
    {
      "signature": "image-alt|img.hero",
      "owner": "a11y-owner",
      "approved_at": "2026-03-01T09:00:00Z",
      "expires_at": "2026-04-15T00:00:00Z",
      "reason": "Deferred until landing-page redesign"
    }
  ]
}
```

Schema is strict: every waiver entry must include exactly `signature`, `owner`, `approved_at`, `expires_at`, and `reason`.

## Approval checkpoints

1. `new` debt triage checkpoint
- Confirm severity, user impact, and owner in the current sprint/release board.
- Decide: remediate now, or explicitly convert to `accepted` with rationale and due date.
- Record reviewer and approval timestamp in the PR/release notes.

2. `accepted` debt continuation checkpoint
- Revalidate that defer rationale is still valid.
- Confirm mitigation/monitoring remains in place.
- Re-approve with updated target milestone when needed.
- Refresh waiver metadata (`approved_at`, `expires_at`, `reason`) before expiry.

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
  --waiver-expiry-mode warn \
  --summary-only
```

2. Read metadata:
- `run_meta.baseline_diff.debt_transitions.new|accepted|retired`
- finding-level `debt_state` tag in `findings[]`
- `run_meta.baseline_diff.waiver_review` and `run_meta.waiver_gate`

3. Enforce renewal on release pipelines:

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target <target> \
  --output-dir out/debt-release-gate \
  --baseline-report .ci/wcag-baseline.json \
  --waiver-expiry-mode fail \
  --fail-on serious \
  --fail-on-new-only
```

4. Update baseline only after approvals:
- Refresh committed baseline JSON after triage/approval is complete.
- Keep prior baseline artifact in CI/release evidence for traceability.

5. Release gate expectation:
- Significant remediation releases must include baseline refresh evidence (report paths, reviewer, decision log).
- Attach waiver-expiry review evidence (expired/valid/missing counts and renewal decisions) for accepted debt.
- If baseline is unchanged, document why and who approved carry-forward debt.

