# Replay Verification Lane

Use replay verification to confirm remediation stability across repeated runs and scanner variance.

## Purpose

- Re-run a target against current scanners and compare unresolved findings against a prior run directory.
- Emit deterministic replay artifacts for CI triage and release gating.
- Fail only when new high-severity regressions are deterministic.

## CLI

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target C:\repo\sample.html \
  --output-dir out-replay \
  --replay-verify-from out-baseline \
  --mock-axe-json axe.json \
  --skip-lighthouse
```

`--replay-verify-from` must point to a directory containing `wcag-report.json`.

## Artifacts

- `replay-summary.json`: per-signature replay result and gate decision.
- `replay-diff.md`: reviewer-friendly table of `resolved` / `unchanged` / `regressed` / `non-deterministic`.
- `run_meta.replay_verification`: summary pointer and gate metadata in `wcag-report.json`.

## Gate semantics

- Exit code `47` when replay introduces deterministic high-severity regressions.
- `non-deterministic` is used when scanner capabilities drift between source and current run.
- Scanner drift does not fail the replay gate; it requires manual review evidence.

## CI guidance

- Keep scanner availability consistent between source and replay runs where possible.
- Archive `replay-summary.json`, `replay-diff.md`, and `wcag-report.json` together for audit traceability.
- Add replay evidence to release checks when remediation logic or scanner versions change.
