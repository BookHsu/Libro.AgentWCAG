# Adoption Smoke Guide

Use this guide to validate install, doctor, smoke, integrity, and troubleshooting flows for a downstream adopter.

## First-Run Smoke

Goal: confirm that a user can install, verify, run, and remove the skill without manual repo-specific intervention.

Before consumer smoke, stage versioned release assets:

- `python .\scripts\package-release.py --output-dir .\dist\release --overwrite`

Expected release assets:

- `libro-wcag-<version>-codex.zip`
- `libro-wcag-<version>-claude.zip`
- `libro-wcag-<version>-gemini.zip`
- `libro-wcag-<version>-copilot.zip`
- `libro-wcag-<version>-all-in-one.zip`
- `libro-wcag-<version>-release-manifest.json`
- `libro-wcag-<version>-sha256sums.txt`
- `latest-release.json`

## Release Consumer Flow

Use the packaged bootstrap installers instead of repo-relative source paths:

- `pwsh -File .\scripts\install-latest.ps1 -ReleaseBase .\dist\release -Agent codex`
- `sh ./scripts/install-latest.sh --release-base ./dist/release --agent codex`

Both flows support latest resolution through `latest-release.json` and pinned installs through `--version <semver>`. They must verify `libro-wcag-<version>-sha256sums.txt` before invoking the packaged installer.

Clean-environment scripted smoke:

- `python .\scripts\run-release-adoption-smoke.py --release-dir .\dist\release --agent codex`

Success criteria for clean release smoke:

- starts from the packaged release asset directory, not repo-relative skill sources
- verifies the selected bundle hash against both `sha256sums.txt` and the release manifest
- installs from the extracted bundle with release provenance exported through environment variables
- runs `doctor-agent.py --verify-manifest-integrity`
- runs a mock-backed audit from the extracted bundle
- uninstalls cleanly
- writes `smoke-summary.json`

Failure triage must preserve:

- install / doctor / audit / uninstall logs
- the resolved release manifest and bundle filename
- the generated `smoke-summary.json`

This same flow is the publish gate smoke lane consumed by `.github/workflows/release.yml`.

Repo-native smoke vs release-consumer smoke:

- repo-native smoke validates scripts directly from the checkout and is useful during feature development
- release-consumer smoke starts from packaged release assets and is the gate for publishable operator experience

Run the scripted realistic validation flow:

- `python .\scripts\run-realistic-validation-smoke.py --agent codex`

The script executes:

1. `install-agent.py --agent codex --dest <temp> --force`
2. `doctor-agent.py --agent codex --dest <temp>`
3. `run_accessibility_audit.py --execution-mode apply-fixes --wcag-version 2.2` against `docs/testing/realistic-sample/mixed-findings.html`
4. Captures representative artifacts in `docs/testing/realistic-sample/artifacts/`

Pass criteria:

- install command succeeds with no missing manifest assets
- doctor command reports healthy right after install, including `manifest_provenance.verified = true` and `version_consistency.verified = true`
- audit command emits both JSON and Markdown reports
- apply-fixes output emits diff and snapshot artifacts
- smoke summary shows mixed remediation outcomes plus installed/report provenance

Representative smoke artifacts should preserve:

- installer provenance in `install-manifest.json` (`product_version`, `source_revision`)
- doctor consistency data (`expected_product`, `installed_product`, `version_consistency`)
- report provenance in `wcag-report.sample.json`, `wcag-report.sample.md`, and SARIF/manifest examples stored beside the smoke output

## Demo Package Walkthrough

Create a temporary folder with this structure:

```text
demo-package/
  target/
    page.html
  run-demo.ps1
  run-demo.sh
```

Use thin wrapper scripts to call:

- `scripts/install-agent.py`
- `scripts/doctor-agent.py`
- `skills/libro-wcag/scripts/run_accessibility_audit.py`

Keep this workflow script-first and minimal. For deterministic smoke artifacts, reuse `docs/testing/realistic-sample/` plus mock scanner payloads.

## Post-Install Integrity Verification

Run integrity-aware doctor checks:

- `python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity`
- `python .\scripts\doctor-agent.py --agent all --dest .\.tmp\agents --verify-manifest-integrity`

Healthy output should show:

- `ok = true`
- `manifest_integrity.verified = true`
- `manifest_provenance.verified = true`
- `version_consistency.verified = true`
- no hash mismatches
- no missing files

If integrity fails:

- reinstall with `--force`
- re-run doctor with `--verify-manifest-integrity`
- compare installed adapter contents against `skills/libro-wcag/adapters/<adapter>/`

## Troubleshooting Intake

Collect this minimum context for install or remediation issues:

- platform: OS, shell, Python version
- agent target: `codex`, `claude`, `gemini`, or `copilot`
- install destination path
- repo commit or installed package version
- exact failing command

Fast triage buckets:

1. environment or setup error
2. installer path or permission error
3. scanner invocation error
4. contract mismatch
5. remediation scope misunderstanding
