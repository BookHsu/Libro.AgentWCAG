# Release Checklist

Use this checklist before publishing a new version of `libro-agent-wcag`.

## 1. Packaging readiness

- [ ] `README.md` install and usage sections reflect the current repo behavior.
- [ ] Adapter prompt templates and usage examples are synchronized across supported agents.
- [ ] `scripts/install-agent.py`, wrapper scripts, and uninstall flow are still aligned.
- [ ] `skills/libro-agent-wcag/agents/openai.yaml` and manifest references are valid.

## 2. Validation readiness

- [ ] Run unit and integration suite:
  - `python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"`
- [ ] Run skill structural validation:
  - `python scripts/validate_skill.py skills/libro-agent-wcag`
- [ ] Run dependency-audit lane (`pip-audit --strict` and `npm audit --audit-level=high`) with archived logs.
- [ ] Capture and archive `--preflight-only` output (including `version_provenance`) for release traceability.
- [ ] Verify `artifact-manifest.json` is generated for the release candidate and includes checksums for machine + markdown outputs.
- [ ] Run first-run smoke sequence from `docs/release/first-run-smoke.md`.
- [ ] Verify release notes and changelog entries match the tested behavior.

## 3. Publish readiness

- [ ] Confirm target version tag and release title are finalized.
- [ ] Ensure `CHANGELOG.md` has a dated version section with highlights and known limits.
- [ ] Confirm all blocking defects are closed or explicitly listed as known limitations.
- [ ] For significant remediation changes, attach baseline refresh evidence (`run_meta.baseline_diff.debt_transitions`, baseline artifact path, approver).
- [ ] Run baseline provenance verification mode (`--baseline-evidence-mode hash` or `hash-chain`) and archive verification evidence per `docs/release/provenance-verification.md`.
- [ ] Run waiver-expiry review (`--waiver-expiry-mode warn|fail`) and attach renewal/retirement evidence for accepted debt waivers.
- [ ] Push `master` and create release artifacts/tags per project policy.

