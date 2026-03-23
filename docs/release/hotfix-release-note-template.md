# Hotfix Release Note Template

Use this template when publishing a corrective hotfix release.

## Title

`Libro.AgentWCAG <version>`

## Replaces

- Broken version:
- Failure mode:

## Fix Summary

- 

## User Action Required

- Upgrade from:
- Verify with:

```powershell
pwsh -File .\scripts\install-latest.ps1 -ReleaseBase <release-asset-url-or-dir> -Agent codex
python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity
```

## Checksum Verification

- Verify `libro-agent-wcag-<version>-sha256sums.txt`.

## Known Remaining Limits

- 
