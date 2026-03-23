# Real-Scanner CI Lane

This guide defines the live real-scanner GitHub Actions lane used as the formal PR gate for scanner-backed validation.

## Workflow contract

- Workflow path: [`.github/workflows/libro-agent-wcag-real-scanner.yml`](../../.github/workflows/libro-agent-wcag-real-scanner.yml)
- Workflow name: `libro-agent-wcag-real-scanner`
- Job name: `libro-agent-wcag-real-scanner`
- Trigger events:
  - `pull_request`
  - `workflow_dispatch`
- Required check name for branch protection: `libro-agent-wcag-real-scanner`

This lane is live-only. It does not fall back to mock scanner payloads.

## Runtime policy

- Runner: `ubuntu-latest`
- Browser strategy: verify a supported Chrome/Chromium binary is available on the runner; do not install Chrome in the workflow
- Fixed scanner versions:
  - `@axe-core/cli@4.10.2`
  - `lighthouse@12.3.0`
- Fixed target:
  - `docs/testing/realistic-sample/mixed-findings.html`

## Fail-fast policy

The workflow fails immediately when any of the following happens:

- Python or Node.js setup fails
- fixed scanner toolchain installation fails
- browser availability verification fails
- scanner preflight fails
- `axe` execution fails
- `lighthouse` execution fails
- expected report artifacts are not produced
- artifact upload step fails

Mock payloads and deterministic fallback are not permitted in this PR gate.

## Artifact contract

Store lane evidence under `out/real-scanner`.

Always retain artifacts for `14` days.

Expected triage artifacts:

- raw logs:
  - `raw/python.version.log`
  - `raw/node.version.log`
  - `raw/axe.version.log`
  - `raw/lighthouse.version.log`
  - `raw/browser.version.log`
- preflight:
  - `preflight.json`
- normalized summary:
  - `normalized-summary.live.json`
- capability negotiation:
  - `capability-negotiation.json`
- normalized report outputs:
  - `live/wcag-report.json`
  - `live/wcag-report.md`
  - `live/wcag-report.sarif`
  - `live/artifact-manifest.json`

The uploaded GitHub artifact name is `libro-agent-wcag-real-scanner-artifacts`.

## Capability negotiation artifact

`capability-negotiation.json` acts as the handoff index and must include:

- `lane_mode`
- `scanners_available`
- `required_check`
- `target`
- `summary_artifacts`
- `report_artifacts`
- `raw_scanner_logs`

## Triage handoff

When opening a triage item, include:

1. `capability-negotiation.json`
2. `normalized-summary.live.json`
3. `live/wcag-report.json`
4. `live/wcag-report.sarif`
5. any raw version/browser logs needed for runtime diagnosis

This keeps PR review and local reproduction aligned.
