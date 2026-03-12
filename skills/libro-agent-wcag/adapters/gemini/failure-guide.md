# Gemini Failure Guide

## When To Downgrade Execution

- Downgrade from `apply-fixes` to `suggest-only` for unsupported rule families.
- Downgrade when the target is a framework component without reliable file-level rewrite support.
- Keep WCAG 2.2 manual-review findings visible when no direct scanner mapping exists.

## Recovery Steps

1. Report the downgrade in `run_meta.notes`.
2. Keep version-matched citations.
3. Return concrete remediation guidance instead of risky edits.

## Downgrade And Escalation Example

- Downgrade: unsupported rewrite operation or missing local file target.
- Escalate: remediation can alter interactive behavior across components.
- Required note: include `downgrade_reason` and list unresolved findings as manual.
