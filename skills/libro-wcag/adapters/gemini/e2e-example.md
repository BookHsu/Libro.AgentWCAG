# Gemini End-to-End Example

## Scenario

Load the adapter template into a custom instruction, run a WCAG 2.2 audit, and surface manual-review items.

## Invocation

```text
Follow the libro-wcag core contract exactly:
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

## Output Snapshot

```json
{
  "run_meta": {
    "task_mode": "modify",
    "execution_mode": "audit-only",
    "product": {
      "product_name": "Libro.AgentWCAG",
      "product_version": "1.2.1",
      "source_revision": "git:example",
      "report_schema_version": "1.0.0"
    }
  },
  "summary": {
    "auto_fixed_count": 0,
    "manual_required_count": 2,
    "remediation_lifecycle": {
      "implemented": 0,
      "verified": 0,
      "planned": 2,
      "manual_review_required": 2
    }
  }
}
```
