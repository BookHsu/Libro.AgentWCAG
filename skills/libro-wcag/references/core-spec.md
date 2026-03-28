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
  "output_language": "en | zh-TW"
}
```

Validation rules:
- `task_mode` must be `create` or `modify`.
- `execution_mode` must be `audit-only`, `suggest-only`, or `apply-fixes`.
- `wcag_version` must be one of `2.0`, `2.1`, `2.2`.
- `conformance_level` must be one of `A`, `AA`, `AAA`.
- `output_language` currently supports `en` and `zh-TW` only. Other BCP-47 values are accepted but fall back to `en`. The internal dictionary design allows adding languages in the future.
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
   - `apply-fixes`: apply safe first-pass fixes for supported local targets (`.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, `.vue`), then let the calling agent or adapter handle unsupported or higher-risk changes
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
    "modification_owner": "agent-or-adapter | core-workflow",
    "tools": {
      "axe": "ok | skipped | error",
      "lighthouse": "ok | skipped | error"
    },
    "diff_artifacts": [],
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
      "status": "open | fixed | partial | needs-review",
      "fixability": "auto-fix | assisted | manual",
      "verification_status": "not-run | diff-generated | verified | manual-review",
      "manual_review_required": "boolean"
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
      "fixability": "auto-fix | assisted | manual",
      "verification_status": "not-run | diff-generated | verified | manual-review",
      "manual_review_required": "boolean",
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
    "change_summary": [],
    "diff_summary": [],
    "remediation_lifecycle": {
      "planned": 0,
      "implemented": 0,
      "verified": 0,
      "manual_review_required": 0
    }
  }
}
```

## 4. Markdown Table Contract

Use exactly these columns and order:

`Issue ID | Source | WCAG Version | Level | SC | Current | Fix | Changed Target | Citation | Status`

Prefix the table with a short summary line that states the execution mode and whether files were modified.
Support localized summary lines and column headers while keeping JSON keys canonical.
For `apply-fixes`, `files_modified` may become `true` and `modification_owner` may become `core-workflow` when the target is a supported local file (`.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, `.vue`) and safe rewrite helpers succeed. Unsupported target types must keep `files_modified=false`, preserve assisted/manual semantics, and leave ownership with `agent-or-adapter`.
Diff artifacts must be recorded in `run_meta.diff_artifacts[]`, and fix verification should move from `not-run` to `diff-generated` when the core workflow rewrites a supported local target.

Status vocabulary:
- Findings: `open`, `fixed`, `partial`, `needs-review`
- Fixes: `planned`, `implemented`, `verified`

## 5. Schema Versioning Policy

The report schema follows semantic versioning (`MAJOR.MINOR.PATCH`):

- **MAJOR** — breaking changes to required fields, removed keys, or incompatible structural changes. Consumers relying on the previous schema may fail.
- **MINOR** — new optional fields or additive changes. Existing consumers continue to work.
- **PATCH** — documentation fixes, description updates, or constraint tightening that does not alter field presence.

The authoritative version lives in `shared_constants.REPORT_SCHEMA_VERSION` and is mirrored as a `const` in the schema file's `report_schema.version` field. The `report_artifacts` module validates that both values match before staging any report artifact.

Compatibility contract:

- The `report_schema.compatibility` field uses a semver range (e.g. `^1.0.0`) indicating that consumers built for the same major version can safely read the report.
- When upgrading the schema, update `REPORT_SCHEMA_VERSION`, the schema filename, the `$id`, the `version` const, and the compatibility range in a single commit.
- Baseline governance checks (`baseline_governance.py`, `advanced_gates.py`) compare the report's `report_schema.version` against the expected version and flag mismatches.

No automated migration between major versions is provided at this time. Consumers should treat major version bumps as requiring manual review.

## 6. Language Separation

Prompt instructions and output language serve different purposes and are intentionally decoupled:

- **Prompt language**: All adapter prompt templates (`adapters/*/prompt-template.md`) use English for agent directives. This ensures precise, unambiguous instructions regardless of the user's preferred output language.
- **Output language**: Controlled by the `output_language` contract field (default `zh-TW`). Affects Markdown column headers, summary labels, and human-facing report text. The `_language_key()` helper in `wcag_workflow.py` maps any value starting with `zh` to the `zh-TW` dictionary; all other values fall back to `en`.

Adapters must not translate their directive sections based on `output_language`. Only the generated report content respects this field.

