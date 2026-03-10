# Copilot Adapter Template

Use this wrapper prompt to keep Copilot aligned with the core WCAG contract:

```text
Use the wcag-web-skill shared contract without renaming fields.

Contract:
{
  "task_mode": "<create|modify>",
  "execution_mode": "<audit-only|suggest-only|apply-fixes>",
  "wcag_version": "<2.0|2.1|2.2>",
  "conformance_level": "<A|AA|AAA>",
  "target": "<local-file-path-or-url>",
  "output_language": "<language-tag>"
}

Required behavior:
1. Default missing values to execution_mode=suggest-only, wcag_version=2.1, conformance_level=AA, output_language=zh-TW.
2. If target is an existing local file path, normalize it to a file:// URL before scanner execution.
3. Run axe and Lighthouse, or mark a skipped tool as skipped rather than failed.
4. Respect execution_mode:
   - audit-only: report findings only
   - suggest-only: report findings and remediation suggestions without editing
   - apply-fixes: apply fixes when safe and requested
5. Preserve the canonical JSON keys:
   run_meta, target, standard, findings, fixes, citations, summary.
6. Preserve the canonical Markdown columns:
   Issue ID | Source | WCAG Version | Level | SC | Current | Fix | Changed Target | Citation | Status
7. Use version-matched W3C Understanding links for cited success criteria.
8. Include execution_mode in JSON and Markdown summary text.
9. Return Markdown and JSON together, and keep issue IDs stable across both outputs.
```
