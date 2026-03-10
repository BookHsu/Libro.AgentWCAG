# OpenAI/Codex Adapter Template

Use this wrapper prompt to invoke the core WCAG workflow:

```text
Use $wcag-web-skill with the following contract:
{
  "task_mode": "<create|modify>",
  "execution_mode": "<audit-only|suggest-only|apply-fixes>",
  "wcag_version": "<2.0|2.1|2.2>",
  "conformance_level": "<A|AA|AAA>",
  "target": "<path-or-url>",
  "output_language": "<language-tag>"
}

Requirements:
1) Resolve defaults (suggest-only + 2.1 + AA + zh-TW) if missing.
2) Run axe + Lighthouse checks.
3) Map each finding to WCAG SC and W3C citation.
4) Respect execution_mode:
   - audit-only: report findings only
   - suggest-only: report findings and remediation suggestions without editing
   - apply-fixes: apply remediations when safe and requested
4) Provide both outputs:
   - Markdown table with fixed columns
   - JSON with canonical keys
5) Include execution_mode in JSON and Markdown summary text.
6) Keep finding IDs aligned across Markdown and JSON.
```
