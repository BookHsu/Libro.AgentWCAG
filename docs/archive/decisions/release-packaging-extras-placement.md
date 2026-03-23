# Release Packaging Extras Placement Decision

## Decision

Release packaging extras remain in this repository under `docs/release/` and `.github/ISSUE_TEMPLATE/`.

## Why this choice

- The extras depend on the same scripts and contract definitions shipped in this repo.
- Co-location reduces drift between workflow behavior and release guidance.
- Contributors can update implementation and packaging guidance in one pull request.

## Scope included now

- Demo package walkthrough (`demo-package-walkthrough.md`)
- Reusable prompt/invocation templates (`prompt-invocation-templates.md`)
- Troubleshooting intake docs (`troubleshooting-intake.md`)
- Issue templates for install failures and remediation mismatches

## Re-evaluate criteria

Move extras to a companion examples repo only if one of these becomes true:

1. Demo assets become significantly larger than documentation-only content.
2. We need independent versioning cadence for examples vs core skill.
3. Cross-repo consumers require language/framework-specific packs not suitable for this core repo.
