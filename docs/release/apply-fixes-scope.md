# Apply-Fixes Scope (M16)

This document defines the productionized `apply-fixes` boundary used by
`skills/libro-wcag/scripts/run_accessibility_audit.py` and
`skills/libro-wcag/scripts/auto_fix.py`.

## Behavior Audit (2026-03-12)

- `execution_mode=apply-fixes` only attempts core rewrites when `target` resolves to an existing local file path.
- Supported local file types are limited to: `.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, `.vue`.
- Unsupported local file types and non-local targets are always skipped by core rewrites and logged in `run_meta.notes`.
- When no rewrite is applied, stale `wcag-fixes.diff` and `wcag-fixed-report.snapshot.json` artifacts are removed to keep repeated runs stable.

## Scope Matrix

| Rule Family | Rule IDs | File Types | Safety Level | Core Behavior |
| --- | --- | --- | --- | --- |
| Language semantics | `html-has-lang`, `html-lang-valid`, `html-xml-lang-mismatch`, `valid-lang` | `.html`, `.htm`, `.xhtml`, `.tsx` (Next.js layout), `.jsx`, `.vue` | low-risk deterministic | auto-fix in core workflow |
| Alternative text | `image-alt`, `input-image-alt`, `area-alt` | `.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, `.vue` | low-risk deterministic | auto-fix in core workflow |
| Accessible names | `button-name`, `link-name`, `label`, `select-name`, `aria-toggle-field-name`, `aria-tooltip-name`, `aria-progressbar-name`, `aria-meter-name` | `.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, `.vue` | low-risk deterministic | auto-fix in core workflow |
| ARIA validity | `aria-required-attr`, `aria-valid-attr-value` | `.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, `.vue` | low-risk deterministic | auto-fix in core workflow |
| Document/structure | `document-title`, `list`, `listitem`, `table-fake-caption`, `td-has-header`, `th-has-data-cells` | `.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, `.vue` | low-risk deterministic | auto-fix in core workflow |
| Timing/viewport | `meta-refresh`, `meta-viewport` | `.html`, `.htm`, `.xhtml` | low-risk deterministic | auto-fix in core workflow |

## Intentionally Not Auto-Fixed

These classes remain outside core `apply-fixes` and are expected to be handled as `suggest-only` or assisted/manual remediation:

- Assisted-only rule classes: structural/interaction refactors such as `heading-order`, `region`, `skip-link`, `tabindex`, `presentation-role-conflict`, `nested-interactive`, `duplicate-id-aria`.
- Manual-review classes: WCAG 2.2 manual checks (`wcag22-manual-*`) and scanner/tool failure fallback findings.
- Unsupported target classes: non-local targets, local files outside the supported extension list, and high-risk transformations requiring project-specific intent.

## Contract Expectations

- `run_meta.files_modified=true` and `run_meta.modification_owner=core-workflow` only when a supported local target is rewritten.
- `run_meta.diff_artifacts[]` should contain generated diff artifacts only for runs with applied changes.
- Findings and fixes that are not auto-fixed must keep canonical downgrade metadata (`downgrade_reason`, `fix_blockers`, and manual review flags).
