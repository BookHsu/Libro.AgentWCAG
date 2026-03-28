# Docs Index

This directory is organized by operational purpose so the project is easier to read and maintain.

## Start Here

- `../README.md`: product overview, install, usage, validation, and release links
- `../TESTING-PLAN.md`: test matrix and coverage mapping
- `../CONTRIBUTING.md`: contribution workflow, contract guardrails, and review expectations
- `../SECURITY.md`: vulnerability reporting and security scope

## Sections

### `automations/`

Automation specs, review policies, and generated todo inventories used by Codex-driven repository maintenance.

- `automations/todo.md`: rolling backlog for automation-assisted repository work
- `automations/20260328_todo.md`: point-in-time automation worklist with resolved false-positive tracking
- `automations/test-plan-automation.md`: automation design for test planning
- `automations/test-plan-review-policy.md`: review rules for automation-generated plans

### `policy-bundles/`

Versioned rule-policy bundles used by the CLI, MCP entrypoints, and release validation.

- `policy-bundles/strict-web-app.json`
- `policy-bundles/legacy-content.json`
- `policy-bundles/marketing-site.json`

### `release/`

Normative release, CI, environment, policy, and operator guidance.

- `release/release-playbook.md`: primary release procedure
- `release/ga-release-workflow.md`: GitHub Actions release flow and responsibilities
- `release/adoption-smoke-guide.md`: consumer smoke checks after packaging or installation
- `release/apply-fixes-scope.md`: what `apply-fixes` may and may not rewrite
- `release/baseline-governance.md`: baseline, debt, and waiver governance
- `release/advanced-ci-gates.md`: policy bundle, fail-on, and CI enforcement patterns
- `release/real-scanner-ci-lane.md`: real-scanner lane expectations and artifacts
- `release/prompt-invocation-templates.md`: reusable invocation patterns for agents and operators
- `release/supported-environments.md`: supported operating systems and runtime assumptions
- `release/ga-definition.md`: GA scope and support boundaries
- `release/resilient-run-patterns.md`: retry and error recovery for CLI runs
- `release/repo-admin-setup.md`: GitHub Actions and npm publishing config
- `release/rollback-playbook.md`: rollback rules and recovery procedures
- `release/release-note-template.md`: template for standard releases
- `release/hotfix-release-note-template.md`: template for hotfix releases

### `testing/`

Testing guidance, playbooks, and realistic sample assets for regression work.

- `testing/testing-playbook.md`: test strategy and validation commands
- `testing/realistic-sample/`: sample target, fixture artifacts, and known limitations used in smoke validation

### `examples/`

Example assets that illustrate integration patterns but are not the primary source of truth.

- `examples/claude/`: Claude settings and MCP examples
- `examples/copilot/`: Copilot MCP configuration examples for VS Code-style `servers` documents
- `examples/gemini/`: Gemini MCP configuration examples using `mcpServers`
- `examples/ci/`: reusable CI examples including install and release-download flows

### `archive/`

Historical records retained for traceability.

- `archive/testing/`: historical test plans and manual checklists
- `archive/decisions/`: superseded design decisions and packaging notes
