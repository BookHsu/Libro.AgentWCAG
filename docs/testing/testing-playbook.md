# Testing Playbook

This playbook consolidates the repository's manual, scenario, system, end-to-end, and non-functional testing guidance.

## Manual Testing Checklists

### Acceptance Test / UAT

- Install `libro-wcag` for the target agent.
- Invoke the skill on one existing page in `audit-only`, `suggest-only`, and `apply-fixes` intent.
- Confirm the result includes Markdown and JSON outputs with aligned issue IDs.
- Confirm the result explains whether files were modified.
- Confirm citations point to `w3.org`.

### Alpha Test

- Run the skill internally on at least one local HTML file and one remote URL.
- Record any missing contract fields, broken prompts, or malformed reports.
- Verify the doctor command reports the installation as healthy before testing.

### Beta Test

- Ask one external user to install via the documented installer path.
- Have them verify install, invocation, and uninstall without local repo knowledge.
- Record friction in installation, prompt loading, or report interpretation.

### Usability Test

- Validate the README gives enough guidance for first install without oral handoff.
- Validate each agent's first-use guidance is sufficient to invoke the skill correctly.
- Confirm the testing plan and runtime requirements are discoverable.

### Exploratory Testing

- Run the skill on pages with mixed issues: missing alt text, labels, link names, and language attributes.
- Try unusual targets: local files, invalid schemes, and partially broken installs.
- Record any confusing output wording or duplicated findings.

## Scenario, System, and End-to-End Assets

### System Test

- Validate the repo as a whole by running:
  - unit test discovery
  - skill validation
  - install -> doctor -> audit -> artifact capture flow
- Confirm all steps succeed from the repo root.

### End-to-End Test

- Install the skill to a temporary destination.
- Run `run_accessibility_audit.py` against `docs/testing/realistic-sample/mixed-findings.html`.
- Verify the generated JSON, Markdown, diff, and snapshot outputs.
- Run `doctor-agent.py` before and after uninstall.

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

## Non-Functional and Reliability Checks

### Compatibility Test

- Verify Python installer behavior for `codex`, `claude`, `gemini`, `copilot`, and `all`.
- Verify PowerShell and POSIX wrapper scripts point to the Python installer.

### Performance Test

- Run normalization on a synthetic report with many findings.
- Confirm completion stays within an acceptable local threshold.

### Stress Test

- Run normalization with repeated or large finding sets.
- Confirm report generation still succeeds without malformed output.

### Endurance / Soak Test

- Execute repeated normalization loops and repeated install/doctor/uninstall cycles.
- Confirm no progressive failures occur.

### Volume / Capacity Test

- Generate a report with a larger set of findings and citations.
- Confirm JSON and Markdown files are written correctly.

### Scalability Test

- Compare small and larger synthetic inputs.
- Confirm growth remains operationally linear enough for local CLI usage.

### Security Test

- Verify invalid target schemes are rejected.
- Verify nonexistent local files are rejected before scanner execution.
- Verify install destinations are not silently overwritten without `--force`.

### Vulnerability Scan

- Automated baseline: `test_repo_invocation.py` runs `python -m pip check`.
- Keep dependency and script review before release.
- Current minimum command set:
  - `python -m pip check`
  - `python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"`
- If additional dependencies are added later, attach a dedicated dependency scanner.

### Recovery Test

- Break an installed bundle by removing the adapter prompt.
- Confirm `doctor-agent.py` reports the installation as unhealthy.
- Reinstall with `--force` and confirm health returns.

### Interrupt Test

- Simulate partial or broken installations by removing expected files.
- Confirm doctor and reinstall flows can detect and recover from the interruption.

### Concurrency Test

- Install to independent destinations in parallel.
- Confirm both installations complete successfully and generate valid manifests.
