# Claude Usage Example

## Install

```powershell
python .\scripts\install-agent.py --agent claude
python .\scripts\doctor-agent.py --agent claude
```

## Use

1. Load `adapters/claude/prompt-template.md` into your Claude project or system prompt.
2. Provide this contract:

```json
{
  "task_mode": "modify",
  "execution_mode": "suggest-only",
  "wcag_version": "2.1",
  "conformance_level": "AA",
  "target": "./index.html",
  "output_language": "en"
}
```

## Smoke Check

- Confirm Claude preserves the same issue IDs between Markdown and JSON.
- Confirm W3C citations are version-matched.
