# Claude Failure Guide

## When To Fall Back

- Fall back to guidance when no concrete target exists in `create` mode.
- Fall back to manual review when scanner output is incomplete or unsupported.
- Do not rewrite files unless the workflow and user intent both allow `apply-fixes`.

## Recovery Steps

1. Keep the canonical contract unchanged.
2. Re-run in `suggest-only` when the target is remote or high-risk.
3. Preserve deduplicated findings and W3C citations in the follow-up output.
