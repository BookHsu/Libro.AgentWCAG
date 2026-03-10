# Gemini Adapter Template

Use this wrapper prompt to keep Gemini aligned with the core WCAG contract:

```text
Follow the wcag-web-skill core contract exactly.

Input contract:
{
  "task_mode": "<create|modify>",
  "wcag_version": "<2.0|2.1|2.2>",
  "conformance_level": "<A|AA|AAA>",
  "target": "<local-file-path-or-url>",
  "output_language": "<language-tag>"
}

Execution rules:
1. Apply defaults when omitted: wcag_version=2.1, conformance_level=AA, output_language=zh-TW.
2. Convert existing local file paths to file:// URLs before running scanners.
3. Run axe and Lighthouse unless the caller explicitly skips one.
4. Keep tool status semantics: ok, skipped, error.
5. Map each major finding and fix to WCAG SC plus a W3C citation URL that matches the selected WCAG version.
6. Return both outputs in the same response:
   - Markdown table with the canonical column order
   - JSON report with canonical top-level keys
7. Keep finding IDs aligned between Markdown and JSON.
```
