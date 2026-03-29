# Markdown Cleanup Decision (2026-03-29)

This note records the repository markdown-convergence decisions that were previously staged in temporary automation planning files.

## Outcome

- Removed the temporary root documents `CLAUDE.md` and `SKILL-TODO.md`.
- Moved the root-level test matrix `TESTING-PLAN.md` to `docs/testing/test-matrix.md`.
- Removed the temporary `docs/automations/` directory after converging the remaining decisions into durable docs, tests, and changelog entries.

## Durable Rules

- Human-facing documentation lives in `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/README.md`, `docs/release/`, and `docs/testing/`.
- Skill contract and adapter markdown under `skills/` and workspace mirrors remain product assets, not general cleanup targets.
- Archive markdown under `docs/archive/` may remain for traceability, but should not be treated as current operator guidance or GitHub Pages source material.
- Test snapshots and sample reports remain test assets, not general documentation.

## GitHub Pages Source Boundaries

First-pass Pages-eligible sources:

- `README.md`
- `README.en.md`
- `SECURITY.md`
- `docs/README.md`
- `docs/release/release-playbook.md`
- `docs/release/apply-fixes-scope.md`
- `docs/release/apply-fixes-scope.en.md`
- `docs/release/supported-environments.md`
- `docs/release/adoption-smoke-guide.md`
- `docs/testing/testing-playbook.md`
- `docs/testing/test-matrix.md`

Explicit exclusions:

- `skills/`
- workspace skill mirrors under `.claude/`, `.codex/`, `.copilot/`, `.gemini/`
- `docs/archive/`
- sample reports and test snapshots
