# Testing Playbook

This document consolidates the most useful test, smoke, documentation-consistency, and manual validation flows for the public project.

## Minimum Regression Set

After changing CLI behavior, report output, README content, or wrappers, run at least:

```powershell
python -m unittest skills.libro-wcag.scripts.tests.test_cli_flows
python -m unittest skills.libro-wcag.scripts.tests.test_repo_scripts
python scripts/validate_skill.py skills/libro-wcag
```

For smaller edits, start with the narrowest useful subset:

```powershell
python -m unittest skills.libro-wcag.scripts.tests.test_cli_flows.CliFlowTests.test_run_accessibility_audit_summary_only_prints_compact_json
python -m unittest skills.libro-wcag.scripts.tests.test_repo_scripts.RepoScriptTests.test_libro_audit_preflight_only_returns_json
```

## CLI Smoke Paths

### 1. Preflight

Confirm the Python CLI and scanner toolchain status can be read:

```powershell
python .\scripts\libro.py audit --preflight-only
```

### 2. Single HTML audit

```powershell
python .\scripts\libro.py audit .\docs\testing\realistic-sample\mixed-findings.html --skip-axe --skip-lighthouse --summary-only --output-dir .\out\smoke
```

Expected:

- stdout is compact JSON
- `wcag-report.json` and `wcag-report.md` are written
- `run_meta.product` and `report_schema` are present

### 3. Reduced artifact mode

```powershell
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --target .\docs\testing\realistic-sample\mixed-findings.html --skip-axe --skip-lighthouse --summary-only --artifacts minimal --output-dir .\out\minimal
```

Expected:

- core reports still exist
- sidecars such as `debt-trend.json` and `scanner-stability.json` are not written

### 4. Aggregate report

```powershell
python .\scripts\libro.py report .\out\smoke\wcag-report.json --format terminal --no-color
python .\scripts\libro.py report .\out\smoke\wcag-report.json --format html --output .\out\wcag-summary.html
```

Expected:

- `--no-color` emits no ANSI escape sequences
- terminal mode remains printable on Windows CP950 terminals
- HTML mode writes an aggregate report successfully

## UX Checks

After CLI or README changes, manually confirm:

- `python .\scripts\libro.py audit --print-examples`
- `python .\scripts\libro.py scan --print-examples`
- `python .\scripts\libro.py report --print-examples`
- `python .\skills\libro-wcag\scripts\run_accessibility_audit.py --print-examples`

Check that:

- example commands match real supported flags
- README and docs do not contradict CLI help
- wrappers (`libro.ps1`, `libro.sh`, `bin/libro.js`) still cover the public commands

## Public Docs Consistency

After editing formal human-facing docs, confirm:

- `README.md` and `README.en.md` are aligned
- `docs/README.md` and `docs/README.en.md` work as documentation entry points
- `docs/testing/testing-playbook.md` and `docs/testing/testing-playbook.en.md` stay aligned
- `docs/testing/test-matrix.md` and `docs/testing/test-matrix.en.md` stay aligned
- `CHANGELOG.md` records externally visible behavior changes

## Broader Validation

For higher confidence, run the full suite:

```powershell
python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-wcag
```

If the change touches release, packaging, or docs, also run:

```powershell
python -m unittest skills.libro-wcag.scripts.tests.test_release_docs
python -m unittest skills.libro-wcag.scripts.tests.test_release_packaging
python -m unittest skills.libro-wcag.scripts.tests.test_release_workflow
```

## Manual Scenarios

### Acceptance / UAT

- install the skill for a target agent
- run `audit-only`, `suggest-only`, and `apply-fixes`
- confirm report fields, statuses, citations, and modification notes are understandable

### Exploratory

- try local HTML, URL targets, invalid schemes, and missing-scanner setups
- confirm errors lead to the next step instead of only showing a traceback

### Documentation

- start from README and complete install -> audit -> report without oral handoff
- confirm a new user can understand the three main paths: single audit, batch scan, and aggregate report
