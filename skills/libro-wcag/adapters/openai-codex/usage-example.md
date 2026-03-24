# OpenAI/Codex Usage Example

## Install

```powershell
python .\scripts\install-agent.py --agent codex
python .\scripts\doctor-agent.py --agent codex
```

## Invoke

```text
Use $libro-wcag with:
{
  "task_mode": "modify",
  "execution_mode": "suggest-only",
  "wcag_version": "2.1",
  "conformance_level": "AA",
  "target": "./index.html",
  "output_language": "zh-TW"
}
```

## Smoke Check

- Confirm the agent returns both Markdown and JSON.
- Confirm finding IDs match across both outputs.

## First-Run Output Example

```markdown
### Summary
- Mode: suggest-only
- Findings: 2
- Manual review required: true
```

```json
{
  "summary": {
    "total_findings": 2,
    "manual_required_count": 1,
    "remediation_lifecycle": {
      "implemented": 0,
      "planned": 1,
      "manual_review_required": 1
    }
  }
}
```
