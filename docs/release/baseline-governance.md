# Baseline Governance

Use this guide to manage baseline-driven accessibility debt and verify baseline evidence integrity before applying release gates.

## Debt States

- `new`: unresolved in current report but not present in prior baseline
- `accepted`: unresolved in both current and baseline reports with explicit defer approval
- `retired`: unresolved in baseline but no longer unresolved in current report

## Debt Waivers

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

Every waiver entry must include exactly `signature`, `owner`, `approved_at`, `expires_at`, and `reason`.

## Approval Checkpoints

1. Triage `new` debt and decide whether to remediate now or explicitly accept it.
2. Revalidate `accepted` debt before waiver expiry and refresh owner, date, and rationale when needed.
3. Attach rerun evidence when retiring debt and confirm no equivalent regression was introduced.

## Evidence Generation

Generate baseline evidence artifacts:

```powershell
python skills/libro-wcag/scripts/run_accessibility_audit.py `
  --target <target> `
  --output-dir out/baseline `
  --baseline-evidence-mode hash `
  --report-format json
```

Expected outputs:

- `wcag-report.json` with `run_meta.baseline_evidence`
- `artifact-manifest.json` with checksums and generator metadata

## Verification Before Diff Gating

```powershell
python skills/libro-wcag/scripts/run_accessibility_audit.py `
  --target <target> `
  --output-dir out/compare `
  --baseline-report out/baseline/wcag-report.json `
  --baseline-evidence-mode hash-chain `
  --fail-on moderate `
  --fail-on-new-only
```

Behavior:

- fail fast when baseline evidence hash does not match current file content
- extend lineage in `hash-chain` mode with parent and chain hashes

## Operational Runbook

1. Run baseline diff audit with `--waiver-expiry-mode warn`.
2. Read `run_meta.baseline_diff`, finding-level `debt_state`, and waiver review output.
3. Enforce renewal on release pipelines with `--waiver-expiry-mode fail`.
4. Refresh committed baseline JSON only after approvals are complete.

## Release Evidence

Archive these artifacts for release review:

- `artifact-manifest.json`
- `wcag-report.json` or `wcag-report.sarif`
- `wcag-report.md`
- `schemas/wcag-report-1.0.0.schema.json`

Recommended assertions:

- `artifact_count > 0`
- all manifest entries include 64-char `sha256`
- `run_meta.baseline_evidence.baseline_verification.verified = true` when `--baseline-report` is used
