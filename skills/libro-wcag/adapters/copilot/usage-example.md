# Copilot Usage Example

## Install

```powershell
python .\scripts\install-agent.py --agent copilot
python .\scripts\doctor-agent.py --agent copilot
```

## Use

1. Load `adapters/copilot/prompt-template.md` into your Copilot instruction file.
2. Provide this contract:

```json
{
  "task_mode": "create",
  "execution_mode": "suggest-only",
  "wcag_version": "2.1",
  "conformance_level": "AA",
  "target": "./draft.html",
  "output_language": "zh-TW"
}
```

## Smoke Check

- Confirm create mode avoids fake scan claims when no concrete target exists.
- Confirm canonical JSON keys remain unchanged.

## First-Run Output Example

```markdown
### Summary
- Mode: suggest-only
- Findings: 1
- Manual review required: true
```

```json
{
  "summary": {
    "total_findings": 1,
    "manual_required_count": 1,
    "remediation_lifecycle": {
      "implemented": 0,
      "planned": 1,
      "manual_review_required": 1
    }
  }
}
```
