# Troubleshooting Intake Guide

Use this intake when collecting actionable reports for install failures or remediation mismatches.

## Required context

- Platform: OS + shell + Python version
- Agent target: `codex`, `claude`, `gemini`, or `copilot`
- Install destination path
- Repo commit/branch (or installed package version)
- Exact command that failed

## Installation-failure intake checklist

- Full stderr/stdout from `install-agent.py` and `doctor-agent.py`
- Whether `--force` and custom `--dest` were used
- File permission or path-length constraints
- Whether wrapper scripts (`install-agent.ps1` / `.sh`) were used

## Remediation-mismatch intake checklist

- Input target file type and path
- Chosen contract (`task_mode`, `execution_mode`, `wcag_version`, `conformance_level`)
- Generated `wcag-report.json` and `wcag-report.md`
- If `apply-fixes`, include diff artifact and post-fix snapshot
- Expected vs actual behavior

## Fast triage buckets

1. Environment/setup error (Python/Node/tools missing)
2. Installer path/permission error
3. Scanner invocation error (`axe` or `lighthouse` unavailable)
4. Contract mismatch (wrong execution mode or unsupported target type)
5. Remediation scope misunderstanding (`apply-fixes` safe-only boundary)

## Routing rule

- Installation path issues: assign to installer maintainers.
- Finding/fix behavior issues: assign to workflow/remediation maintainers.
- Documentation gaps: assign to release docs owners.
