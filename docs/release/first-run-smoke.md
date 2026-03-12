# Install + Doctor First-Run Smoke

Use this smoke flow to validate a clean first-run experience.

## Goal

Confirm that a user can install, verify, run, and remove the skill without manual repo-specific intervention.

## Steps

1. Install a target adapter (example: codex):
   - `python .\scripts\install-agent.py --agent codex --force`
2. Verify installation health:
   - `python .\scripts\doctor-agent.py --agent codex`
3. Run one audit command against a known sample target:
   - `python .\skills\libro-agent-wcag\scripts\run_accessibility_audit.py --target .\skills\libro-agent-wcag\scripts\tests\fixtures\missing-alt.html --mode suggest-only --format json`
4. Confirm output includes findings and canonical report fields.
5. Uninstall and re-check:
   - `python .\scripts\uninstall-agent.py --agent codex`
   - `python .\scripts\doctor-agent.py --agent codex`
6. Ensure uninstall state is reported as unhealthy/missing as expected.

## Pass criteria

- Install command succeeds with no missing manifest assets.
- Doctor command reports healthy right after install.
- Audit command executes and emits valid report output.
- Uninstall removes installed bundle and doctor reflects removal.
