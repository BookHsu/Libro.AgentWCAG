---
name: libro-agent-wcag
description: Vendor-neutral WCAG workflow for creating new web pages or remediating existing pages with selectable WCAG model (2.0/2.1/2.2 and A/AA/AAA). Use when any AI agent must perform consistent accessibility audit/remediation, produce aligned Markdown+JSON outputs, and attach W3C official citations.
---

# Libro.AgentWCAG

Use this skill as a cross-agent accessibility contract. Keep business logic in the core spec and only adapt prompt syntax per platform adapter.

## Required Input Contract

Collect or infer this contract before doing work:

```json
{
  "task_mode": "create | modify",
  "execution_mode": "audit-only | suggest-only | apply-fixes",
  "wcag_version": "2.0 | 2.1 | 2.2",
  "conformance_level": "A | AA | AAA",
  "target": "local file path or URL",
  "output_language": "BCP-47, default zh-TW"
}
```

Apply defaults when omitted:
- `execution_mode`: `suggest-only`
- `wcag_version`: `2.1`
- `conformance_level`: `AA`
- `output_language`: `zh-TW`

Treat local file paths as first-class inputs. The audit runner converts existing local paths to `file://` URLs before invoking scanners.

## Fixed Workflow

1. Lock the selected WCAG model and note defaults used.
2. Run automated checks with both axe and Lighthouse via `scripts/run_accessibility_audit.py`.
3. Rank findings by severity and impact, then map each item to WCAG SC.
4. Respect `execution_mode`:
   - `audit-only`: find issues only
   - `suggest-only`: find issues and propose remediation steps without editing
   - `apply-fixes`: apply safe first-pass remediations for supported local targets (`.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, `.vue`), then let the agent or adapter handle any remaining changes
5. Produce the two required outputs:
   - Markdown comparison table
   - JSON structured report
6. Attach W3C official citations for all major findings/fixes.

Interpret `task_mode` as follows:
- `create`: work on a draft, generated page, or template before release. If no concrete page exists yet, fall back to guidance and manual review rather than pretending a scan was executed.
- `modify`: audit an existing target first, then propose or apply changes based on `execution_mode`.

## Output Contract

Keep field semantics unchanged across adapters.

Markdown columns:

`Issue ID | Source | WCAG Version | Level | SC | Current | Fix | Changed Target | Citation | Status`

JSON top-level keys:

`run_meta`, `target`, `standard`, `findings[]`, `fixes[]`, `citations[]`, `summary`

Key remediation fields to preserve:
- `findings[].fixability`
- `findings[].verification_status`
- `findings[].manual_review_required`
- `fixes[].fixability`
- `fixes[].verification_status`
- `summary.diff_summary[]`
- `summary.remediation_lifecycle`
- `run_meta.diff_artifacts[]`

Report the chosen `execution_mode` in both JSON and Markdown summary text.
For `apply-fixes`, the core scripts may modify supported local targets, emit diff artifacts, and mark `files_modified=true`; unsupported target types plus assisted/manual-only remediation classes still fall back to agent or adapter-driven remediation.

Use `scripts/normalize_report.py` to normalize mixed tool outputs into the contract.

## Adapter Rules

- Use `adapters/openai-codex/prompt-template.md` for OpenAI/Codex orchestration.
- Use `adapters/claude/prompt-template.md` for Claude orchestration.
- Use `adapters/gemini/prompt-template.md` for Gemini orchestration.
- Use `adapters/copilot/prompt-template.md` for Copilot orchestration.
- Use each adapter's `usage-example.md` for install and invocation examples.
- Use each adapter's `failure-guide.md` for downgrade and recovery behavior.
- Use each adapter's `e2e-example.md` for platform-specific end-to-end invocation patterns.
- Never add adapter-specific business logic that alters core output semantics.

## References

- Load `references/core-spec.md` for strict field definitions and process details.
- Load `references/wcag-citations.md` for official W3C citation mapping.
- Load `references/adapter-mapping.md` for cross-agent translation rules.
- Load `references/framework-patterns-react.md` when the target is React or Next.js JSX.
- Load `references/framework-patterns-vue.md` when the target is Vue or Nuxt.
- Load `references/framework-patterns-nextjs.md` when the target is specifically Next.js routing/layout output.

## Remediation Support

Use `scripts/remediation_library.py` as the shared strategy library for common fixes. It provides remediation summary text, priority, confidence, auto-fix support flags, and framework hints for the most common accessibility rules.

Use `scripts/auto_fix.py` for safe first-pass local HTML rewrites. It currently supports a focused set of rules such as missing `lang`, `xml:lang` mismatches, invalid language-of-parts values, missing `alt` text on images, image inputs, and image map areas, missing button names, missing link names, ARIA widget names, simple form control labels, document titles, list semantics (`list` and `listitem`), table caption normalization (`table-fake-caption`), automatic meta refresh removal, and unsafe viewport settings, and emits a unified diff for verification.

Use `scripts/rewrite_helpers.py` for reusable HTML/CSS/JS text rewrite helpers and keep those helpers covered by unit tests when extending auto-fix behavior.

