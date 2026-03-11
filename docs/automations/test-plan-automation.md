# Test Development Automation Spec

Purpose: use Codex Automations to continuously develop missing tests for `Libro.AgentWCAG`, not merely maintain the testing plan.

## Primary Objective

On each automation run, identify the highest-value missing or weak test coverage in this repository and implement additional tests until every automatable applicable test type in `TESTING-PLAN.md` is backed by real test code.

The automation must prefer writing tests over writing documentation.

## Automation Mission

The automation is responsible for all of the following:

- keep `TESTING-PLAN.md` aligned with the repo
- detect missing or weak coverage
- implement new tests for automatable categories
- strengthen weak tests when only shallow coverage exists
- add fixtures, snapshots, harnesses, or support assets when needed
- use manual testing assets only for categories that cannot be honestly automated in-repo

## Recommended Codex Automation Trigger

Use this file with a Codex Automation configured on an automatic schedule.

Recommended schedule:

- Daily while the repo is evolving
- Weekly once the repo stabilizes

Recommended automation instruction:

> Read `docs/automations/test-plan-automation.md` and `docs/automations/test-plan-review-policy.md`. Inspect the repository, identify the highest-priority missing automated test coverage, implement the next increment of test development, update the testing plan to reflect actual coverage mode, run full validation, and prepare a reviewable change set without changing protected contract semantics.

## Success Definition

A run is successful only if it does at least one of the following:

- adds a new automated test for an automatable test type
- deepens an existing automated test from shallow to stronger coverage
- replaces a temporary manual-only placeholder with real automated coverage
- updates the matrix to reflect the newly completed automation work

A run is not successful if it only rewrites documentation while automatable gaps still exist.

## Coverage Policy

Classify each applicable test type using one of these coverage modes:

- `Automated`
- `Static Contract`
- `Scripted Manual`

Use these rules:

1. If a test type is realistically automatable inside this repo, the target coverage mode is `Automated`.
2. If the artifact is metadata, prompt templates, wrappers, or documentation, `Static Contract` is valid.
3. Use `Scripted Manual` only when the test type inherently requires human evaluation or external users.

## Automation Targets

The following applicable test types are automation targets and should be pushed toward real test code:

- Unit Test
- Component Test
- Module Test
- Integration Test
- System Test
- End-to-End Test
- Functional Test
- Smoke Test
- Sanity Test
- Regression Test
- Black-box Test
- White-box Test
- Gray-box Test
- Static Testing
- Dynamic Testing
- Boundary Value Testing
- Equivalence Partitioning
- Decision Table Testing
- State Transition Testing
- Error Guessing
- Scenario Test
- Data-Driven Test
- Parameterized Test
- Compatibility Test
- Accessibility Test
- Performance Test
- Stress Test
- Endurance / Soak Test
- Volume / Capacity Test
- Scalability Test
- Security Test
- Vulnerability Scan where realistic for local tooling
- Recovery Test
- Installation Test
- Upgrade Test
- Configuration Test
- Localization Test
- Internationalization Test
- Interrupt Test
- Concurrency Test

## Manual-Only Categories

The following applicable categories may remain `Scripted Manual` unless the repo later gains a realistic automation path:

- Acceptance Test / UAT
- Alpha Test
- Beta Test
- Usability Test
- Exploratory Testing

## Scope

The automation may inspect and modify:

- `TESTING-PLAN.md`
- `docs/testing/*`
- `skills/libro-agent-wcag/scripts/tests/*`
- `.github/workflows/test.yml`
- `README.md` when testing or validation instructions change
- test fixtures, snapshots, or helper assets created under a test-owned path

The automation may inspect but should not freely rewrite unless required to make valid tests possible:

- `skills/libro-agent-wcag/scripts/*`
- `scripts/*`
- `skills/libro-agent-wcag/SKILL.md`
- `skills/libro-agent-wcag/references/*`
- `skills/libro-agent-wcag/adapters/*`
- `skills/libro-agent-wcag/agents/openai.yaml`

## Protected Files and Semantics

Do not modify these unless explicitly requested by a human reviewer:

- `LICENSE`
- canonical JSON key names in the core contract
- Markdown report column order
- supported adapter names
- skill name `libro-agent-wcag`
- repo/product name `Libro.AgentWCAG`

Do not change business semantics just to satisfy tests.

## Required Run Sequence

1. Inspect the repo file tree excluding `.git` and `__pycache__`.
2. Read:
   - `TESTING-PLAN.md`
   - `README.md`
   - `docs/testing/*`
   - `skills/libro-agent-wcag/scripts/tests/*`
3. Detect new, renamed, or removed non-test files.
4. Detect applicable matrix rows that are still weakly covered or only documented.
5. Select the next highest-value automatable gap.
6. Implement tests, fixtures, or helper assets for that gap.
7. Update static/manual assets only when the gap is truly non-automatable.
8. Update `TESTING-PLAN.md` so that `Current Status` and `Coverage Mode` match reality.
9. Update `README.md` only if validation or testing guidance changed.
10. Run validation commands.
11. Summarize exactly what test-development work was completed.

## Prioritization Rules

Use this priority order when choosing the next gap:

1. missing automated coverage for high-value executable paths
2. weak CLI and integration coverage
3. missing scenario, decision-table, and state-transition coverage
4. missing resilience, recovery, interrupt, or concurrency coverage
5. missing performance, stress, endurance, or volume coverage
6. static/manual asset cleanup

## Coverage Rules

When coverage is missing, use this order of preference:

1. Add an automated test if the behavior is deterministic and local.
2. Add a static contract check if the target is documentation, metadata, or a wrapper script.
3. Add or update a scripted manual asset only when the category is not meaningfully automatable in-repo.

Examples:

- Python logic: add `unittest`
- CLI flow: add subprocess-based test
- file/contract integrity: add static assertions
- scenario or system flow: add fixture-backed integration tests
- UAT/Beta/Usability: keep scripted manual assets in `docs/testing/`

## Required Validation Commands

Run all of these after changes:

```powershell
python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-agent-wcag
```

If a change touches installation guidance or wrappers, also verify relevant installer flows with temporary destinations.

## Expected Output From Each Automation Run

The automation output must include:

- which automatable gap was selected
- files changed
- test types added or strengthened
- whether `TESTING-PLAN.md` changed
- validation command results
- remaining automatable gaps, if any

## Completion Criteria

A run is complete only if all of the following are true:

- automated tests pass
- `validate_skill.py` passes
- `TESTING-PLAN.md` matches the current repo coverage state
- no protected semantics were changed
- at least one meaningful increment of test development was completed unless no automatable gap remains
- any remaining non-automated category is explicitly justified as `Scripted Manual`

## Refusal Conditions

Do not auto-merge or silently commit changes that:

- alter protected contract semantics
- remove existing coverage without replacement
- downgrade an automatable category from automated coverage to manual-only coverage
- claim a category is complete when only documentation was added but real test code is still feasible
- introduce external dependencies without a strong reason and corresponding test updates
