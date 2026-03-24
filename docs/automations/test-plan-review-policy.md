# Test Development Automation Review Policy

This file defines how automation-generated test-development changes should be reviewed before acceptance.

## Review Goal

Accept automation output only when it meaningfully increases real test coverage or preserves already-earned coverage without weakening the repo contract.

## Reviewer Checklist

Check the following in order:

1. Scope control
- Changes stay within allowed automation scope or have a clear justification.
- Protected files and semantics were not modified unexpectedly.
- The automation stayed inside the testing lane.

2. Test-development progress
- The run added or strengthened actual test code for an automatable category, unless no automatable gap remained.
- The automation did not stop at documentation-only changes when real tests were still feasible.
- The automation did not take ownership of product feature development.

3. Matrix integrity
- `TESTING-PLAN.md` reflects the actual repo state.
- Each applicable row declares an honest coverage mode.
- Automatable categories are not left as `Scripted Manual` without a strong technical reason.

4. Test quality
- New tests are specific, deterministic, and readable.
- Static contract checks are meaningful and not superficial string padding.
- Manual assets are used only for inherently human-evaluated categories.

5. Validation quality
- `python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"` passed.
- `python scripts/validate_skill.py skills/libro-wcag` passed.
- If installation flows changed, installer and doctor flows were exercised.

6. Safety
- No contract semantics changed just to satisfy tests.
- No hidden dependency or environment assumption was introduced.
- No unrelated repo areas were rewritten.
- No feature-development change was bundled into the testing iteration beyond the minimum test-enabling edit.

## When To Reject Or Send Back

Reject or request revision if any of these occur:

- `TESTING-PLAN.md` claims automated coverage that is not backed by test code
- the automation added only documentation while automatable gaps still exist
- tests are flaky, environment-coupled, or meaningless
- automation changed `LICENSE`, skill identity, adapter naming, or canonical output semantics
- new files were added without updating the file-to-coverage relationship
- the automation summary does not explain remaining automatable gaps or why a manual fallback is necessary
- the automation took ownership of feature development instead of staying in the testing lane

## Preferred Change Pattern

Good automation changes usually look like this:

- one or more new tests, fixtures, snapshots, or harnesses
- optional updates to `docs/testing/*` only when required
- a targeted `TESTING-PLAN.md` update
- no unrelated business-logic changes

## Escalation Rules

Escalate to human review before acceptance when:

- the automation wants to change the core contract
- the automation wants to add new dependencies
- the automation proposes deleting tests or coverage assets
- the automation touches adapter semantics or installation destinations
- the automation concludes a category must remain manual-only for a non-obvious reason
- the automation needs a non-trivial feature change to make a test possible

## Review Queue Summary Template

Use this summary structure when reviewing automation output:

- Objective addressed
- Automatable gap selected
- Files changed
- Test types added or strengthened
- Validation results
- Remaining gaps or blocked areas
