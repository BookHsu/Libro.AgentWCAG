# OpenAI/Codex Usage Example

## Install

```powershell
python .\scripts\install-agent.py --agent codex
python .\scripts\doctor-agent.py --agent codex
```

## Invoke

```text
Use $libro-agent-wcag with:
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
