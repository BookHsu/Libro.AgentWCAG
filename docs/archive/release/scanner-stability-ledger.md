# Scanner Stability Ledger

Use scanner stability tracking to detect volatility drift across repeated runs before it silently degrades CI signal quality.

## CLI options

- `--stability-baseline <path>`: baseline source for stability history. Supported inputs:
  - `scanner-stability.json`
  - prior `wcag-report.json` containing `run_meta.scanner_stability`
  - a directory containing either of those files
- `--stability-mode off|warn|fail`:
  - `off`: always emit `scanner-stability.json`, but skip gate evaluation.
  - `warn`: compare current variance with approved bounds and emit warning notes only.
  - `fail`: fail CI (`exit code 48`) when variance breaches approved bounds.

## Artifact contract

Each run emits `scanner-stability.json` with:

- `points[]`: historical run rows keyed by scanner/rule/target
- `variance_rows[]`: per-key min/max/latest variance window summary
- `comparison`: current-vs-previous delta, breach list, and scanner capability drift flags
- `approved_bounds`: allowed variance thresholds (`default_max_variance`, optional `per_signature` overrides)
- `gate`: deterministic status (`evaluated`, `failed`, `downgrade_reason`, `exit_code`)

## Stability window handling

- Window size is inherited from baseline artifact `window` when available.
- When missing or invalid, window defaults to `5`.
- Output points are always truncated to the active window to keep artifacts bounded and deterministic.

## Deterministic fallback behavior

When comparison cannot be safely enforced, the run downgrades and continues:

- `missing-history`: no usable baseline points.
- `scanner-capability-changed`: baseline scanner availability differs from current run.
- `mode-off`: stability gate intentionally disabled.

These reasons are recorded in `run_meta.scanner_stability.gate.downgrade_reason` and `run_meta.notes`.
