# Testing Matrix

This document defines the main maintained test matrix for `Libro.AgentWCAG`, with emphasis on CLI behavior, report output, installation flows, and public documentation consistency.

## Core Matrix

| Test Type | Applies | Automated | Main Scope | Representative Assets |
| --- | --- | --- | --- | --- |
| Unit Test | Yes | Yes | workflow, remediation, helpers | `test_workflow.py`, `test_remediation_library.py`, `test_rewrite_helpers.py` |
| Component Test | Yes | Yes | `run_accessibility_audit.py`, `scripts/libro.py`, installer scripts | `test_runner.py`, `test_cli_flows.py`, `test_repo_scripts.py` |
| Integration Test | Yes | Yes | install -> doctor -> audit/report | `test_install_agent.py`, `test_repo_scripts.py`, `test_repo_invocation.py` |
| System Test | Yes | Partial | repo as an installable skill product | `test_matrix_completion.py`, `docs/testing/testing-playbook.md` |
| End-to-End Test | Yes | Partial | install -> invoke -> output artifacts | `test_cli_flows.py`, `test_matrix_completion.py`, `docs/testing/testing-playbook.md` |
| Regression Test | Yes | Yes | CLI, contract, release, reporting | full `test_*.py` suite |
| Static Contract Test | Yes | Yes | repo structure, schema, docs, adapter contract | `test_repo_contracts.py`, `validate_skill.py` |
| Documentation Consistency | Yes | Partial | README, docs, public commands | `test_release_docs.py`, `docs/testing/testing-playbook.md` |
| Compatibility Test | Yes | Yes | agents, wrappers, cross-platform entrypoints | `test_install_agent.py`, `test_repo_scripts.py` |
| Security / Boundary Test | Yes | Yes | invalid target, overwrite, path handling | `test_runner.py`, `test_cli_flows.py`, install overwrite tests |
| Performance / Scalability | Yes | Partial | normalization, batch scan, artifact emission | `test_matrix_completion.py`, `docs/testing/testing-playbook.md` |

## Current High-Value Coverage Areas

### CLI and report output

- `skills/libro-wcag/scripts/run_accessibility_audit.py`
- `scripts/libro.py`
- `skills/libro-wcag/scripts/aggregate_report.py`
- `skills/libro-wcag/scripts/report_renderers.py`

Coverage focus:

- single HTML / URL audit
- `summary-only` JSON
- SARIF output
- `--print-examples`
- `--artifacts minimal`
- `libro report --no-color`

### Installation and verification tooling

- `scripts/install-agent.py`
- `scripts/doctor-agent.py`
- `scripts/uninstall-agent.py`
- `scripts/libro.ps1`
- `scripts/libro.sh`
- `bin/libro.js`

Coverage focus:

- install / doctor / remove
- wrapper-to-Python entrypoint wiring
- scanner preflight status
- workspace installation paths

### Contract and report shape

- `skills/libro-wcag/SKILL.md`
- `skills/libro-wcag/references/core-spec.md`
- `skills/libro-wcag/schemas/wcag-report-1.0.0.schema.json`

Coverage focus:

- stable JSON top-level keys
- fixed Markdown column order
- schema version alignment
- adapter / repo contract drift prevention

## Minimum Validation Commands

```powershell
python -m unittest skills.libro-wcag.scripts.tests.test_cli_flows
python -m unittest skills.libro-wcag.scripts.tests.test_repo_scripts
python scripts/validate_skill.py skills/libro-wcag
```

## Full Validation Commands

```powershell
python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-wcag
```

## Public Interface Checks

After changing the public CLI or README, confirm at least:

- README example commands exist and run
- wrappers support the public commands referenced by README
- the three main paths all have smoke coverage: `audit`, `scan`, and `report`
- the zh-TW primary files and English companion files stay aligned
