# Gemini End-to-End Example

## Scenario

Load the adapter template into a custom instruction, run a WCAG 2.2 audit, and surface manual-review items.

## Invocation

```text
Follow the libro-agent-wcag core contract exactly:
{
  "task_mode": "modify",
  "execution_mode": "audit-only",
  "wcag_version": "2.2",
  "conformance_level": "AAA",
  "target": "./account.html",
  "output_language": "en"
}
```

## Expected Result

- Scanner findings plus WCAG 2.2 manual-review placeholders.
- No file edits.
- Canonical report fields preserved.
