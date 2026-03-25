# Release Playbook

Use this playbook as the primary release-readiness document for `libro-wcag`.

## Packaging Readiness

- Confirm `README.md` install and usage sections reflect current repo behavior.
- Confirm adapter prompt templates and usage examples are synchronized across supported agents.
- Confirm `scripts/install-agent.py`, wrapper scripts, and uninstall flow remain aligned.
- Confirm the release tag `vX.Y.Z` is the single version source for this publish.
- Run `python scripts/apply-release-version.py --version X.Y.Z` when staging a local dry run from a tag candidate.
- Run `python scripts/package-release.py --output-dir dist/release --overwrite` from the repo root to stage versioned release assets.
- Confirm `skills/libro-wcag/agents/openai.yaml` and manifest references are valid.
- Confirm `pyproject.toml`, `package.json`, and `.claude-plugin/*.json` were all updated by the tag-derived version injection step.
- Confirm release automation sets `LIBRO_AGENTWCAG_SOURCE_REVISION`; if not set, verify the build runs from a git checkout where `HEAD` resolves cleanly.
- If release packaging needs a pinned timestamp, set `LIBRO_AGENTWCAG_BUILD_TIMESTAMP` as a UTC ISO-8601 value; invalid or missing required provenance must fail fast rather than writing partial metadata.
- Confirm release asset names match the documented contract:
  - `libro-wcag-<version>-<agent>.zip` for `codex`, `claude`, `gemini`, and `copilot`
  - `libro-wcag-<version>-all-in-one.zip`
  - `libro-wcag-<version>-release-manifest.json`
  - `libro-wcag-<version>-sha256sums.txt`
  - `latest-release.json`
- Confirm release bundles exclude `skills/libro-wcag/scripts/tests/`, `docs/testing/`, and `docs/archive/`.

## Validation Readiness

- Run unit and integration suite:
  - `python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"`
- Run skill structural validation:
  - `python scripts/validate_skill.py skills/libro-wcag --validate-policy-bundles`
- Verify `.github/workflows/libro-wcag-real-scanner.yml` still defines workflow/job name `libro-wcag-real-scanner`.
- Verify the required PR check name remains `libro-wcag-real-scanner`.
- Verify the real-scanner lane still targets `docs/testing/realistic-sample/mixed-findings.html`.
- Verify the real-scanner lane still retains artifacts for `14` days and uploads `wcag-report.sarif`.
- Run dependency-audit lane (`pip-audit --strict` and `npm audit --audit-level=high`) with archived logs.
- Capture and archive `--preflight-only` output, including `version_provenance`.
- Verify `artifact-manifest.json` is generated for the release candidate and includes checksums for machine and markdown outputs plus generator `product_version`, `source_revision`, and report schema metadata.
- Verify the release manifest enumerates every packaged bundle with a 64-character `sha256` and that `sha256sums.txt` covers the bundles plus the release manifest itself.
- Run the adoption smoke flow in `docs/release/adoption-smoke-guide.md`.
- Verify release notes and changelog entries match the tested behavior.

## Publish Readiness

- Confirm target version tag and release title are finalized.
- Confirm the Git tag `vX.Y.Z` is ready to become the single release version source.
- Confirm all blocking defects are closed or explicitly listed as known limitations.
- Confirm `.github/workflows/release.yml` still uses the documented validate -> package-release -> clean-release-smoke -> publish-release gate order.
- Confirm `.github/workflows/publish-npm.yml` is the workflow filename configured in npm trusted publishing for `librowcag-cli`.
- Confirm npm trusted publishing is configured for `librowcag-cli`; the publish workflow should not require a stored `NPM_TOKEN`.
- For significant remediation changes, attach baseline refresh evidence and approver context.
- Run baseline governance checks described in `docs/release/baseline-governance.md`.
- Run advanced CI gate reviews described in `docs/release/advanced-ci-gates.md`.
- For any policy preset or bundle change, attach policy-bundle drift evidence and reviewer sign-off before merge.
- Push `master` and create release artifacts or tags per project policy.
- Confirm GA/rollback references remain current:
  - `docs/release/ga-definition.md`
  - `docs/release/ga-release-workflow.md`
  - `docs/release/rollback-playbook.md`
  - `docs/release/release-note-template.md`
  - `docs/release/hotfix-release-note-template.md`

## Release Notes Workflow

1. Keep `CHANGELOG.md` as human-facing history, but do not use it to drive release version selection.
2. Let GitHub auto-generated release notes draft the release body from merged changes.
3. Review the generated notes before publishing and add any missing known limitations or operator guidance.
4. Use `docs/release/release-note-template.md` for standard release guidance and `docs/release/hotfix-release-note-template.md` for hotfix guidance.

## Post-Publish Verification

- Download the published assets from the GitHub Release page.
- Verify `libro-wcag-<version>-sha256sums.txt`.
- Run `install-latest.ps1` or `install-latest.sh`; successful bootstrap must automatically complete doctor verification.
- Run a first audit and then uninstall the skill.

## Quality Gate

A release is not publish-ready unless:

- the release tag is correct and immutable
- notes reflect behavior that is already merged and validated
- breaking or operator-impacting changes are explicitly called out
