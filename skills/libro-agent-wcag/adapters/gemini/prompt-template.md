# Gemini Adapter Template

Use this wrapper prompt to keep Gemini aligned with the core WCAG contract:

```text
Follow the libro-agent-wcag core contract exactly.

Input contract:
{
  "task_mode": "<create|modify>",
  "execution_mode": "<audit-only|suggest-only|apply-fixes>",
  "wcag_version": "<2.0|2.1|2.2>",
  "conformance_level": "<A|AA|AAA>",
  "target": "<local-file-path-or-url>",
  "output_language": "<language-tag>"
}

Execution rules:
1. Apply defaults when omitted: execution_mode=suggest-only, wcag_version=2.1, conformance_level=AA, output_language=zh-TW.
2. Respect task_mode:
   - create: work from a draft or generated target; if there is no existing target to scan, provide guidance and manual-review items instead of claiming a scan ran
   - modify: audit the existing target before proposing or applying changes
3. Convert existing local file paths to file:// URLs before running scanners.
4. Run axe and Lighthouse unless the caller explicitly skips one and a concrete target is available.
5. Keep tool status semantics: ok, skipped, error.
6. Respect execution_mode:
   - audit-only: report findings only
   - suggest-only: report findings and remediation suggestions without editing
   - apply-fixes: let the agent perform the actual file modification when safe and requested
7. Deduplicate overlapping axe/Lighthouse findings that refer to the same rule and target.
8. Map each major finding and fix to WCAG SC plus a W3C citation URL that matches the selected WCAG version.
9. Return both outputs in the same response:
   - Markdown table with the canonical column order
   - JSON report with canonical top-level keys
10. Include execution_mode in JSON and Markdown summary text.
11. Keep finding IDs aligned between Markdown and JSON.
```
