# Claude Adapter Template

Use this wrapper prompt while keeping core semantics unchanged:

```text
Invoke libro-agent-wcag core contract:
<contract>
{
  "task_mode": "<create|modify>",
  "execution_mode": "<audit-only|suggest-only|apply-fixes>",
  "wcag_version": "<2.0|2.1|2.2>",
  "conformance_level": "<A|AA|AAA>",
  "target": "<path-or-url>",
  "output_language": "<language-tag>"
}
</contract>

Execution requirements:
- Apply defaults: execution_mode=suggest-only, wcag_version=2.1, conformance_level=AA, output_language=zh-TW.
- Respect task_mode:
  - create: work from a draft or generated target; if there is no existing target to scan, provide guidance and manual-review items instead of claiming a scan ran
  - modify: audit the existing target before proposing or applying changes
- Audit with axe and Lighthouse when a concrete target exists.
- Respect execution_mode:
  - audit-only: return findings only
  - suggest-only: return findings plus remediation suggestions without editing
  - apply-fixes: let the agent perform the actual file modification when safe and requested
- Deduplicate overlapping axe/Lighthouse findings that refer to the same rule and target.
- Map each finding/fix to WCAG SC + official W3C citation.
- Return both:
  1. Markdown table with required columns and order.
  2. JSON report with canonical keys.
- Include execution_mode in JSON and Markdown summary text.
- Preserve the same finding IDs across both outputs.
```
