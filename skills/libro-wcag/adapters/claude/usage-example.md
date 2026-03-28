# Claude Usage Example

## Install

```powershell
python .\scripts\libro.py install claude
python .\scripts\libro.py doctor claude
```

If you need workspace MCP, install dependencies and use the sample config in `docs/examples/claude/mcp.sample.json`. Claude uses a top-level `mcpServers` object for MCP configuration. You can also emit a local config directly:

```powershell
python -m pip install -r .\mcp-server\requirements.txt
python .\scripts\libro.py install claude --workspace-root . --emit-mcp-config claude
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
- Confirm Claude MCP config keeps the `mcpServers` top-level key from `docs/examples/claude/mcp.sample.json`.

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

## Advanced: Baseline & Risk Calibration

Use `--risk-calibration-source` and `--stability-baseline` to compare the current audit against a prior run. These flags work identically across all adapters. See `references/cli-reference.md` for the full option reference.

```powershell
python skills/libro-wcag/scripts/run_accessibility_audit.py `
  --target ./index.html `
  --output-dir out/current `
  --risk-calibration-source out/prior/wcag-report.json `
  --risk-calibration-mode warn `
  --stability-baseline out/prior/wcag-report.json `
  --stability-mode warn
```

The audit report will include `run_meta.risk_calibration` and `run_meta.stability_check` sections when these flags are active.
