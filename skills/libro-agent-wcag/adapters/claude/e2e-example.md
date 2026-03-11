# Claude End-to-End Example

## Scenario

Attach the adapter template to a project prompt, audit an existing page, and return canonical Markdown and JSON.

## Invocation

```text
Invoke libro-agent-wcag core contract with:
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
