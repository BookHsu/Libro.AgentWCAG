# Release Note Template

Use this template for standard `Libro.AgentWCAG` releases.

## Title

`Libro.AgentWCAG <version>`

## Highlights

- 

## Breaking Changes

- None

## Known Limitations

- 

## Install / Verify

```powershell
pwsh -File .\scripts\install-latest.ps1 -ReleaseBase <release-asset-url-or-dir> -Agent codex
python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity
```

## Checksum Verification

- Verify `libro-agent-wcag-<version>-sha256sums.txt` before installation.
- Confirm the selected bundle checksum matches both the checksum file and `libro-agent-wcag-<version>-release-manifest.json`.

## Rollback / Hotfix Context

- Superseded versions:
- Operator notes:
