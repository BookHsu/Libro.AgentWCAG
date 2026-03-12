# Gemini Usage Example

## Install

```powershell
python .\scripts\install-agent.py --agent gemini
python .\scripts\doctor-agent.py --agent gemini
```

## Use

1. Load `adapters/gemini/prompt-template.md` into your Gemini custom instruction or wrapper.
2. Provide this contract:

```json
{
  "task_mode": "modify",
  "execution_mode": "audit-only",
  "wcag_version": "2.2",
  "conformance_level": "AA",
  "target": "./index.html",
  "output_language": "en"
}
```

## Smoke Check

- Confirm tool statuses use `ok`, `skipped`, or `error`.
- Confirm WCAG 2.2 manual-review findings remain visible when needed.

## First-Run Output Example

```markdown
### Summary
- Mode: audit-only
- Findings: 4
- Manual review required: true
```

```json
{
  "summary": {
    "total_findings": 4,
    "manual_required_count": 2,
    "remediation_lifecycle": {
      "implemented": 0,
      "planned": 2,
      "manual_review_required": 2
    }
  }
}
```
