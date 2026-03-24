# M20 Validation Rerun (2026-03-12)

This run re-validated post-M20 behavior for deterministic smoke and real-scanner lanes, with additional Windows runtime hardening.

## Completed TODO Items

- Marked `Current Execution Order` items as complete in `SKILL-TODO.md`.
- Added Windows `npx.cmd` fallback for scanner subprocess execution.
- Added robust subprocess decoding (`utf-8` with replacement) and `stderr/stdout` null guards.

## Commands Executed

- Deterministic smoke:
  - `python scripts/run-realistic-validation-smoke.py --agent codex`
- Real-scanner/manual comparison:
  - `python skills/libro-wcag/scripts/run_accessibility_audit.py --target <fixture> --execution-mode suggest-only|apply-fixes`
  - with `NPM_CONFIG_CACHE=.tmp-npm-cache`

## Evidence Artifacts

- `.tmp-test/m20-validation-batch3/tooling-check.json`
- `.tmp-test/m20-validation-batch3/deterministic-smoke.log`
- `.tmp-test/m20-validation-batch3/real-scanner-validation.log`
- `.tmp-test/m20-validation-batch3/real-scanner-apply-fixes-comparison.json`
- `.tmp-test/m20-validation-batch3/real-scanner-manual/*/command.log`

## Results Summary

- Deterministic smoke: passed.
- Real-scanner lane: executed but environment-constrained.
  - `@axe-core/cli` installation/execution failed with `EPERM spawn` in this sandboxed host.
  - `lighthouse` failed to start Chrome due access denied (`ECONNREFUSED` after launcher failure).
- Report pipeline remained stable and produced JSON/Markdown reports without runtime crashes.

## Environment Notes

- This validation now explicitly supports Windows command resolution where `subprocess` cannot execute bare `npx`.
- For full real-scanner parity, run in an environment with:
  - npm install/exec permissions
  - Chrome launch permissions for Lighthouse

## Preflight Snapshot

- Command:
- `python skills/libro-wcag/scripts/run_accessibility_audit.py --target docs/testing/realistic-sample/mixed-findings.html --preflight-only --output-dir .tmp-test/m20-validation-batch3/preflight-only`
- Result:
  - `npx`: ok (`npx.cmd --version`)
  - `lighthouse`: ok (`npx.cmd --no-install lighthouse --version`)
  - `@axe-core/cli`: missing in no-install mode (must be pre-installed in host image)
