# Changelog

All notable changes to this project are documented in this file.

This project follows a simple versioned release-notes practice inspired by Keep a Changelog.

## [Unreleased]

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

## Changelog Discipline

- Every published version must use `## [X.Y.Z] - YYYY-MM-DD`.
- Release notes must match behavior already validated by the release workflow.
- Breaking changes, known limitations, install/verify commands, and rollback-impacting issues must be called out explicitly.

## [0.1.0] - 2026-03-12

### Added

- Initial cross-agent WCAG skill contract and adapters for Codex, Claude, Gemini, and Copilot.
- Installer, doctor, and uninstall scripts with manifest-oriented install validation.
- Core workflow reporting, remediation strategy library, and framework-aware coverage baselines.
