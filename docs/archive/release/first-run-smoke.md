# Install + Doctor First-Run Smoke

Use this smoke flow to validate a clean first-run experience.

## Goal

Confirm that a user can install, verify, run, and remove the skill without manual repo-specific intervention.

## Baseline smoke command

Run the scripted realistic validation flow:

- `python .\scripts\run-realistic-validation-smoke.py --agent codex`

The script executes:

1. `install-agent.py --agent codex --dest <temp> --force`
2. `doctor-agent.py --agent codex --dest <temp>`
3. `run_accessibility_audit.py --execution-mode apply-fixes --wcag-version 2.2` against `docs/testing/realistic-sample/mixed-findings.html`
   - Uses deterministic mock scanner payloads in `docs/testing/realistic-sample/scanner-fixtures/`
4. Captures representative artifacts in `docs/testing/realistic-sample/artifacts/`

## Artifacts captured

- `wcag-report.sample.json`
- `wcag-report.sample.md`
- `wcag-fixes.sample.diff`
- `wcag-fixed-report.sample.snapshot.json`
- `smoke-summary.json`

## Optional real-scanner extension

When `npx @axe-core/cli` and `lighthouse` are available, run real-scanner tests:

- `set LIBRO_RUN_REAL_SCANNERS=1`
- `python -m unittest skills.libro-wcag.scripts.tests.test_fixtures_and_integration.RealScannerIntegrationTests`

## Pass criteria

- Install command succeeds with no missing manifest assets.
- Doctor command reports healthy right after install.
- Audit command emits both JSON and Markdown reports.
- Apply-fixes output emits diff + snapshot artifacts.
- Smoke summary shows mixed remediation outcomes (`auto_fixed_count > 0` and `manual_required_count > 0`).
