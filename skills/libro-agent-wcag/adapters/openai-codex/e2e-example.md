# OpenAI/Codex End-to-End Example

## Scenario

Audit an existing `index.html`, apply safe first-pass fixes, then return both outputs.

## Invocation

```text
Use $libro-agent-wcag with:
{
  "task_mode": "modify",
  "execution_mode": "apply-fixes",
  "wcag_version": "2.2",
  "conformance_level": "AA",
  "target": "./index.html",
  "output_language": "zh-TW"
}
```

## Expected Result

- Core workflow may emit `wcag-fixes.diff`.
- JSON includes canonical `fixability`, `verification_status`, and `diff_summary` fields.
- Any unsupported fixes remain planned for the agent to handle explicitly.
