# Changelog

All notable changes to this project are documented in this file.

This project follows a simple versioned release-notes practice inspired by Keep a Changelog.

## [Unreleased]

### Fixed

- Scanner runtime now reports malformed axe/lighthouse JSON artifacts with file path and line/column context instead of crashing.
- Workflow JSON loading now raises descriptive `ValueError` messages for malformed local report inputs.
- `run-realistic-validation-smoke.py` now validates `wcag-report.json` existence and JSON shape before building the smoke summary.
- `scripts/validate_skill.py` now rejects missing adapter directories/docs, missing `scripts/`, and incomplete `SKILL.md` frontmatter.
- Release bundles now include `CHANGELOG.md` for downstream release-note traceability.
- Scanner command execution now distinguishes permission-denied failures from transient process-launch `OSError` conditions, improving retry classification.
- Lighthouse debug-port readiness now uses the remaining global timeout instead of a fixed 0.5 second socket window.

### Added

- Regression coverage for malformed scanner JSON artifacts, malformed workflow inputs, and missing smoke-report artifacts.
- Regression coverage for skill validation contract checks and release-bundle changelog contents.
- Regression coverage for scanner launch error classification and debug-port timeout handling.

## [1.2.1] - 2026-03-25

### Fixed

- The published `librowcag-cli` npm package now includes package provenance fallback so `libro install <agent>` works without `.git` or `pyproject.toml`.

### Added

- Regression coverage for npm-style packaged installs outside a git checkout.

## [1.1.2] - 2026-03-25

### Changed

- Release workflow now keeps npm provenance generation in GitHub Actions only.
- `package.json` no longer forces provenance during local manual publish.
- Release docs and examples now point to the `1.1.2` release line.

### Install / Verify

- Install the npm CLI with `npm install -g librowcag-cli`.
- Local manual publish should use `npm publish --access public`.
- GitHub Actions release publish should use trusted publishing with provenance.

### Known Limitations

- npm trusted publishing still depends on the release tag pointing at a commit that already contains the final release workflow.

## [1.1.0] - 2026-03-25

### Added

- Unified `libro` CLI entrypoints for install, verification, and removal across supported agents.
- npm-publishable global CLI package `librowcag-cli`.
- Claude plugin marketplace manifests and workspace skill discovery support.
- Gemini workspace skill support, MCP server scaffolding, and reusable install workflow examples.

### Changed

- README and README.en now focus on project purpose, install, usage, and license only.
- Installation docs now prioritize Claude Marketplace, npm CLI, and clone-plus-CLI paths.
- Usage docs now show minimal execution-mode examples for `audit-only`, `suggest-only`, and `apply-fixes`.

### Install / Verify

- Install the npm CLI with `npm install -g librowcag-cli`.
- Install a target agent with `libro install claude`.
- Verify installation with `libro doctor claude`.

### Known Limitations

- Publishing `librowcag-cli` to npm still depends on the publisher account satisfying npm 2FA policy.

## [1.0.2] - 2026-03-23

### Added

- Chinese default repository homepage with a preserved English companion file in `README.en.md`.
- Repo admin setup guide for release asset publishing and PR bypass configuration in `docs/release/repo-admin-setup.md`.

### Changed

- Release workflow now also reacts to GitHub Release `published` events so manually published releases can still receive packaged zip assets.
- README default language is now Traditional Chinese, with quick-install guidance for published release assets.
- GA release workflow docs now describe the GitHub UI publish path alongside tag-push and manual dispatch flows.

### Install / Verify

- Bootstrap install from published release assets with `pwsh -File .\scripts\install-latest.ps1 -ReleaseBase https://github.com/<owner>/<repo>/releases/download/v1.0.2 -Agent codex`.

### Checksum Verification

- Verify `libro-agent-wcag-1.0.2-sha256sums.txt` before installing any release bundle.
- Confirm the selected bundle hash matches both the checksum file and `libro-agent-wcag-1.0.2-release-manifest.json`.

### Known Limitations

- Owner/admin bypass remains a GitHub repository setting and is not enforced by repository files alone.

## [1.0.1] - 2026-03-23

### Added

- Release-readiness docs for checklist, environment matrix, and first-run smoke guidance.
- Baseline diff policy gate (`--baseline-report`, `--fail-on-new-only`) in `run_accessibility_audit.py`.
- GitHub Actions WCAG CI sample with SARIF PR annotation and artifact retention guidance.
- Scanner stability ledger artifact (`scanner-stability.json`) with per-scanner/rule/target variance tracking and approved-bound comparison modes (`--stability-baseline`, `--stability-mode`).
- Release documentation for scanner stability governance in `docs/release/scanner-stability-ledger.md`.
- Formal release workflow contract in `.github/workflows/release.yml` with validate -> package -> clean smoke -> publish gates.
- GA definition, GA release workflow, and rollback/hotfix playbooks for non-author operators.

### Changed

- README now links release-readiness references and M20 CI policy/baseline examples.
- Release checklist now requires scanner stability evidence review for volatility gates and capability drift downgrades.
- Changelog discipline now requires release notes to match the tested release workflow, GA blocker policy, and rollback communication rules.

### Install / Verify

- Package release assets with `python .\scripts\package-release.py --output-dir .\dist\release --overwrite`.
- Bootstrap install from release assets with `pwsh -File .\scripts\install-latest.ps1 -ReleaseBase .\dist\release -Agent codex`.
- Post-install verification is part of bootstrap and can also be run explicitly with `python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity`.

### Checksum Verification

- Verify `libro-agent-wcag-1.0.1-sha256sums.txt` before installing any release bundle.
- Confirm the selected bundle hash matches both the checksum file and `libro-agent-wcag-1.0.1-release-manifest.json`.

### Known Limitations

- GitHub Release publish flow is contract-tested in-repo; final end-to-end publish still depends on a real tag push in GitHub Actions.

## Changelog Discipline

- Every published version must use `## [X.Y.Z] - YYYY-MM-DD`.
- Release notes must match behavior already validated by the release workflow.
- Breaking changes, known limitations, install/verify commands, and rollback-impacting issues must be called out explicitly.

## [0.1.0] - 2026-03-12

### Added

- Initial cross-agent WCAG skill contract and adapters for Codex, Claude, Gemini, and Copilot.
- Installer, doctor, and uninstall scripts with manifest-oriented install validation.
- Core workflow reporting, remediation strategy library, and framework-aware coverage baselines.
