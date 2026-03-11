# Scenario and System Test Assets

This file defines scenario, system, and end-to-end coverage assets for the repo.

## System Test

- Validate the repo as a whole by running:
  - unit test discovery
  - skill validation
  - install -> doctor -> normalize report -> uninstall flow
- Confirm all steps succeed from the repo root.

## End-to-End Test

- Install the skill to a temporary destination.
- Run `normalize_report.py` or `run_accessibility_audit.py` against a sample HTML target.
- Verify the generated JSON and Markdown outputs.
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
- Confirm the report marks intent but still reports `files_modified=false` in the core workflow.

## Decision Table

| task_mode | execution_mode | target state | expected behavior |
| --- | --- | --- | --- |
| create | audit-only | draft/no scan | guidance or manual review only |
| create | suggest-only | draft/no scan | guidance plus suggested fixes |
| create | apply-fixes | draft/no scan | allow agent rewrite intent, but core workflow still reports no file modification |
| modify | audit-only | existing target | findings only |
| modify | suggest-only | existing target | findings plus planned fixes |
| modify | apply-fixes | existing target | findings plus fix intent for agent/adapter |

## State Transition Reference

- `open` -> `planned` when a finding is identified and a remediation is proposed.
- `open` -> `needs-review` when a scanner fails or mapping requires manual review.
- `planned` -> `implemented` or `verified` is reserved for future agent-side rewrite verification.
