# GA Definition

Use this document to decide whether `Libro.AgentWCAG` is ready for general availability.

## Product Scope

- Cross-agent WCAG skill payload for Codex, Claude, Gemini, and Copilot.
- Repo-native installer, doctor, uninstall, release packaging, and release-consumer bootstrap paths.
- Machine-readable audit outputs (`json`, `markdown`, `sarif`, `artifact-manifest.json`) with stable schema/version contracts.

## Intended User

- Maintainers shipping the skill as a release asset.
- Downstream adopters installing the packaged skill through bootstrap installers or repo-native installers.
- CI owners integrating accessibility audits and release smoke validation into delivery pipelines.

## Supported Environments

- Python `3.12+`
- Node.js active LTS (`18+`)
- Windows PowerShell and POSIX shell release-consumer flows
- Runtime/tooling details remain anchored in `docs/release/supported-environments.md`

## Support Boundaries

- Supported:
  - install -> doctor -> audit -> uninstall through documented scripts
  - packaged release bundles and checksum verification
  - current adapters and documented entrypoints
- Non-goals:
  - hidden/manual release steps outside documented workflow
  - direct mutation of published tags or published release assets
  - undocumented bootstrap behavior or compatibility promises

## GA Quality Gates

A GA release is allowed only when all blocker gates pass:

- `release.yml` validate job passes automated tests and skill validation
- release packaging succeeds from the repo root
- clean release smoke succeeds from packaged assets
- release notes and changelog match tested behavior
- rollback steps are available to an operator who is not the original author

## Blocker Policy

- Blocker:
  - failed automated tests
  - failed package generation
  - failed checksum verification
  - failed clean release smoke
  - schema/CLI contract drift without explicit versioned documentation
- Non-blocker:
  - documentation polish that does not change behavior
  - additive troubleshooting notes
  - optional examples that do not affect release assets

## Compatibility Promises

- Existing CLI flags, exit codes, artifact filenames, and report schema version remain stable unless explicitly versioned and documented.
- The pushed Git tag `vX.Y.Z` remains the single source of release version for published artifacts.
- `install-manifest.json`, `artifact-manifest.json`, and report schema versioning must remain machine-readable and backward-compatible within the same release line.
- Adapter entrypoint paths documented in installer manifests are part of the release contract.

## Versioning Policy

- Semantic versioning is the release policy baseline.
- Tag format is `vX.Y.Z`.
- Deprecation and compatibility changes are communicated only through formal release versions, `CHANGELOG.md`, and release notes; there is no separate pre-announcement window.
- Breaking changes require:
  - a semver-major bump
  - explicit changelog callout
  - updated GA/release workflow documentation

## Known Limitations Acceptance

- Known limitations may ship only if they do not break the release, install, doctor, audit, or uninstall path for supported environments.
- Any accepted limitation must be recorded in `CHANGELOG.md` or release notes when it materially affects adopters.
