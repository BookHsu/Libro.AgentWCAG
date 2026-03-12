# Real-Scanner CI Lane Productization

This guide defines the reusable optional real-scanner lane for GitHub Actions and the artifact contract used for triage handoff.

## Reusable workflow template

Use [`.github/workflows/reusable-real-scanner-lane.yml`](../../.github/workflows/reusable-real-scanner-lane.yml) through `workflow_call`.

Key behaviors:

- Optional gate: lane only runs when caller passes `enabled: true`.
- Matrix lane modes: `live` and `fallback`.
- Clear skip semantics:
  - `live` runs only when both `@axe-core/cli` and `lighthouse` are available.
  - `fallback` always runs with mock fixtures to keep report contract checks deterministic.

## Evidence artifact conventions

Store lane evidence under one root (`out/real-scanner` by default):

- Raw scanner logs:
  - `raw/axe.version.log`
  - `raw/lighthouse.version.log`
  - `raw/scanner-unavailable.log` (only when real scanners are unavailable)
- Normalized summaries:
  - `normalized-summary.live.json`
  - `normalized-summary.fallback.json`
- Capability negotiation:
  - `capability-negotiation.json`

`capability-negotiation.json` is the handoff index artifact and must include:

- `lane_mode` (`live` or `fallback`)
- `scanners_available` (`true`/`false`)
- `matrix_modes` (`["live", "fallback"]`)
- `summary_artifacts`
- `raw_scanner_logs`

## Triage handoff references

When opening a triage item, include:

1. `capability-negotiation.json` path
2. Chosen summary artifact path (`normalized-summary.live.json` or `normalized-summary.fallback.json`)
3. Any raw scanner logs used for decision context

This keeps local `--summary-only` output expectations and CI lane outputs aligned for review.

## Sample caller workflow

See [`docs/release/github-actions-wcag-ci-sample.yml`](./github-actions-wcag-ci-sample.yml) for a full pipeline that calls the reusable lane.