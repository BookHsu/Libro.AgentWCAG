# Adapter Mapping

## Goal

Translate platform prompt syntax while preserving the core contract.

## Required invariants

- Do not rename canonical JSON keys.
- Do not change Markdown column order.
- Do not change status vocabulary.
- Do not omit W3C citations for major findings/fixes.

## Platform mapping

### OpenAI/Codex adapter

- Use direct instruction blocks with explicit tool steps.
- Use the core input contract keys as-is.
- Output both Markdown and JSON in one response.

### Claude adapter

- Use XML-like instruction delimiters if needed by client setup.
- Keep input/output contract fields unchanged.
- Keep the same finding IDs between Markdown and JSON.

### Gemini adapter

- Use direct prompt instructions with the canonical JSON contract inline.
- Preserve `ok | skipped | error` tool status semantics.
- Require version-matched W3C Understanding URLs.

### Copilot adapter

- Use plain-language instructions with the canonical contract inline.
- Preserve canonical JSON keys and Markdown column order verbatim.
- Require stable issue IDs across Markdown and JSON.
