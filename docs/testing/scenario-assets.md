# Scenario and System Test Assets

This file defines scenario, system, and end-to-end coverage assets for the repo.

## System Test

- Validate the repo as a whole by running:
  - unit test discovery
  - skill validation
  - install -> doctor -> audit -> artifact capture flow
- Confirm all steps succeed from the repo root.

## End-to-End Test

- Install the skill to a temporary destination.
- Run `run_accessibility_audit.py` against `docs/testing/realistic-sample/mixed-findings.html`.
- Verify the generated JSON, Markdown, diff, and snapshot outputs.
- Run `doctor-agent.py` before and after uninstall.

## Scenario Test

### Scenario A: Create Mode Guidance
- Use `task_mode=create` with no real scanner output.
- Confirm the report avoids fake scan claims and keeps guidance/manual-review semantics.

### Scenario B: Modify Mode Audit
- Use `task_mode=modify` with scanner findings.
- Confirm the report includes findings, fixes, and citations.

### Scenario C: Apply-Fixes Intent
- Use `execution_mode=apply-fixes`.
- Confirm the report marks intent and applies only safe deterministic rewrites.

### Scenario D: Realistic Mixed Validation Lane
- Run `python .\scripts\run-realistic-validation-smoke.py --agent codex`.
- Confirm `docs/testing/realistic-sample/artifacts/smoke-summary.json` reports both:
  - `auto_fixed_count > 0`
  - `manual_required_count > 0`
- Confirm artifacts include JSON, Markdown, unified diff, and fixed-report snapshot outputs.

## Decision Table

| task_mode | execution_mode | target state | expected behavior |
| --- | --- | --- | --- |
| create | audit-only | draft/no scan | guidance or manual review only |
| create | suggest-only | draft/no scan | guidance plus suggested fixes |
| create | apply-fixes | draft/no scan | allow agent rewrite intent while preserving manual-review boundaries |
| modify | audit-only | existing target | findings only |
| modify | suggest-only | existing target | findings plus planned fixes |
| modify | apply-fixes | existing target | findings plus safe automatic rewrites and explicit unsupported boundaries |

## State Transition Reference

- `open` -> `planned` when a finding is identified and a remediation is proposed.
- `open` -> `needs-review` when a scanner fails or mapping requires manual review.
- `planned` -> `implemented` when safe deterministic rewrites are applied.
- `implemented` -> `verified` remains reserved for explicit post-fix verification gates.
