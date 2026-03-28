# Claude End-to-End Example

## Scenario

Attach the adapter template to a project prompt, audit an existing page, and return canonical Markdown and JSON.

## Invocation

```text
Invoke libro-wcag core contract with:
{
  "task_mode": "modify",
  "execution_mode": "suggest-only",
  "wcag_version": "2.1",
  "conformance_level": "AA",
  "target": "./checkout.html",
  "output_language": "en"
}
```

## Expected Result

- One deduplicated finding per rule/target pair.
- Matching issue IDs across Markdown and JSON.
- Suggested fixes remain `planned` when no safe auto-fix runs.

## Output Snapshot

```json
{
  "run_meta": {
    "task_mode": "modify",
    "execution_mode": "suggest-only",
    "product": {
      "product_name": "Libro.AgentWCAG",
      "product_version": "1.2.1",
      "source_revision": "git:example",
      "report_schema_version": "1.0.0"
    }
  },
  "summary": {
    "auto_fixed_count": 0,
    "manual_required_count": 1,
    "remediation_lifecycle": {
      "implemented": 0,
      "verified": 0,
      "planned": 2,
      "manual_review_required": 1
    }
  }
}
```
