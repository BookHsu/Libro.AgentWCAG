# Risk Calibration Workflow

Use risk calibration to reduce triage noise from unstable high-severity rules by scoring historical evidence from repeated fixture/baseline runs.

## CLI options

- `--risk-calibration-source <path>`: JSON evidence source (single report/artifact file or directory containing report JSON files).
- `--risk-calibration-mode off|warn|strict`:
  - `off`: disable calibration (default).
  - `warn`: compute signals and record downgrade notes if evidence is missing/stale/conflicting.
  - `strict`: fail CI (`exit code 46`) when currently triggered high-severity rules are statistically unstable.

## Run metadata contract

`run_meta.risk_calibration` includes:

- `mode`, `source_path`, `applied`, `downgrade_reason`
- `rules[]` with per-rule precision signals (`observations`, `actionable_count`, `high_severity_*`)
- `unstable_high_severity_rules[]`
- `gate.failed` and `gate.exit_code`

## Fallback behavior (deterministic)

When calibration cannot be applied, the run continues with downgraded messaging in `run_meta.notes`:

- `missing-evidence`: source missing or no usable evidence
- `stale-schema`: schema mismatch in calibration/report evidence
- `conflicting-rule-ids`: duplicate `rule_id` entries in calibration artifacts

## Recommended CI pattern

1. Keep a calibration evidence directory from repeated baseline/fixture runs.
2. Run with `--risk-calibration-mode warn` on regular CI lanes.
3. Enable `--risk-calibration-mode strict` on release lanes after evidence quality is stable.
