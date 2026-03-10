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

### Gemini/Copilot placeholders (v2)

- Keep directories and template stubs present.
- Do not implement platform-specific logic in v1.

