# OpenAI/Codex Failure Guide

## When To Stop Auto-Fix

- Stop when the target is not a local HTML file.
- Stop when the finding requires layout, design, or product intent decisions.
- Stop when a rule is not listed as safe auto-fix in the core workflow.

## Recovery Steps

Use `apply-fixes` only when the target and rule set remain within safe workflow boundaries.


1. Re-run with `execution_mode: suggest-only` if a safe fix cannot be applied.
2. Preserve the JSON issue IDs and citations.
3. Ask the user to approve any higher-risk semantic or visual change.
