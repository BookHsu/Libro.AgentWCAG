# OpenAI/Codex Adapter Template

Use this wrapper prompt to invoke the core WCAG workflow:

```text
Use $libro-wcag with the following contract:
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
2) Respect task_mode:
   - create: work from a draft or generated target; if there is no existing target to scan, provide guidance and manual-review items instead of claiming a scan ran
   - modify: audit the existing target before proposing or applying changes
3) Run axe + Lighthouse checks when a concrete target exists.
4) Map each finding to WCAG SC and W3C citation.
5) Respect execution_mode:
   - audit-only: report findings only
   - suggest-only: report findings and remediation suggestions without editing
   - apply-fixes: allow the core workflow to apply safe first-pass local HTML fixes, then let the agent handle unsupported or higher-risk changes
6) Deduplicate overlapping axe/Lighthouse findings that refer to the same rule and target.
7) Provide both outputs:
   - Markdown table with fixed columns
   - JSON with canonical keys
8) Include execution_mode in JSON and Markdown summary text.
9) Keep finding IDs aligned across Markdown and JSON.
```
