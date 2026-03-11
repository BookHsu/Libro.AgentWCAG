# Testing Plan

This document defines the applicable test matrix for `Libro.AgentWCAG`, maps each test type to the relevant repo area, and tracks what is already covered versus what still needs to be added.

## Test Matrix

| Test Type | Applies | Repo Areas | Current Status | Notes |
| --- | --- | --- | --- | --- |
| Unit Test | Yes | `skills/libro-agent-wcag/scripts/wcag_workflow.py`, `skills/libro-agent-wcag/scripts/remediation_library.py` | Implemented | Core rule mapping, language output, severity, citation, remediation strategy logic are covered. |
| Component Test | Yes | `skills/libro-agent-wcag/scripts/run_accessibility_audit.py`, `skills/libro-agent-wcag/scripts/normalize_report.py`, installer scripts | Partial | Some CLI behaviors are covered; more command-path coverage can be added. |
| Module Test | Yes | `skills/libro-agent-wcag/scripts/`, `skills/libro-agent-wcag/adapters/` | Partial | Adapter and workflow modules are covered; full module-level scenarios can expand. |
| Integration Test | Yes | Workflow + installer + validator path | Partial | Install/doctor/uninstall and CLI flows exist; scanner-backed integration can expand further. |
| System Test | Yes | Whole repo as an installable skill product | Planned | Needs a more formal end-to-end validation flow across install, invoke, and report generation. |
| End-to-End Test | Yes | Install -> invoke -> audit/report flow | Planned | Best implemented with sample fixtures and real agent entry simulations. |
| Functional Test | Yes | Reporting, install flow, language behavior, execution modes | Implemented / Partial | Major functions are covered; more user-facing scenarios can be added. |
| Non-Functional Test | Partial | Performance, resilience, stability | Planned | Not a single test type; use concrete subtypes below. |
| Smoke Test | Yes | Repo validation, root test discovery, installer basics | Implemented | Root discovery and validator checks already exist. |
| Sanity Test | Yes | Recently changed areas | Implemented | Current unit/integration suite serves this role after changes. |
| Regression Test | Yes | All core workflow and install paths | Implemented / Ongoing | Current test suite protects against common regressions; should keep growing. |
| Acceptance Test / UAT | Yes | Installed skill behavior against intended user outcomes | Planned | Good candidate for manual checklist and future sample scenarios. |
| Alpha Test | Yes | Internal usage before release | Planned | Manual team usage on sample projects. |
| Beta Test | Yes | External real-user trial | Planned | Useful once published broadly. |
| Black-box Test | Yes | CLI tools and report outputs | Partial | Existing CLI tests qualify; more scenario-based output validation can be added. |
| White-box Test | Yes | Workflow internals and branching logic | Implemented | Current unit tests cover many internals directly. |
| Gray-box Test | Yes | Install + adapter + workflow contracts | Partial | Suitable for multi-step scenario tests with known internal contracts. |
| Static Testing | Yes | Code review, validator, file structure, docs | Implemented / Partial | `validate_skill.py` exists; lint/type/security scans can still be added. |
| Dynamic Testing | Yes | All runtime scripts | Implemented | Main suite executes runtime logic. |
| Boundary Value Testing | Yes | CLI args, execution modes, target validation | Partial | Some invalid input tests exist; more coverage is possible. |
| Equivalence Partitioning | Yes | Versions, levels, agent targets, language variants | Partial | Covered for several core inputs; can expand to more combinations. |
| Decision Table Testing | Yes | `task_mode` + `execution_mode` + target availability | Planned | Good fit for future scenario matrix tests. |
| State Transition Testing | Partial | Execution/report lifecycle | Planned | Only worth adding if workflow state becomes more explicit. |
| Error Guessing | Yes | Invalid targets, missing files, duplicate findings, scanner failure | Implemented / Ongoing | Several error-path tests already exist. |
| Exploratory Testing | Yes | Installed skill behavior on real pages | Planned | Manual practice still valuable. |
| Scenario Test | Yes | Real-world create/modify workflows | Partial | Some workflow cases exist; richer scenario fixtures still needed. |
| Data-Driven Test | Yes | Same workflow with multiple WCAG versions/levels/languages | Partial | Parameterized loops exist; can be expanded. |
| Parameterized Test | Yes | Versions, levels, execution modes, agents | Partial | Current tests use loops; formal parameterization can expand later. |
| API Test | No | N/A | Not Applicable | The repo does not expose an API service. |
| UI Test | No | N/A | Not Applicable | The repo does not ship a UI application. |
| Compatibility Test | Yes | Different agents, OS/script entry points | Partial | PowerShell/sh/Python installer support exists; deeper environment checks can expand. |
| Cross-browser Test | No | N/A | Not Applicable | No browser UI is shipped. |
| Responsive Test | No | N/A | Not Applicable | No responsive UI is shipped. |
| Usability Test | Yes | Installation instructions and invocation flow | Planned | Manual review or user trial needed. |
| Accessibility Test | Yes | HTML fixture scanning and report output | Partial | Core purpose of repo; sample fixture coverage should grow further. |
| Performance Test | Partial | Workflow speed and scanner overhead | Planned | Not critical yet, but useful later. |
| Load Test | No | N/A | Not Applicable | No service endpoint to load. |
| Stress Test | Partial | Large fixture sets / scanner timeouts | Planned | Could be relevant for bulk auditing workflows. |
| Spike Test | No | N/A | Not Applicable | No service endpoint to spike. |
| Endurance / Soak Test | Partial | Long-running scan batches | Planned | Only relevant if batch processing grows. |
| Volume / Capacity Test | Partial | Large report / many fixtures | Planned | Useful once sample corpus grows. |
| Scalability Test | Partial | Batch audit workflows | Planned | Future concern, not immediate. |
| Security Test | Yes | CLI input boundaries, install path handling | Partial | Target validation exists; more explicit security checks can be added. |
| Vulnerability Scan | Yes | Dependencies and scripts | Planned | Could be added with dependency/security tooling. |
| Penetration Test | No | N/A | Not Applicable | No exposed service to penetration test. |
| Authorization Test | No | N/A | Not Applicable | No auth/role system exists. |
| Authentication Test | No | N/A | Not Applicable | No login/authentication flow exists. |
| Recovery Test | Partial | Failed scan recovery and reinstall flows | Partial | Error handling exists; more explicit recovery scenarios can be added. |
| Failover Test | No | N/A | Not Applicable | No HA topology exists. |
| Backup/Restore Test | No | N/A | Not Applicable | No persisted data store exists. |
| Installation Test | Yes | `scripts/install-agent.py`, wrappers, manifest generation | Implemented / Partial | Core install flow is tested; wrappers can be covered further. |
| Upgrade Test | Yes | Reinstall with `--force`, future version migration | Partial | Force reinstall is covered conceptually; explicit upgrade scenarios can expand. |
| Configuration Test | Yes | Agent choice, destination override, force behavior, language | Partial | Some CLI config is covered; matrix can be expanded. |
| Localization Test | Yes | Markdown output language | Implemented / Partial | `zh-TW` and English summary/header output is covered; more strings can be added later. |
| Internationalization Test | Yes | Language fallback design | Partial | Basic fallback exists; broader locale coverage can expand. |
| Database Test | No | N/A | Not Applicable | No database exists. |
| DB Migration Test | No | N/A | Not Applicable | No database exists. |
| Interrupt Test | Partial | Mid-install overwrite / missing files / scanner failure | Partial | Some interruption-like cases are covered; abrupt process interruption is not. |
| Concurrency Test | Partial | Parallel installs to different destinations | Planned | Possible future enhancement. |
| Chaos Test | No | N/A | Not Applicable | No distributed runtime system exists. |

## Repo Mapping

### Core workflow and reporting

- `skills/libro-agent-wcag/scripts/wcag_workflow.py`
- `skills/libro-agent-wcag/scripts/normalize_report.py`
- `skills/libro-agent-wcag/scripts/run_accessibility_audit.py`
- Best-fit tests:
  - Unit Test
  - Component Test
  - Functional Test
  - Boundary Value Testing
  - Error Guessing
  - Localization Test
  - Accessibility Test

### Remediation strategy logic

- `skills/libro-agent-wcag/scripts/remediation_library.py`
- Best-fit tests:
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
- Best-fit tests:
  - Installation Test
  - Integration Test
  - Configuration Test
  - Recovery Test
  - Compatibility Test
  - Smoke Test

### Skill contract and adapters

- `skills/libro-agent-wcag/SKILL.md`
- `skills/libro-agent-wcag/agents/openai.yaml`
- `skills/libro-agent-wcag/adapters/*/prompt-template.md`
- Best-fit tests:
  - Module Test
  - Black-box Test
  - Gray-box Test
  - Regression Test

### References and framework guides

- `skills/libro-agent-wcag/references/core-spec.md`
- `skills/libro-agent-wcag/references/adapter-mapping.md`
- `skills/libro-agent-wcag/references/wcag-citations.md`
- `skills/libro-agent-wcag/references/framework-patterns-*.md`
- Best-fit tests:
  - Static Testing
  - Acceptance Test
  - Scenario Test

## Already Implemented

- Unit tests for workflow logic, rule mapping, severity mapping, citations, remediation strategy defaults, and edge cases.
- Integration-style CLI tests for:
  - `normalize_report.py`
  - `install-agent.py`
  - `doctor-agent.py`
  - `uninstall-agent.py`
- Root-level smoke coverage through repo discovery and validator execution.
- Regression coverage for:
  - dedup
  - multi-SC citations
  - WCAG 2.2 manual review fallback
  - execution mode/task mode semantics
  - install manifests and agent-specific adapter selection
- Static validation via `scripts/validate_skill.py`.

## Still Worth Adding

- More realistic HTML fixture integration tests that exercise actual scanner outputs end-to-end.
- End-to-end scenario tests for:
  - `create` mode with draft-only guidance
  - `modify` mode with real sample pages
  - `apply-fixes` workflows once actual rewriting exists
- Broader localization coverage beyond summary lines and headers.
- Formal decision-table tests for `task_mode` x `execution_mode` x target-availability combinations.
- Wrapper-script tests for `install-agent.ps1` and `install-agent.sh`.
- Upgrade tests that simulate replacing an older installed bundle with a newer one.
- Manual acceptance and exploratory checklists for real user workflows.

## Execution Commands

Run the current automated suite:

```powershell
python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-agent-wcag
```
