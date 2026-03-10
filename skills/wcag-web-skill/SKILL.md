---
name: wcag-web-skill
description: Vendor-neutral WCAG workflow for creating new web pages or remediating existing pages with selectable WCAG model (2.0/2.1/2.2 and A/AA/AAA). Use when any AI agent must perform consistent accessibility audit/remediation, produce aligned Markdown+JSON outputs, and attach W3C official citations.
---

# WCAG Web Skill

Use this skill as a cross-agent accessibility contract. Keep business logic in the core spec and only adapt prompt syntax per platform adapter.

## Required Input Contract

Collect or infer this contract before doing work:

```json
{
  "task_mode": "create | modify",
  "execution_mode": "audit-only | suggest-only | apply-fixes",
  "wcag_version": "2.0 | 2.1 | 2.2",
  "conformance_level": "A | AA | AAA",
  "target": "local file path or URL",
  "output_language": "BCP-47, default zh-TW"
}
```

Apply defaults when omitted:
- `execution_mode`: `suggest-only`
- `wcag_version`: `2.1`
- `conformance_level`: `AA`
- `output_language`: `zh-TW`

Treat local file paths as first-class inputs. The audit runner converts existing local paths to `file://` URLs before invoking scanners.

## Fixed Workflow

1. Lock the selected WCAG model and note defaults used.
2. Run automated checks with both axe and Lighthouse via `scripts/run_accessibility_audit.py`.
3. Rank findings by severity and impact, then map each item to WCAG SC.
4. Respect `execution_mode`:
   - `audit-only`: find issues only
   - `suggest-only`: find issues and propose remediation steps without editing
   - `apply-fixes`: find issues and apply remediations when the agent can safely modify the target
5. Produce the two required outputs:
   - Markdown comparison table
   - JSON structured report
6. Attach W3C official citations for all major findings/fixes.

## Output Contract

Keep field semantics unchanged across adapters.

Markdown columns:

`Issue ID | Source | WCAG Version | Level | SC | Current | Fix | Changed Target | Citation | Status`

JSON top-level keys:

`run_meta`, `target`, `standard`, `findings[]`, `fixes[]`, `citations[]`, `summary`

Report the chosen `execution_mode` in both JSON and Markdown summary text.

Use `scripts/normalize_report.py` to normalize mixed tool outputs into the contract.

## Adapter Rules

- Use `adapters/openai-codex/prompt-template.md` for OpenAI/Codex orchestration.
- Use `adapters/claude/prompt-template.md` for Claude orchestration.
- Use `adapters/gemini/prompt-template.md` for Gemini orchestration.
- Use `adapters/copilot/prompt-template.md` for Copilot orchestration.
- Never add adapter-specific business logic that alters core output semantics.

## References

- Load `references/core-spec.md` for strict field definitions and process details.
- Load `references/wcag-citations.md` for official W3C citation mapping.
- Load `references/adapter-mapping.md` for cross-agent translation rules.
