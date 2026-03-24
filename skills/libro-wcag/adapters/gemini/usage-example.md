# Gemini Usage Example

## Install

```powershell
python .\scripts\install-agent.py --agent gemini
python .\scripts\doctor-agent.py --agent gemini
```

If you work inside a repo-local Gemini workspace, you can also commit `.gemini/skills/libro-wcag/SKILL.md` and let Gemini discover the skill without a user-home install. To materialize the same layout into another workspace root, run:

```powershell
python .\scripts\install-agent.py --agent gemini --workspace-root .
```

For MCP-based Gemini integration, install dependencies and emit a workspace-local config:

```powershell
python -m pip install -r .\mcp-server\requirements.txt
python .\scripts\install-agent.py --agent gemini --workspace-root . --emit-mcp-config gemini
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
