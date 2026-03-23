# Changelog

All notable changes to this project are documented in this file.

This project follows a simple versioned release-notes practice inspired by Keep a Changelog.

## [Unreleased]

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
