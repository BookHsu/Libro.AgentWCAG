# Copilot End-to-End Example

## Scenario

Use an instruction file to audit a draft page in `create` mode, then return guidance without pretending a scan exists.

## Invocation

```text
Use the libro-wcag shared contract:
{
  "task_mode": "create",
  "execution_mode": "suggest-only",
  "wcag_version": "2.1",
  "conformance_level": "AA",
  "target": "./draft/home.html",
  "output_language": "zh-TW"
}
```

## Expected Result

- If the file exists, scan it.
- If it does not exist yet, emit manual-review guidance instead of fake scanner claims.
- Return canonical Markdown and JSON outputs.

## Output Snapshot

```json
{
  "run_meta": {
    "task_mode": "create",
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
      "planned": 1,
      "manual_review_required": 1
    }
  }
}
```
