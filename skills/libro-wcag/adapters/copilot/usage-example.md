# Copilot Usage Example

## Install

```powershell
python .\scripts\libro.py install copilot
python .\scripts\libro.py doctor copilot
```

If you need workspace MCP, install dependencies, compare against `docs/examples/copilot/mcp.sample.json`, and emit a local `.vscode/mcp.json`:

```powershell
python -m pip install -r .\mcp-server\requirements.txt
python .\scripts\libro.py install copilot --workspace-root . --emit-mcp-config copilot
```

Copilot writes VS Code MCP settings, so the sample uses a top-level `servers` object instead of the `mcpServers` key used by Claude and Gemini.

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
- Confirm Copilot MCP config keeps the VS Code `servers` top-level key from `docs/examples/copilot/mcp.sample.json`.

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
