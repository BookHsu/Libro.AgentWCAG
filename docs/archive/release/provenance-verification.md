# Provenance Verification Workflow

Use this workflow to verify baseline evidence integrity before applying debt transitions in CI/release gates.

## 1. Generate baseline evidence artifacts

Run a baseline capture with evidence mode enabled:

```powershell
python skills/libro-wcag/scripts/run_accessibility_audit.py `
  --target <target> `
  --output-dir out/baseline `
  --baseline-evidence-mode hash `
  --report-format json
```

Expected outputs:

- `out/baseline/wcag-report.json` (`run_meta.baseline_evidence` contains `report_hash`)
- `out/baseline/artifact-manifest.json` (checksums + generator metadata)

## 2. Verify baseline before diff gating

When comparing against a baseline report, enable evidence verification:

```powershell
python skills/libro-wcag/scripts/run_accessibility_audit.py `
  --target <target> `
  --output-dir out/compare `
  --baseline-report out/baseline/wcag-report.json `
  --baseline-evidence-mode hash-chain `
  --fail-on moderate `
  --fail-on-new-only
```

Behavior:

- If baseline declared hash mismatches the current baseline file content, execution fails fast.
- In `hash-chain` mode, chain lineage is validated/extended with `baseline_chain_parent` and `chain_hash`.

## 3. CI checks to archive

Archive these artifacts for every release candidate run:

- `artifact-manifest.json`
- `wcag-report.json` or `wcag-report.sarif`
- `wcag-report.md`
- `schemas/wcag-report-1.0.0.schema.json`

Recommended CI assertions:

- `artifact-manifest.json` contains `artifact_count > 0` and all entries include 64-char `sha256`.
- `run_meta.baseline_evidence.baseline_verification.verified` is `true` when `--baseline-report` is used.
- `run_meta.baseline_evidence.mode` matches the expected pipeline mode (`hash` or `hash-chain`).

## 4. Release readiness handoff

Add links to archived manifest + baseline verification artifacts in release notes/review checklist so approvers can verify evidence provenance quickly.
