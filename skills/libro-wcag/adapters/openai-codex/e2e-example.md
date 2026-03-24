# OpenAI/Codex End-to-End Example

## Scenario

Audit an existing `index.html`, apply safe first-pass fixes, then return both outputs.

## Invocation

```text
Use $libro-wcag with:
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

## Output Snapshot

```json
{
  "run_meta": {
    "task_mode": "modify",
    "execution_mode": "apply-fixes"
  },
  "summary": {
    "auto_fixed_count": 3,
    "manual_required_count": 1,
    "remediation_lifecycle": {
      "implemented": 3,
      "planned": 1,
      "manual_review_required": 1
    }
  }
}
```
