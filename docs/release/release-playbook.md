# Release Playbook

Use this playbook as the primary release-readiness document for `libro-agent-wcag`.

## Packaging Readiness

- Confirm `README.md` install and usage sections reflect current repo behavior.
- Confirm adapter prompt templates and usage examples are synchronized across supported agents.
- Confirm `scripts/install-agent.py`, wrapper scripts, and uninstall flow remain aligned.
- Confirm `skills/libro-agent-wcag/agents/openai.yaml` and manifest references are valid.

## Validation Readiness

- Run unit and integration suite:
  - `python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"`
- Run skill structural validation:
  - `python scripts/validate_skill.py skills/libro-agent-wcag --validate-policy-bundles`
- Run dependency-audit lane (`pip-audit --strict` and `npm audit --audit-level=high`) with archived logs.
- Capture and archive `--preflight-only` output, including `version_provenance`.
- Verify `artifact-manifest.json` is generated for the release candidate and includes checksums for machine and markdown outputs.
- Run the adoption smoke flow in `docs/release/adoption-smoke-guide.md`.
- Verify release notes and changelog entries match the tested behavior.

## Publish Readiness

- Confirm target version tag and release title are finalized.
- Ensure `CHANGELOG.md` has a dated version section with highlights and known limits.
- Confirm all blocking defects are closed or explicitly listed as known limitations.
- For significant remediation changes, attach baseline refresh evidence and approver context.
- Run baseline governance checks described in `docs/release/baseline-governance.md`.
- Run advanced CI gate reviews described in `docs/release/advanced-ci-gates.md`.
- For any policy preset or bundle change, attach policy-bundle drift evidence and reviewer sign-off before merge.
- Push `master` and create release artifacts or tags per project policy.

## Release Notes Workflow

1. Create a new version header in `CHANGELOG.md` using `## [X.Y.Z] - YYYY-MM-DD`.
2. Move validated items from `[Unreleased]` into that version section.
3. Group notes under these buckets when applicable:
   - `Added`
   - `Changed`
   - `Fixed`
   - `Removed`
4. Include known limitations that affect adoption or behavior.
5. Cross-check release notes against merged PRs and test outcomes.
6. Link the changelog section in the release announcement.

## Quality Gate

A release is not publish-ready unless:

- the changelog has a dated version section
- notes reflect behavior that is already merged and validated
- breaking or operator-impacting changes are explicitly called out
