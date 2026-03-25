# GA Release Workflow

Use this workflow when publishing a formal GitHub release for `Libro.AgentWCAG`.

## Trigger

- Automatic publish trigger: push a tag matching `v*`
- `release.yml` publishes GitHub release assets for the tag
- `publish-npm.yml` publishes `librowcag-cli` to npm for the same tag

## Version Bump Flow

1. Validate release assets and clean smoke locally when needed.
2. Create and push tag `vX.Y.Z`.
3. Let `release.yml` derive `X.Y.Z` from the tag, run `scripts/apply-release-version.py`, then perform validate -> package -> smoke -> GitHub Release publish.
4. Let `publish-npm.yml` derive the same `X.Y.Z` from the tag, run `scripts/apply-release-version.py`, and publish `librowcag-cli` to npm using OIDC trusted publishing.
5. GitHub release notes are auto-generated at publish time and do not drive the version number.

## Pipeline Stages

1. `validate`
   - runs `python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"`
   - runs `python scripts/validate_skill.py skills/libro-wcag --validate-policy-bundles`
2. `package-release`
   - resolves `release_version=${GITHUB_REF_NAME#v}`
   - runs `python scripts/apply-release-version.py --version <release_version>`
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
5. `publish-npm.yml`
   - resolves `release_version=${GITHUB_REF_NAME#v}`
   - runs `python scripts/apply-release-version.py --version <release_version>`
   - uses GitHub Actions OIDC / npm trusted publishing rather than a stored `NPM_TOKEN`
   - publishes `librowcag-cli` to npm with `npm publish --access public`

## Post-Publish Verification

Every release must perform one post-publish verification pass:

1. download the published assets from GitHub Release
2. verify `sha256sums.txt`
3. run `install-latest.ps1` or `install-latest.sh`
4. confirm installer-triggered doctor verification succeeds
5. run a first audit
6. uninstall cleanly

## Publish Gate

Publish is blocked unless:

- validate passes
- package-release passes
- clean-release-smoke passes
- release tag/version metadata resolves cleanly
- npm trusted publishing remains bound to the workflow filename configured on npmjs.com

No undocumented manual override is allowed to skip these gates.

## Release Metadata And Notes

- Release title format: `Libro.AgentWCAG <version>`
- Release body source: GitHub auto-generated release notes
- Required release note sections:
  - highlights
  - breaking changes, when applicable
  - known limitations
  - install / verify commands
  - checksum verification guidance
- Use `docs/release/release-note-template.md` for standard release guidance.
- Use `docs/release/hotfix-release-note-template.md` for hotfix guidance.
- Hotfix releases follow the same structure and must explicitly identify the superseded version.

## Artifact Retention

- staged release assets: `14` days by default
- smoke artifacts: `14` days by default
- workflow dispatch can override retention days when needed for investigation

## Release Asset Set

The published asset set must include:

- `libro-wcag-<version>-codex.zip`
- `libro-wcag-<version>-claude.zip`
- `libro-wcag-<version>-gemini.zip`
- `libro-wcag-<version>-copilot.zip`
- `libro-wcag-<version>-all-in-one.zip`
- `libro-wcag-<version>-sha256sums.txt`
- `libro-wcag-<version>-release-manifest.json`
- `latest-release.json`
- bootstrap/support assets emitted by packaging

## Operator Checklist

Before pushing a release tag:

- confirm GA blockers are closed or explicitly deferred as non-blockers
- confirm rollback operator and approver are known
- confirm required branch protection still includes `libro-wcag-real-scanner`
- confirm npm trusted publisher still points at the workflow filename currently responsible for `npm publish`
