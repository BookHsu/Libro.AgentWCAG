# GA Release Workflow

Use this workflow when publishing a formal GitHub release for `Libro.AgentWCAG`.

## Trigger

- Automatic publish trigger: push a tag matching `v*`
- Manual trigger: `workflow_dispatch` on `.github/workflows/release.yml` with `release_tag`

## Pipeline Stages

1. `validate`
   - runs `python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"`
   - runs `python scripts/validate_skill.py skills/libro-agent-wcag --validate-policy-bundles`
2. `package-release`
   - exports `LIBRO_AGENTWCAG_SOURCE_REVISION=${GITHUB_SHA}`
   - exports `LIBRO_AGENTWCAG_BUILD_TIMESTAMP=<UTC ISO-8601>`
   - runs `python scripts/package-release.py --output-dir dist/release --overwrite`
   - uploads staged release assets with retention
3. `clean-release-smoke`
   - downloads staged release assets
   - runs `python scripts/run-release-adoption-smoke.py --release-dir dist/release --agent codex --summary-path dist/release/smoke-summary.json`
   - uploads smoke artifacts even on failure
4. `publish-release`
   - runs only after `package-release` and `clean-release-smoke` succeed
   - publishes all staged release assets as the GitHub Release payload

## Publish Gate

Publish is blocked unless:

- validate passes
- package-release passes
- clean-release-smoke passes
- release tag/version metadata resolves cleanly

No undocumented manual override is allowed to skip these gates.

## Release Metadata And Notes

- Release title format: `Libro.AgentWCAG <version>`
- Release body source: the matching version section in `CHANGELOG.md`
- Required release note sections:
  - highlights
  - breaking changes, when applicable
  - known limitations
  - install / verify commands
  - checksum verification guidance
- Hotfix releases follow the same structure and must explicitly identify the superseded version.

## Artifact Retention

- staged release assets: `14` days by default
- smoke artifacts: `14` days by default
- workflow dispatch can override retention days when needed for investigation

## Release Asset Set

The published asset set must include:

- `libro-agent-wcag-<version>-codex.zip`
- `libro-agent-wcag-<version>-claude.zip`
- `libro-agent-wcag-<version>-gemini.zip`
- `libro-agent-wcag-<version>-copilot.zip`
- `libro-agent-wcag-<version>-all-in-one.zip`
- `libro-agent-wcag-<version>-sha256sums.txt`
- `libro-agent-wcag-<version>-release-manifest.json`
- `latest-release.json`
- bootstrap/support assets emitted by packaging

## Operator Checklist

Before pushing a release tag:

- confirm `CHANGELOG.md` has the tested release notes
- confirm GA blockers are closed or explicitly deferred as non-blockers
- confirm rollback operator and approver are known
- confirm required branch protection still includes `libro-agent-wcag-real-scanner`
