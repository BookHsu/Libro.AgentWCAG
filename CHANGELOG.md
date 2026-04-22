# Changelog

All notable changes to this project are documented in this file.

This project follows a simple versioned release-notes practice inspired by Keep a Changelog.

## [Unreleased]

### Added

- `README.en.md`, `docs/README.en.md`, `docs/testing/testing-playbook.en.md`, and `docs/testing/test-matrix.en.md` now provide English companion files for the primary zh-TW public documentation set.
- `run_accessibility_audit.py --print-examples` and `libro audit|scan|report --print-examples` now print copy-paste examples for the most common workflows.
- `libro report --no-color` now provides an ANSI-free, emoji-free terminal mode suitable for plain Windows consoles and CI logs.
- `run_accessibility_audit.py --artifacts minimal` now keeps core reports while skipping optional sidecar artifacts such as `debt-trend.json` and `scanner-stability.json`.
- `libro scan` now de-duplicates repeated targets, creates collision-resistant per-target output directories, and writes `scan-output.log` when a target emits stdout/stderr.
- `libro report` now auto-falls back to plain ASCII terminal output when stdout cannot encode Unicode safely.
- `docs/archive/decisions/markdown-cleanup-20260329.md` now records the markdown convergence decisions and the first-pass GitHub Pages source set after temporary planning files were removed.
- `docs/testing/test-matrix.md` now holds the detailed coverage matrix that previously lived at the repo root in `TESTING-PLAN.md`.
- `libro audit` subcommand forwards all arguments to `run_accessibility_audit.py`, providing a short CLI entry point for WCAG audits (e.g. `libro audit https://example.com`).
- `libro doctor --check-scanners` verifies scanner toolchain availability (Node.js, npx, axe, lighthouse) alongside the existing skill file checks.
- README.md and README.en.md now include a "CLI Quick Start" section with copy-paste CLI examples for audit, suggest, apply-fixes, and preflight checks.
- `references/cli-reference.md` provides a complete CLI option reference covering policy bundles, baselines, SARIF output, failure gates, and scanner control.
- All four adapter prompt templates now cross-reference `cli-reference.md` for advanced CLI options.
- `remediation_library.py` now includes `auto_fix_reason` on every rule where `auto_fix_supported` is `False`, explaining why automatic remediation is not feasible (e.g. color-contrast: "Color choices require design intent").
- `test_schema_validation.py` validates generated reports against the JSON Schema using `jsonschema`, catching schema/code mismatches at test time.
- `jsonschema>=4.20` is now an optional test dependency in `pyproject.toml`.
- `mcp-server/requirements.lock` provides hash-pinned dependency versions for production deployments.
- All four adapter `usage-example.md` files now include an "Advanced: Baseline & Risk Calibration" section with `--risk-calibration-source` and `--stability-baseline` CLI examples.
- `test_repo_contracts.py` now validates MCP tool parameter defaults match SKILL.md contract defaults using AST-based source parsing.
- `WcagUrlSlugTests` validates all `WCAG_UNDERSTANDING_PATHS` slugs are well-formed, unique, and produce correct URLs for WCAG 2.0/2.1/2.2, with optional HTTP HEAD reachability check gated behind `LIBRO_RUN_URL_VALIDATION=1`.
- `vue-sfc-complex.vue` fixture and integration test verify that Vue SFC auto-fix applies button-name, link-name, and image-alt fixes inside `<template>` without corrupting `<script>` content.
- `generate_snapshots.py` tool and 15 new `.report.json` + `.report.md` snapshot baselines provide regression detection for all HTML fixture files.
- Document governance audit (AA1) classifies all formal documents with keep/merge/remove decisions; 20 documents confirmed as authoritative, 11 archive documents identified for removal.
- `README.md` and `README.en.md` now document MCP read-only limitation and `requirements.lock` availability for production deployments.
- `supported-environments.md` now includes MCP server as a supported environment with hash-pinned dependency lock file reference.
- Removed 11 superseded `docs/archive/release/` files; updated `docs/README.md` index with 7 previously unlisted release docs.
- Verified all 3 bilingual document pairs (README, apply-fixes-scope, real-scanner-ci-lane) follow the zh-TW `.md` + English `.en.md` convention with aligned structure.

### Fixed

- `run_accessibility_audit.py` no longer rewrites the primary report outputs multiple times during a single run; the main report artifacts are now written once after the final report shape is assembled.
- `libro.ps1` and `libro.sh` now advertise `scan` and `report` alongside `install`, `doctor`, `remove`, and `audit`, so wrapper help matches the actual unified CLI surface.
- Removed redundant `CLAUDE.md`, which only repeated the repository-wide `AGENTS.md` instruction without adding any Claude-specific contract or workflow behavior.
- Removed the completed root backlog file `SKILL-TODO.md` after its remaining cleanup decisions were captured elsewhere, and moved `TESTING-PLAN.md` into `docs/testing/test-matrix.md` so root docs stay focused on durable entry points.
- Removed the temporary `docs/automations/` planning directory after converging its durable decisions into formal docs, tests, changelog, and archive notes.
- `_report_to_sarif()` now generates RFC 3986 compliant `file:///` URIs for local targets on Windows, instead of bare `C:/path` style strings that some SARIF consumers cannot parse.
- SARIF output now includes `helpUri` (W3C Understanding URL), `help` text, `ruleIndex`, and `invocations` object per SARIF 2.1.0 spec, improving tool interoperability.
- SARIF results now include `contextRegion` (±1 line around the finding) and `snippet` (CSS selector) for better IDE and analysis tool integration.

### Changed

- `run_accessibility_audit.py` now routes policy resolution, runtime validation, preflight payload construction, scanner execution, and auxiliary artifact emission through focused internal helpers, reducing `main()` duplication while preserving CLI behavior.
- `scripts/libro.py` now routes scan execution, progress reporting, report runtime loading, and aggregate output dispatch through focused helpers while keeping the public CLI surface unchanged.
- `report_renderers.py` and `report_artifacts.py` now normalize single-report context and baseline diff aliases consistently, so compact summaries and aggregate-oriented renderers share the same fallback semantics.
- `release.yml` `clean-release-smoke` now uses a matrix strategy to smoke-test all four agents (codex, claude, gemini, copilot) in parallel instead of only codex.
- `run_accessibility_audit.py` now runs axe and Lighthouse scanners in parallel using `concurrent.futures.ThreadPoolExecutor` when both are active, reducing total audit wall-clock time.
- `run_accessibility_audit.py` now gracefully handles `task_mode=create` with non-existent targets by skipping scanners and producing guidance-only manual-review findings instead of crashing.
- `validate_skill.py` now warns when policy bundle `include_rules` or `ignore_rules` contain rule IDs not found in the scanner/remediation registry.
- `scripts/install-agent.py` now backs up existing installations before `--force` replacement and automatically rolls back on failure, preventing incomplete installation states.
- `scripts/install-agent.py` now reads the installed version from the existing manifest and warns on stderr when a `--force` install would downgrade.
- `core-spec.md` now includes a Schema Versioning Policy (§5) documenting the semver rules, compatibility contract, and upgrade checklist for the report schema.
- `core-spec.md` now includes a Language Separation section (§6) documenting that adapter prompt directives stay in English while only report output respects the `output_language` field.
- `SKILL.md` Adapter Rules now explicitly states that prompt directives must not be translated based on `output_language`.
- `SKILL.md` and `core-spec.md` now document `output_language` as `en | zh-TW` with explicit fallback-to-`en` behavior for unsupported BCP-47 values, matching the actual runtime capability.

### Security

- MCP server `audit_page.py` now validates local file targets with `Path.resolve()` + `relative_to(REPO_ROOT)` to prevent path traversal attacks. URL targets are passed through unchanged.

### Fixed

- Report JSON Schema now allows `null` for `source_line` and `source_column` in findings, matching the actual output when line/column information is unavailable.
- `libro-wcag-real-scanner.yml` now uses `--report-format sarif` CLI flag instead of importing the private `_report_to_sarif` function, removing the unstable internal API dependency.
- `auto_fix.py` now routes button/link/ARIA widget accessible-name remediation through a shared helper and records attribute-based guesses in diff descriptions as `(guessed from: <attr>)` for reviewer traceability.
- `wcag_workflow.py` now derives `AXE_RULE_TO_SC` and `LIGHTHOUSE_RULE_TO_SC` from a single `SCANNER_RULE_TO_SC` table so shared WCAG mappings stay aligned while preserving scanner-specific overrides.
- `scripts/uninstall-agent.py` now converts filesystem removal failures into clear CLI error messages instead of surfacing raw tracebacks for permission or path-type problems.
- Markdown report summaries now include a visible `⚠️` scanner-coverage warning line whenever axe or Lighthouse fails, so partial reports are easier to notice.
- `README.md` and `README.en.md` now mark the Claude Marketplace install commands as coming soon pending marketplace availability.
- Reusable `install-skill.yml` now checks out `${{ github.repository }}` instead of a hard-coded upstream repo, so forked repositories can call the workflow directly.
- Reusable `install-skill.yml` now exposes an `installation_valid` output even when `doctor-agent.py` fails, letting workflow callers branch on verification results before the job exits.
- `publish-npm.yml` now runs `npm pack --dry-run` before the real pack/publish steps to catch packaging allowlist mistakes earlier.
- The real-scanner CI lane guide now includes the branch-protection and artifact-retention wording expected by the contract tests.
- WCAG report schema now explicitly validates core finding/fix contract fields such as fixability, verification status, confidence, SC mappings, remediation priority, framework hints, and structured summary sections.
- W3C Understanding citations now cover all 87 WCAG 2.x success criteria slugs and generate the correct `WCAG20` / `WCAG21` / `WCAG22` URL path for the selected standard version.
- Scanner runtime now reports malformed axe/lighthouse JSON artifacts with file path and line/column context instead of crashing.
- Workflow JSON loading now raises descriptive `ValueError` messages for malformed local report inputs.
- `run-realistic-validation-smoke.py` now validates `wcag-report.json` existence and JSON shape before building the smoke summary.
- `scripts/validate_skill.py` now rejects missing adapter directories/docs, missing `scripts/`, and incomplete `SKILL.md` frontmatter.
- Release bundles now include `CHANGELOG.md` for downstream release-note traceability.
- `scripts/package-release.py` now fails fast when required release inputs are missing and excludes temporary skill files such as `.tmp`, `.bak`, and editor backup files from shipped bundles.
- Scanner command execution now distinguishes permission-denied failures from transient process-launch `OSError` conditions, improving retry classification.
- Lighthouse debug-port readiness now uses the remaining global timeout instead of a fixed 0.5 second socket window.
- Schema artifact staging now rejects mismatched `report_schema.version.const` values instead of silently recording the wrong schema version in generated reports.
- Browser discovery now checks standard macOS Chrome and Edge app bundle paths before giving up.
- `rewrite_helpers.py` now uses `re.Pattern` type hints instead of deprecated `typing.Pattern` on Python 3.12+.
- Repository docs now include a maintained `docs/README.md` section guide plus explicit `CONTRIBUTING.md` and `SECURITY.md` policies for contributors and maintainers.
- Adapter usage examples now cross-reference the workspace MCP sample configs and explain why Copilot uses `servers` while Claude and Gemini use `mcpServers`.
- Adapter end-to-end example snapshots now include `run_meta.product` and `summary.remediation_lifecycle.verified` so the published examples match current report output.

### Added

- Regression coverage for shared scanner rule mappings and accessible-name guess provenance in auto-fix summaries.
- Regression coverage for Markdown scanner-failure warnings and uninstall error handling.
- Static contract coverage for the WCAG report schema so required finding/fix fields and status vocabularies stay aligned with the documented contract.
- Regression coverage for version-specific citation URLs and previously missing common SC citation mappings such as `1.2.1`, `1.3.4`, `1.3.5`, `1.4.1`, and `1.4.2`.
- Regression coverage for malformed scanner JSON artifacts, malformed workflow inputs, and missing smoke-report artifacts.
- Regression coverage for skill validation contract checks and release-bundle changelog contents.
- Regression coverage for release-packaging input validation and temporary-file exclusion.
- Regression coverage for scanner launch error classification and debug-port timeout handling.
- Regression coverage for macOS browser bundle discovery, schema-version mismatch rejection, and nested normalize-report output directories.
- Explicit `__init__.py` and `py.typed` markers for `skills/libro-wcag/scripts`, plus contract/release checks that keep the typed package metadata in shipped bundles.

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
