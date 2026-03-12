# Release Notes Workflow

This workflow standardizes versioned updates for `libro-agent-wcag`.

## When to update

- Every release candidate and final release must update `CHANGELOG.md`.
- Patch releases must include at least one `Changed` or `Fixed` entry.

## Steps

1. Create a new version header in `CHANGELOG.md` using `## [X.Y.Z] - YYYY-MM-DD`.
2. Move validated items from `[Unreleased]` into that version section.
3. Group notes under these buckets when applicable:
   - `Added`
   - `Changed`
   - `Fixed`
   - `Removed`
4. Include known limitations that affect adoption or behavior.
5. Cross-check release notes against merged PRs and test outcomes.
6. Link the changelog section in the release announcement.

## Quality gate

A release is not publish-ready unless:

- The changelog has a dated version section.
- Notes reflect behavior that is already merged and validated.
- Breaking or operator-impacting changes are explicitly called out.
