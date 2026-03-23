# Demo Package Walkthrough

This walkthrough provides a minimal, repeatable package-style validation path outside the unit test suite.

## Goal

Verify that a downstream user can copy a tiny bundle, install the skill, run a scan, and inspect artifacts without using repo test harness commands.

## Demo package layout

Create a temporary folder with this structure:

```text
demo-package/
  target/
    page.html
  run-demo.ps1
  run-demo.sh
```

- `target/page.html`: any local page to audit (the realistic sample can be reused).
- `run-demo.ps1` and `run-demo.sh`: thin wrappers that call the repo scripts.

## PowerShell demo wrapper

```powershell
param(
  [string]$RepoRoot = ".",
  [string]$Target = ".\target\page.html"
)

python "$RepoRoot\scripts\install-agent.py" --agent codex --dest ".\.demo-skill" --force
python "$RepoRoot\scripts\doctor-agent.py" --agent codex --dest ".\.demo-skill"
python "$RepoRoot\skills\libro-agent-wcag\scripts\run_accessibility_audit.py" `
  --target $Target `
  --task-mode modify `
  --execution-mode suggest-only `
  --wcag-version 2.2 `
  --conformance-level AA `
  --output-language zh-TW
```

## Shell demo wrapper

```sh
#!/usr/bin/env sh
set -eu

REPO_ROOT="${1:-.}"
TARGET="${2:-./target/page.html}"

python "$REPO_ROOT/scripts/install-agent.py" --agent codex --dest "./.demo-skill" --force
python "$REPO_ROOT/scripts/doctor-agent.py" --agent codex --dest "./.demo-skill"
python "$REPO_ROOT/skills/libro-agent-wcag/scripts/run_accessibility_audit.py" \
  --target "$TARGET" \
  --task-mode modify \
  --execution-mode suggest-only \
  --wcag-version 2.2 \
  --conformance-level AA \
  --output-language zh-TW
```

## Pass criteria

- Installer and doctor commands complete successfully.
- Audit command emits `wcag-report.json` and `wcag-report.md`.
- Findings include WCAG citations and remediation guidance.
- Demo run can be repeated with stable output shape.

## Notes

- Keep this walkthrough intentionally small and script-first.
- For deterministic smoke artifacts, use `docs/testing/realistic-sample/` plus mock scanner payloads.
