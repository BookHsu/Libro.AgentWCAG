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
2. Respect task_mode:
   - create: work from a draft or generated target; if there is no existing target to scan, provide guidance and manual-review items instead of claiming a scan ran
   - modify: audit the existing target before proposing or applying changes
3. If target is an existing local file path, normalize it to a file:// URL before scanner execution.
4. Run axe and Lighthouse, or mark a skipped tool as skipped rather than failed.
5. Respect execution_mode:
   - audit-only: report findings only
   - suggest-only: report findings and remediation suggestions without editing
   - apply-fixes: let the agent perform the actual file modification when safe and requested
6. Deduplicate overlapping axe/Lighthouse findings that refer to the same rule and target.
7. Preserve the canonical JSON keys:
   run_meta, target, standard, findings, fixes, citations, summary.
8. Preserve the canonical Markdown columns:
   Issue ID | Source | WCAG Version | Level | SC | Current | Fix | Changed Target | Citation | Status
9. Use version-matched W3C Understanding links for cited success criteria.
10. Include execution_mode in JSON and Markdown summary text.
11. Return Markdown and JSON together, and keep issue IDs stable across both outputs.
```
