# Advanced CI Gates

Use these advanced gates to control release quality for scanner variance, replay stability, and noisy high-severity rules.

## Risk Calibration

Purpose: reduce triage noise from unstable high-severity rules using historical evidence.

CLI:

- `--risk-calibration-source <path>`
- `--risk-calibration-mode off|warn|strict`

Key behavior:

- `warn` continues with downgrade notes when evidence is missing, stale, or conflicting
- `strict` fails with exit code `46` when current high-severity rules are statistically unstable

Metadata is recorded under `run_meta.risk_calibration`.

## Replay Verification

Purpose: compare a current run against a prior run directory and fail only on deterministic high-severity regressions.

CLI:

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target C:\repo\sample.html \
  --output-dir out-replay \
  --replay-verify-from out-baseline \
  --mock-axe-json axe.json \
  --skip-lighthouse
```

Artifacts:

- `replay-summary.json`
- `replay-diff.md`
- `run_meta.replay_verification`

Gate semantics:

- exit code `47` on deterministic high-severity regressions
- scanner capability drift downgrades to manual review instead of failing

## Scanner Stability

Purpose: detect volatility drift across repeated runs before CI signal quality degrades.

CLI:

- `--stability-baseline <path>`
- `--stability-mode off|warn|fail`

Each run emits `scanner-stability.json` with points, variance rows, comparison output, approved bounds, and deterministic gate metadata.

Gate semantics:

- `warn` records downgrade notes
- `fail` exits with `48` on approved-bound breaches
- missing history or scanner capability changes downgrade instead of hard-failing

## Recommended CI Pattern

1. Keep baseline and calibration evidence directories under CI artifact retention.
2. Use `warn` modes on regular CI.
3. Use `strict` and `fail` modes on release candidates once evidence quality is stable.
4. Archive gate artifacts together with `wcag-report.json`, `wcag-report.md`, and `artifact-manifest.json`.
