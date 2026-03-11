# Adapter Mapping

## Goal

Translate platform prompt syntax while preserving the core contract.

## Required invariants

- Do not rename canonical JSON keys.
- Do not change Markdown column order.
- Do not change status vocabulary.
- Do not omit W3C citations for major findings/fixes.
- Treat `apply-fixes` as permission for safe core local rewrites first, then agent or adapter-driven modification for anything unsupported.
- Respect `task_mode`: `create` targets drafts/templates, `modify` targets existing pages that should be audited first.
- Keep adapter-specific invocation examples in each `usage-example.md` file aligned with the prompt template.

## Platform mapping

### OpenAI/Codex adapter

- Use direct instruction blocks with explicit tool steps.
- Use the core input contract keys as-is.
- Output both Markdown and JSON in one response.
- Localize human-facing Markdown text based on `output_language` when possible.
- Keep `$libro-agent-wcag` invocation examples current in `adapters/openai-codex/usage-example.md`.

### Claude adapter

- Use XML-like instruction delimiters if needed by client setup.
- Keep input/output contract fields unchanged.
- Keep the same finding IDs between Markdown and JSON.
- Preserve deduped findings instead of re-expanding tool-specific duplicates.
- Keep project/system prompt examples current in `adapters/claude/usage-example.md`.

### Gemini adapter

- Use direct prompt instructions with the canonical JSON contract inline.
- Preserve `ok | skipped | error` tool status semantics.
- Require version-matched W3C Understanding URLs.
- Keep WCAG 2.2-only manual-review findings visible when automatic mapping is unavailable.
- Keep custom-instruction examples current in `adapters/gemini/usage-example.md`.

### Copilot adapter

- Use plain-language instructions with the canonical contract inline.
- Preserve canonical JSON keys and Markdown column order verbatim.
- Require stable issue IDs across Markdown and JSON.
- Treat `create` mode as draft guidance when no concrete existing target can be scanned.
- Keep instruction-file examples current in `adapters/copilot/usage-example.md`.
