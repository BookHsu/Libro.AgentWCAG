# Copilot Failure Guide

## When To Avoid Direct Changes

- Avoid direct changes when the target is a generated framework artifact.
- Avoid changes when the fix would alter component APIs or business logic.
- Treat unresolved ARIA relationships and contrast changes as guided remediation, not safe auto-fix.

## Recovery Steps

Use `apply-fixes` only when the target and rule set remain within safe workflow boundaries.

1. Keep the same issue IDs.
2. Return `manual_review_required=true` where appropriate.
3. Leave unsupported fixes in `planned` status with clear guidance.

## Downgrade And Escalation Example

- Downgrade: generated artifacts or non-deterministic template rewrites.
- Escalate: change requires API updates or design approval.
- Required note: set `downgrade_reason` and preserve manual review actions.
