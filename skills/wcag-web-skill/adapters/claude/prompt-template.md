# Claude Adapter Template

Use this wrapper prompt while keeping core semantics unchanged:

```text
Invoke wcag-web-skill core contract:
<contract>
{
  "task_mode": "<create|modify>",
  "wcag_version": "<2.0|2.1|2.2>",
  "conformance_level": "<A|AA|AAA>",
  "target": "<path-or-url>",
  "output_language": "<language-tag>"
}
</contract>

Execution requirements:
- Apply defaults: wcag_version=2.1, conformance_level=AA, output_language=zh-TW.
- Audit with axe and Lighthouse.
- Map each finding/fix to WCAG SC + official W3C citation.
- Return both:
  1. Markdown table with required columns and order.
  2. JSON report with canonical keys.
- Preserve the same finding IDs across both outputs.
```

