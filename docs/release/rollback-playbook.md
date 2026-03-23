# Rollback Playbook

Use this playbook when a published `Libro.AgentWCAG` release must be withdrawn or superseded.

## Rollback Triggers

- release assets are corrupt or checksum verification fails
- bootstrap installer cannot install a supported agent
- clean release smoke fails after publish
- documented CLI/report contract was broken in the published release
- schema compatibility regression blocks downstream automation

## Owners And Approval

- rollback owner: current release operator
- required approver: one maintainer other than the release operator
- post-rollback communication owner: release operator unless reassigned

## Hard Rules

- Never rewrite or force-move an existing published tag.
- Never replace files inside an existing published release with different bytes under the same tag.
- Never bypass checksum verification to “hot patch” a release.

## Allowed Recovery Actions

- mark the release as withdrawn/yanked in GitHub release notes
- publish a newer corrective hotfix release with a new tag
- communicate the rollback window, impact, and safe version to adopters

## Hotfix Policy

- hotfix tags use the next semver patch release, for example `v0.1.1`
- hotfix must rerun the same validate -> package -> clean smoke -> publish chain
- release notes must explicitly reference the replaced version and the failure reason
- hotfix release title still uses `Libro.AgentWCAG <version>`

## Rollback Procedure

1. Freeze additional publish attempts for the affected version.
2. Confirm the failure mode with retained smoke/package artifacts.
3. Update the GitHub Release body to mark the version as withdrawn and unsafe for new installs.
4. Notify adopters of the affected version, failure mode, and recommended replacement version.
5. Prepare and publish a corrective release under a new tag.
6. Record a postmortem with root cause, missed gate, and corrective action.

## Communication Template

- Affected version:
- Trigger:
- User impact:
- Safe replacement version:
- Immediate adopter action:
- Follow-up postmortem link:
