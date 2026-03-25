# Claude Usage Example

## Install

```powershell
python .\scripts\install-agent.py --agent claude
python .\scripts\doctor-agent.py --agent claude
```

For MCP-based Claude workspace integration, install dependencies and use the sample config in `docs/examples/claude/mcp.sample.json`. You can also emit a local config directly:

```powershell
python -m pip install -r .\mcp-server\requirements.txt
python .\scripts\install-agent.py --agent claude --workspace-root . --emit-mcp-config claude
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

## First-Run Output Example

```markdown
### Summary
- Mode: suggest-only
- Findings: 3
- Manual review required: true
```

```json
{
  "summary": {
    "total_findings": 3,
    "manual_required_count": 1,
    "remediation_lifecycle": {
      "implemented": 0,
      "planned": 2,
      "manual_review_required": 1
    }
  }
}
```
