# Core Spec

## 1. Canonical Input

Use this schema as the single source of truth:

```json
{
  "task_mode": "create | modify",
  "execution_mode": "audit-only | suggest-only | apply-fixes",
  "wcag_version": "2.0 | 2.1 | 2.2",
  "conformance_level": "A | AA | AAA",
  "target": "local file path or URL",
  "output_language": "string"
}
```

Validation rules:
- `task_mode` must be `create` or `modify`.
- `execution_mode` must be `audit-only`, `suggest-only`, or `apply-fixes`.
- `wcag_version` must be one of `2.0`, `2.1`, `2.2`.
- `conformance_level` must be one of `A`, `AA`, `AAA`.
- Apply defaults: `suggest-only`, `2.1`, `AA`, `zh-TW`.
- Allow only `http`, `https`, `file`, or an existing local file path.
- Existing local paths must be normalized to `file://` URLs before scanner execution.

## 2. Canonical Workflow

1. Resolve defaults and lock selected standard.
2. Validate the target, then run axe and Lighthouse scans with a bounded timeout.
3. Normalize findings into unified IDs.
4. Respect `execution_mode`:
   - `audit-only`: do not propose or apply code changes
   - `suggest-only`: propose fixes but do not modify code
   - `apply-fixes`: authorize the calling agent or adapter to apply fixes when safe and requested
5. Map each finding/fix to WCAG SC and citations.
6. Output Markdown table and JSON report.
7. If one scanner fails, continue with available scanner and add manual fallback steps.

Interpret `task_mode` as follows:
- `create`: operate on a draft, generated page, or template. If no concrete page is available yet, skip fake scan claims and emit guidance/manual-review items instead.
- `modify`: operate on an existing target and audit it before proposing or applying changes.

## 3. JSON Output Contract

```json
{
  "run_meta": {
    "generated_at": "ISO-8601",
    "workflow_version": "1.0.0",
    "execution_mode": "audit-only | suggest-only | apply-fixes",
    "output_language": "string",
    "files_modified": "boolean",
    "modification_owner": "agent-or-adapter",
    "tools": {
      "axe": "ok | skipped | error",
      "lighthouse": "ok | skipped | error"
    },
    "notes": []
  },
  "target": {
    "value": "string",
    "task_mode": "create | modify"
  },
  "standard": {
    "wcag_version": "2.0 | 2.1 | 2.2",
    "conformance_level": "A | AA | AAA"
  },
  "findings": [
    {
      "id": "ISSUE-001",
      "source": "axe | lighthouse | manual",
      "sources": ["axe", "lighthouse"],
      "rule_id": "string",
      "severity": "critical | serious | moderate | minor | info",
      "confidence": "high | medium | low",
      "sc": ["1.1.1"],
      "current": "string",
      "changed_target": "string",
      "status": "open | fixed | partial | needs-review"
    }
  ],
  "fixes": [
    {
      "id": "FIX-001",
      "finding_id": "ISSUE-001",
      "description": "string",
      "changed_target": "string",
      "status": "planned | implemented | verified",
      "remediation_priority": "high | medium | low",
      "confidence": "high | medium | low",
      "auto_fix_supported": "boolean",
      "framework_hints": {}
    }
  ],
  "citations": [
    {
      "finding_id": "ISSUE-001",
      "sc": "1.1.1",
      "url": "https://www.w3.org/..."
    }
  ],
  "summary": {
    "total_findings": 0,
    "fixed_findings": 0,
    "needs_manual_review": 0,
    "change_summary": []
  }
}
```

## 4. Markdown Table Contract

Use exactly these columns and order:

`Issue ID | Source | WCAG Version | Level | SC | Current | Fix | Changed Target | Citation | Status`

Prefix the table with a short summary line that states the execution mode and whether files were modified.
Support localized summary lines and column headers while keeping JSON keys canonical.
Because the current core workflow does not rewrite target files, `files_modified` should remain `false` and the modification owner should stay `agent-or-adapter` unless a future remediation engine is added.

Status vocabulary:
- Findings: `open`, `fixed`, `partial`, `needs-review`
- Fixes: `planned`, `implemented`, `verified`
