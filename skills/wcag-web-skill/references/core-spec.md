# Core Spec

## 1. Canonical Input

Use this schema as the single source of truth:

```json
{
  "task_mode": "create | modify",
  "wcag_version": "2.0 | 2.1 | 2.2",
  "conformance_level": "A | AA | AAA",
  "target": "local file path or URL",
  "output_language": "string"
}
```

Validation rules:
- `task_mode` must be `create` or `modify`.
- `wcag_version` must be one of `2.0`, `2.1`, `2.2`.
- `conformance_level` must be one of `A`, `AA`, `AAA`.
- Apply defaults: `2.1`, `AA`, `zh-TW`.
- Existing local paths must be normalized to `file://` URLs before scanner execution.

## 2. Canonical Workflow

1. Resolve defaults and lock selected standard.
2. Run axe and Lighthouse scans.
3. Normalize findings into unified IDs.
4. Map each finding/fix to WCAG SC and citations.
5. Output Markdown table and JSON report.
6. If one scanner fails, continue with available scanner and add manual fallback steps.

## 3. JSON Output Contract

```json
{
  "run_meta": {
    "generated_at": "ISO-8601",
    "workflow_version": "1.0.0",
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
      "severity": "critical | serious | moderate | minor | info",
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
      "status": "planned | implemented | verified"
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
    "needs_manual_review": 0
  }
}
```

## 4. Markdown Table Contract

Use exactly these columns and order:

`Issue ID | Source | WCAG Version | Level | SC | Current | Fix | Changed Target | Citation | Status`

Status vocabulary:
- Findings: `open`, `fixed`, `partial`, `needs-review`
- Fixes: `planned`, `implemented`, `verified`
