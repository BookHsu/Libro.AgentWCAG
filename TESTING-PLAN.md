# Testing Plan

This document defines the applicable test matrix for `Libro.AgentWCAG`, maps each test type to the relevant repo area, and tracks how each applicable item is covered.

Coverage target in this repo:
- every applicable test type must have a valid coverage asset
- every automatable applicable test type should be backed by real test code
- only inherently human-evaluated categories may remain `Scripted Manual`

## Test Matrix

| Test Type | Applies | Automation Target | Repo Areas | Current Status | Coverage Mode | Coverage Asset |
| --- | --- | --- | --- | --- | --- | --- |
| Unit Test | Yes | Yes | `skills/libro-agent-wcag/scripts/wcag_workflow.py`, `skills/libro-agent-wcag/scripts/remediation_library.py` | Implemented | Automated | `test_workflow.py`, `test_remediation_library.py`, `test_matrix_completion.py` |
| Component Test | Yes | Yes | `run_accessibility_audit.py`, `normalize_report.py`, installer scripts | Implemented | Automated | `test_runner.py`, `test_cli_flows.py`, `test_install_agent.py`, `test_repo_scripts.py` |
| Module Test | Yes | Yes | `skills/libro-agent-wcag/scripts/`, `adapters/`, references | Implemented | Automated + Static Contract | `test_adapters.py`, `test_repo_contracts.py`, workflow and remediation tests |
| Integration Test | Yes | Yes | Workflow + installer + validator path | Implemented | Automated | `test_install_agent.py`, `test_repo_scripts.py`, `test_cli_flows.py`, `test_repo_invocation.py` |
| System Test | Yes | Yes | Whole repo as an installable skill product | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/scenario-assets.md` |
| End-to-End Test | Yes | Yes | Install -> invoke -> audit/report flow | Implemented | Automated + Scripted Manual | `test_cli_flows.py`, `test_matrix_completion.py`, `docs/testing/scenario-assets.md` |
| Functional Test | Yes | Yes | Reporting, install flow, language behavior, execution modes | Implemented | Automated | workflow, CLI, install, adapter, and matrix tests |
| Non-Functional Test | Yes | Yes | Performance, resilience, stability | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Smoke Test | Yes | Yes | Repo validation, root test discovery, installer basics | Implemented | Automated | `test_repo_invocation.py`, `validate_skill.py`, install tests |
| Sanity Test | Yes | Yes | Recently changed areas | Implemented | Automated | current automated suite |
| Regression Test | Yes | Yes | All core workflow and install paths | Implemented | Automated | full unit/CLI/contract suite |
| Acceptance Test / UAT | Yes | No | Installed skill behavior against intended user outcomes | Implemented | Scripted Manual | `docs/testing/manual-checklists.md` |
| Alpha Test | Yes | No | Internal usage before release | Implemented | Scripted Manual | `docs/testing/manual-checklists.md` |
| Beta Test | Yes | No | External real-user trial | Implemented | Scripted Manual | `docs/testing/manual-checklists.md` |
| Black-box Test | Yes | Yes | CLI tools and report outputs | Implemented | Automated | `test_cli_flows.py`, install/doctor/uninstall subprocess tests |
| White-box Test | Yes | Yes | Workflow internals and branching logic | Implemented | Automated | `test_workflow.py`, `test_runner.py`, `test_remediation_library.py` |
| Gray-box Test | Yes | Yes | Install + adapter + workflow contracts | Implemented | Automated | `test_repo_scripts.py`, `test_repo_contracts.py`, `test_matrix_completion.py` |
| Static Testing | Yes | Yes | Code review, validator, file structure, docs | Implemented | Static Contract + Automated | `validate_skill.py`, `test_repo_contracts.py` |
| Dynamic Testing | Yes | Yes | All runtime scripts | Implemented | Automated | CLI and workflow subprocess tests |
| Boundary Value Testing | Yes | Yes | CLI args, execution modes, target validation | Implemented | Automated | `test_runner.py`, `test_workflow.py`, `test_cli_flows.py` |
| Equivalence Partitioning | Yes | Yes | Versions, levels, agent targets, language variants | Implemented | Automated | `test_workflow.py`, `test_matrix_completion.py`, install tests |
| Decision Table Testing | Yes | Yes | `task_mode` + `execution_mode` + target availability | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/scenario-assets.md` |
| State Transition Testing | Yes | Yes | Execution/report lifecycle | Implemented | Automated + Scripted Manual | workflow status tests, `docs/testing/scenario-assets.md` |
| Error Guessing | Yes | Yes | Invalid targets, missing files, duplicate findings, scanner failure | Implemented | Automated | `test_runner.py`, `test_cli_flows.py`, `test_workflow.py`, `test_repo_scripts.py` |
| Exploratory Testing | Yes | No | Installed skill behavior on real pages | Implemented | Scripted Manual | `docs/testing/manual-checklists.md` |
| Scenario Test | Yes | Yes | Real-world create/modify workflows | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/scenario-assets.md` |
| Data-Driven Test | Yes | Yes | Same workflow with multiple WCAG versions/levels/languages | Implemented | Automated | `test_workflow.py`, `test_matrix_completion.py` |
| Parameterized Test | Yes | Yes | Versions, levels, execution modes, agents | Implemented | Automated | loop-based subtests in workflow/install/matrix tests |
| API Test | No | No | N/A | Not Applicable | None | repo exposes no API |
| UI Test | No | No | N/A | Not Applicable | None | repo ships no UI |
| Compatibility Test | Yes | Yes | Different agents, OS/script entry points | Implemented | Automated + Scripted Manual | `test_install_agent.py`, `test_repo_scripts.py`, `docs/testing/nonfunctional-checks.md` |
| Cross-browser Test | No | No | N/A | Not Applicable | None | repo ships no browser UI |
| Responsive Test | No | No | N/A | Not Applicable | None | repo ships no responsive UI |
| Usability Test | Yes | No | Installation instructions and invocation flow | Implemented | Scripted Manual | `docs/testing/manual-checklists.md` |
| Accessibility Test | Yes | Yes | HTML fixture scanning and report output | Implemented | Automated | workflow/report tests and CLI report generation tests |
| Performance Test | Yes | Yes | Workflow speed and scanner overhead | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Load Test | No | No | N/A | Not Applicable | None | no service endpoint |
| Stress Test | Yes | Yes | Large fixture sets / scanner timeouts | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Spike Test | No | No | N/A | Not Applicable | None | no service endpoint |
| Endurance / Soak Test | Yes | Yes | Long-running scan batches | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Volume / Capacity Test | Yes | Yes | Large report / many fixtures | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Scalability Test | Yes | Yes | Batch audit workflows | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Security Test | Yes | Yes | CLI input boundaries, install path handling | Implemented | Automated + Scripted Manual | `test_runner.py`, `test_cli_flows.py`, install overwrite tests, `docs/testing/nonfunctional-checks.md` |
| Vulnerability Scan | Yes | Yes | Dependencies and scripts | Implemented | Automated + Scripted Manual | `test_repo_invocation.py`, `docs/testing/nonfunctional-checks.md` |
| Penetration Test | No | No | N/A | Not Applicable | None | no exposed service |
| Authorization Test | No | No | N/A | Not Applicable | None | no auth system |
| Authentication Test | No | No | N/A | Not Applicable | None | no login flow |
| Recovery Test | Yes | Yes | Failed scan recovery and reinstall flows | Implemented | Automated + Scripted Manual | `test_cli_flows.py`, `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Failover Test | No | No | N/A | Not Applicable | None | no HA topology |
| Backup/Restore Test | No | No | N/A | Not Applicable | None | no persistent data store |
| Installation Test | Yes | Yes | Installer, wrappers, manifest generation | Implemented | Automated | `test_install_agent.py`, `test_repo_scripts.py` |
| Upgrade Test | Yes | Yes | Reinstall with `--force`, future version migration | Implemented | Automated | `test_repo_scripts.py`, `test_matrix_completion.py` |
| Configuration Test | Yes | Yes | Agent choice, destination override, force behavior, language | Implemented | Automated | install and matrix tests |
| Localization Test | Yes | Yes | Markdown output language | Implemented | Automated | `test_workflow.py`, `test_cli_flows.py` |
| Internationalization Test | Yes | Yes | Language fallback design | Implemented | Automated | `test_matrix_completion.py`, `test_workflow.py` |
| Database Test | No | No | N/A | Not Applicable | None | no database |
| DB Migration Test | No | No | N/A | Not Applicable | None | no database |
| Interrupt Test | Yes | Yes | Mid-install overwrite / missing files / scanner failure | Implemented | Automated + Scripted Manual | broken install tests, scanner error tests, `docs/testing/nonfunctional-checks.md` |
| Concurrency Test | Yes | Yes | Parallel installs to different destinations | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/nonfunctional-checks.md` |
| Chaos Test | No | No | N/A | Not Applicable | None | no distributed runtime system |

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

- Automated tests for workflow logic, rule mapping, severity bands, citations, remediation strategy defaults, edge cases, CLI flows, install flows, scanner command/error paths, repo contracts, and matrix-completion scenarios.
- Static contract checks for all non-test repo files.
- Scripted manual assets for inherently human-evaluated categories and for mixed-mode categories that still benefit from review checklists.
- Root-level smoke coverage through repo discovery and validator execution.
- Automated baseline vulnerability dependency check coverage via `python -m pip check` in `test_repo_invocation.py`.

## Still Worth Adding

- Real-scanner coverage in CI still depends on environment/tooling availability; keep expanding fixtures and failure-mode assertions when `npx @axe-core/cli` and `lighthouse` are available.
- Keep refreshing representative realistic-sample artifacts (`docs/testing/realistic-sample/artifacts/`) as remediation behavior evolves.
- Optional dependency vulnerability tooling once dependencies grow beyond the current minimal set.

## Execution Commands

Run the current automated suite:

```powershell
python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-agent-wcag
```


