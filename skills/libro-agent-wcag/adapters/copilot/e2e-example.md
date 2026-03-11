# Copilot End-to-End Example

## Scenario

Use an instruction file to audit a draft page in `create` mode, then return guidance without pretending a scan exists.

## Invocation

```text
Use the libro-agent-wcag shared contract:
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
