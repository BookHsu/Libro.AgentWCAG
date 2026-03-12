# Realistic Validation Notes

This note tracks known boundaries discovered from the realistic mixed validation sample.

## Known limitations

- The realistic smoke lane uses deterministic mock scanner payloads by default so outputs stay stable across environments.
- Manual-review findings in this lane are currently represented by WCAG 2.2 manual checks and assisted-only classes; they are not auto-verified by the core workflow.
- Rule mapping still depends on selector quality from scanner payloads; coarse selectors can reduce precision for per-node remediation messaging.

## False-positive boundaries

- `heading-order` and other structural checks may produce context-sensitive findings that still require human review after auto-fixes are applied.
- `link-name` on icon-only links can be auto-labeled safely, but content quality (whether label wording is semantically correct) remains a manual verification item.

## Manual-review expectations

- Treat `needs-review` findings as blocking for final sign-off even when `auto_fixed_count` is non-zero.
- Re-run audit on the post-fix target and manually inspect critical user journeys before accepting changes.
- Use real-scanner mode (`LIBRO_RUN_REAL_SCANNERS=1`) in environments with `npx @axe-core/cli` and `lighthouse` to validate scanner parity.
