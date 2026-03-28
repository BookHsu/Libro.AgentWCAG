# Gemini Usage Example

## Install

```powershell
python .\scripts\libro.py install gemini
python .\scripts\libro.py doctor gemini
```

If you need a workspace-local installation, run:

```powershell
python .\scripts\libro.py install gemini --workspace-root .
```

If you need workspace MCP, install dependencies and compare against `docs/examples/gemini/settings.mcp.sample.json`. Gemini uses a top-level `mcpServers` object for MCP configuration. You can also emit a workspace-local config:

```powershell
python -m pip install -r .\mcp-server\requirements.txt
python .\scripts\libro.py install gemini --workspace-root . --emit-mcp-config gemini
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
- Confirm Gemini MCP config keeps the `mcpServers` top-level key from `docs/examples/gemini/settings.mcp.sample.json`.

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
