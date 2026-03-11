# Adapter Mapping

## Goal

Translate platform prompt syntax while preserving the core contract.

## Required invariants

- Do not rename canonical JSON keys.
- Do not change Markdown column order.
- Do not change status vocabulary.
- Do not omit W3C citations for major findings/fixes.
- Treat `apply-fixes` as permission for the agent or adapter to modify files; the core scripts only express intent and reporting.
- Respect `task_mode`: `create` targets drafts/templates, `modify` targets existing pages that should be audited first.

## Platform mapping

### OpenAI/Codex adapter

- Use direct instruction blocks with explicit tool steps.
- Use the core input contract keys as-is.
- Output both Markdown and JSON in one response.
- Localize human-facing Markdown text based on `output_language` when possible.

### Claude adapter

- Use XML-like instruction delimiters if needed by client setup.
- Keep input/output contract fields unchanged.
- Keep the same finding IDs between Markdown and JSON.
- Preserve deduped findings instead of re-expanding tool-specific duplicates.

### Gemini adapter

- Use direct prompt instructions with the canonical JSON contract inline.
- Preserve `ok | skipped | error` tool status semantics.
- Require version-matched W3C Understanding URLs.
- Keep WCAG 2.2-only manual-review findings visible when automatic mapping is unavailable.

### Copilot adapter

- Use plain-language instructions with the canonical contract inline.
- Preserve canonical JSON keys and Markdown column order verbatim.
- Require stable issue IDs across Markdown and JSON.
- Treat `create` mode as draft guidance when no concrete existing target can be scanned.
