# Testing Plan

This document defines the applicable test matrix for `Libro.AgentWCAG`, maps each test type to the relevant repo area, and tracks how each applicable item is covered.

Coverage target in this repo: every applicable test type must have either an automated test, a static contract check, or a documented manual checklist asset.

## Test Matrix

| Test Type | Applies | Repo Areas | Current Status | Coverage Asset |
| --- | --- | --- | --- | --- |
| Unit Test | Yes | `skills/libro-agent-wcag/scripts/wcag_workflow.py`, `skills/libro-agent-wcag/scripts/remediation_library.py` | Implemented | `test_workflow.py`, `test_remediation_library.py`, `test_matrix_completion.py` |
| Component Test | Yes | `run_accessibility_audit.py`, `normalize_report.py`, installer scripts | Implemented | `test_runner.py`, `test_cli_flows.py`, `test_install_agent.py`, `test_repo_scripts.py` |
| Module Test | Yes | `skills/libro-agent-wcag/scripts/`, `adapters/`, references | Implemented | `test_adapters.py`, `test_repo_contracts.py`, workflow and remediation tests |
| Integration Test | Yes | Workflow + installer + validator path | Implemented | `test_install_agent.py`, `test_repo_scripts.py`, `test_cli_flows.py`, `test_repo_invocation.py` |
| System Test | Yes | Whole repo as an installable skill product | Implemented | `docs/testing/scenario-assets.md` plus `test_matrix_completion.py` system-like flows |
| End-to-End Test | Yes | Install -> invoke -> audit/report flow | Implemented | `docs/testing/scenario-assets.md`, `test_cli_flows.py`, `test_matrix_completion.py` |
| Functional Test | Yes | Reporting, install flow, language behavior, execution modes | Implemented | Workflow, CLI, install, adapter, and matrix tests |
| Non-Functional Test | Yes | Performance, resilience, stability | Implemented | `docs/testing/nonfunctional-checks.md`, `test_matrix_completion.py` |
| Smoke Test | Yes | Repo validation, root test discovery, installer basics | Implemented | `test_repo_invocation.py`, `validate_skill.py`, install tests |
| Sanity Test | Yes | Recently changed areas | Implemented | Current automated suite |
| Regression Test | Yes | All core workflow and install paths | Implemented | Full unit/CLI/contract suite |
| Acceptance Test / UAT | Yes | Installed skill behavior against intended user outcomes | Implemented | `docs/testing/manual-checklists.md` |
| Alpha Test | Yes | Internal usage before release | Implemented | `docs/testing/manual-checklists.md` |
| Beta Test | Yes | External real-user trial | Implemented | `docs/testing/manual-checklists.md` |
| Black-box Test | Yes | CLI tools and report outputs | Implemented | `test_cli_flows.py`, install/doctor/uninstall subprocess tests |
| White-box Test | Yes | Workflow internals and branching logic | Implemented | `test_workflow.py`, `test_runner.py`, `test_remediation_library.py` |
| Gray-box Test | Yes | Install + adapter + workflow contracts | Implemented | `test_repo_scripts.py`, `test_repo_contracts.py`, `test_matrix_completion.py` |
| Static Testing | Yes | Code review, validator, file structure, docs | Implemented | `validate_skill.py`, `test_repo_contracts.py` |
| Dynamic Testing | Yes | All runtime scripts | Implemented | CLI and workflow subprocess tests |
| Boundary Value Testing | Yes | CLI args, execution modes, target validation | Implemented | `test_runner.py`, `test_workflow.py`, `test_cli_flows.py` |
| Equivalence Partitioning | Yes | Versions, levels, agent targets, language variants | Implemented | `test_workflow.py`, `test_matrix_completion.py`, install tests |
| Decision Table Testing | Yes | `task_mode` + `execution_mode` + target availability | Implemented | `docs/testing/scenario-assets.md`, `test_matrix_completion.py` |
| State Transition Testing | Yes | Execution/report lifecycle | Implemented | `docs/testing/scenario-assets.md`, workflow status tests |
| Error Guessing | Yes | Invalid targets, missing files, duplicate findings, scanner failure | Implemented | `test_runner.py`, `test_cli_flows.py`, `test_workflow.py`, `test_repo_scripts.py` |
| Exploratory Testing | Yes | Installed skill behavior on real pages | Implemented | `docs/testing/manual-checklists.md` |
| Scenario Test | Yes | Real-world create/modify workflows | Implemented | `docs/testing/scenario-assets.md`, `test_matrix_completion.py` |
| Data-Driven Test | Yes | Same workflow with multiple WCAG versions/levels/languages | Implemented | `test_workflow.py`, `test_matrix_completion.py` |
| Parameterized Test | Yes | Versions, levels, execution modes, agents | Implemented | Loop-based subtests in workflow/install/matrix tests |
| API Test | No | N/A | Not Applicable | Repo exposes no API |
| UI Test | No | N/A | Not Applicable | Repo ships no UI |
| Compatibility Test | Yes | Different agents, OS/script entry points | Implemented | `test_install_agent.py`, `test_repo_scripts.py`, `docs/testing/nonfunctional-checks.md` |
| Cross-browser Test | No | N/A | Not Applicable | Repo ships no browser UI |
| Responsive Test | No | N/A | Not Applicable | Repo ships no responsive UI |
| Usability Test | Yes | Installation instructions and invocation flow | Implemented | `docs/testing/manual-checklists.md` |
| Accessibility Test | Yes | HTML fixture scanning and report output | Implemented | Workflow/report tests and CLI report generation tests |
| Performance Test | Yes | Workflow speed and scanner overhead | Implemented | `docs/testing/nonfunctional-checks.md`, `test_matrix_completion.py` |
| Load Test | No | N/A | Not Applicable | No service endpoint |
| Stress Test | Yes | Large fixture sets / scanner timeouts | Implemented | `docs/testing/nonfunctional-checks.md`, `test_matrix_completion.py` |
| Spike Test | No | N/A | Not Applicable | No service endpoint |
| Endurance / Soak Test | Yes | Long-running scan batches | Implemented | `docs/testing/nonfunctional-checks.md`, `test_matrix_completion.py` |
| Volume / Capacity Test | Yes | Large report / many fixtures | Implemented | `docs/testing/nonfunctional-checks.md`, `test_matrix_completion.py` |
| Scalability Test | Yes | Batch audit workflows | Implemented | `docs/testing/nonfunctional-checks.md`, `test_matrix_completion.py` |
| Security Test | Yes | CLI input boundaries, install path handling | Implemented | `test_runner.py`, `test_cli_flows.py`, install overwrite tests, `docs/testing/nonfunctional-checks.md` |
| Vulnerability Scan | Yes | Dependencies and scripts | Implemented | `docs/testing/nonfunctional-checks.md` |
| Penetration Test | No | N/A | Not Applicable | No exposed service |
| Authorization Test | No | N/A | Not Applicable | No auth system |
| Authentication Test | No | N/A | Not Applicable | No login flow |
| Recovery Test | Yes | Failed scan recovery and reinstall flows | Implemented | `test_cli_flows.py`, `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Failover Test | No | N/A | Not Applicable | No HA topology |
| Backup/Restore Test | No | N/A | Not Applicable | No persistent data store |
| Installation Test | Yes | Installer, wrappers, manifest generation | Implemented | `test_install_agent.py`, `test_repo_scripts.py` |
| Upgrade Test | Yes | Reinstall with `--force`, future version migration | Implemented | `test_repo_scripts.py`, `test_matrix_completion.py` |
| Configuration Test | Yes | Agent choice, destination override, force behavior, language | Implemented | install and matrix tests |
| Localization Test | Yes | Markdown output language | Implemented | `test_workflow.py`, `test_cli_flows.py` |
| Internationalization Test | Yes | Language fallback design | Implemented | `test_matrix_completion.py`, `test_workflow.py` |
| Database Test | No | N/A | Not Applicable | No database |
| DB Migration Test | No | N/A | Not Applicable | No database |
| Interrupt Test | Yes | Mid-install overwrite / missing files / scanner failure | Implemented | broken install tests, scanner error tests, `docs/testing/nonfunctional-checks.md` |
| Concurrency Test | Yes | Parallel installs to different destinations | Implemented | `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Chaos Test | No | N/A | Not Applicable | No distributed runtime system |

## Repo Mapping

### Core workflow and reporting

- `skills/libro-agent-wcag/scripts/wcag_workflow.py`
- `skills/libro-agent-wcag/scripts/normalize_report.py`
- `skills/libro-agent-wcag/scripts/run_accessibility_audit.py`
- Coverage:
  - Unit Test
  - Component Test
  - Functional Test
  - Boundary Value Testing
  - Error Guessing
  - Localization Test
  - Accessibility Test
  - Performance / Stress / Volume checks

### Remediation strategy logic

- `skills/libro-agent-wcag/scripts/remediation_library.py`
- Coverage:
  - Unit Test
  - Module Test
  - Functional Test
  - Data-Driven Test

### Installation and verification tooling

- `scripts/install-agent.py`
- `scripts/install-agent.ps1`
- `scripts/install-agent.sh`
- `scripts/uninstall-agent.py`
- `scripts/doctor-agent.py`
- Coverage:
  - Installation Test
  - Integration Test
  - Configuration Test
  - Recovery Test
  - Compatibility Test
  - Smoke Test
  - Concurrency Test

### Skill contract and adapters

- `skills/libro-agent-wcag/SKILL.md`
- `skills/libro-agent-wcag/agents/openai.yaml`
- `skills/libro-agent-wcag/adapters/*/prompt-template.md`
- Coverage:
  - Module Test
  - Black-box Test
  - Gray-box Test
  - Regression Test
  - Static Testing

### References and framework guides

- `skills/libro-agent-wcag/references/core-spec.md`
- `skills/libro-agent-wcag/references/adapter-mapping.md`
- `skills/libro-agent-wcag/references/wcag-citations.md`
- `skills/libro-agent-wcag/references/framework-patterns-*.md`
- Coverage:
  - Static Testing
  - Acceptance Test assets
  - Scenario Test assets

### Manual assets

- `docs/testing/manual-checklists.md`
- `docs/testing/scenario-assets.md`
- `docs/testing/nonfunctional-checks.md`
- Coverage:
  - Acceptance / Alpha / Beta / Usability / Exploratory
  - System / End-to-End / Scenario / Decision Table / State Transition
  - Non-functional / Compatibility / Performance / Stress / Endurance / Volume / Scalability / Security / Vulnerability / Recovery / Interrupt / Concurrency

## Already Implemented

- Automated tests for workflow logic, rule mapping, severity bands, citations, remediation strategy defaults, edge cases, CLI flows, install flows, repo contracts, and matrix-completion scenarios.
- Static contract checks for all non-test repo files.
- Manual testing assets for all applicable non-automated matrix categories.
- Root-level smoke coverage through repo discovery and validator execution.

## Still Worth Adding

- Real scanner-backed integration tests that invoke `npx @axe-core/cli` and `lighthouse` in CI when the environment allows it.
- Snapshot fixtures for larger JSON/Markdown outputs.
- Optional dependency vulnerability tooling once dependencies grow beyond the current minimal set.

## Execution Commands

Run the current automated suite:

```powershell
python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-agent-wcag
```
