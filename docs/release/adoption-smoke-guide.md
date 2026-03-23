# Adoption Smoke Guide

Use this guide to validate install, doctor, smoke, integrity, and troubleshooting flows for a downstream adopter.

## First-Run Smoke

Goal: confirm that a user can install, verify, run, and remove the skill without manual repo-specific intervention.

Run the scripted realistic validation flow:

- `python .\scripts\run-realistic-validation-smoke.py --agent codex`

The script executes:

1. `install-agent.py --agent codex --dest <temp> --force`
2. `doctor-agent.py --agent codex --dest <temp>`
3. `run_accessibility_audit.py --execution-mode apply-fixes --wcag-version 2.2` against `docs/testing/realistic-sample/mixed-findings.html`
4. Captures representative artifacts in `docs/testing/realistic-sample/artifacts/`

Pass criteria:

- install command succeeds with no missing manifest assets
- doctor command reports healthy right after install
- audit command emits both JSON and Markdown reports
- apply-fixes output emits diff and snapshot artifacts
- smoke summary shows mixed remediation outcomes

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
- `skills/libro-agent-wcag/scripts/run_accessibility_audit.py`

Keep this workflow script-first and minimal. For deterministic smoke artifacts, reuse `docs/testing/realistic-sample/` plus mock scanner payloads.

## Post-Install Integrity Verification

Run integrity-aware doctor checks:

- `python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity`
- `python .\scripts\doctor-agent.py --agent all --dest .\.tmp\agents --verify-manifest-integrity`

Healthy output should show:

- `ok = true`
- `manifest_integrity.verified = true`
- no hash mismatches
- no missing files

If integrity fails:

- reinstall with `--force`
- re-run doctor with `--verify-manifest-integrity`
- compare installed adapter contents against `skills/libro-agent-wcag/adapters/<adapter>/`

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
