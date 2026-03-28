# Security Policy

## Reporting a Vulnerability

Please do not open a public GitHub issue for suspected security vulnerabilities.

Report security issues privately to the maintainers through the repository security advisory flow or the maintainer contact channel documented for the current release process. Include:

- affected version or commit
- reproduction steps or proof of concept
- impact assessment
- any suggested mitigation or workaround

We will acknowledge receipt, validate the report, and coordinate remediation and disclosure timing.

## Scope

Security-sensitive areas in this repository include:

- `mcp-server/` command execution and target handling
- `skills/libro-wcag/scripts/auto_fix.py` and file rewrite behavior
- install / uninstall / packaging scripts under `scripts/`
- release and publish workflows under `.github/workflows/`
- dependency and supply-chain integrity for Python and npm artifacts

## Supported Versions

Security fixes are prioritized for:

- the latest released version
- the current default branch when a fix has not yet been released

Older versions may receive guidance or workarounds, but are not guaranteed full patch support.

## Disclosure Principles

- We prefer coordinated disclosure after a fix or mitigation is available.
- We may publish advisories, changelog notes, or release notes once remediation is ready.
- If a report concerns unsafe automatic rewriting, we may temporarily narrow or disable the affected auto-fix path before a full fix ships.

## Repository Hygiene

Contributors should:

- avoid introducing new shell-invocation risks or path traversal behavior
- keep auto-fixes limited to demonstrably safe rewrites
- preserve provenance and version-sync checks in release tooling
- document security-relevant behavior changes in `CHANGELOG.md`
