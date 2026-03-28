# Supported Environments Matrix

This matrix defines the currently supported runtime and scanner prerequisites.

| Area | Supported | Notes |
| --- | --- | --- |
| Python runtime | 3.12+ | Required for workflow and repo scripts. |
| Node.js runtime | Active LTS (18+) | Required for scanner tooling through `npx`. |
| Package execution | `npx` available in PATH | Used for `@axe-core/cli` and `lighthouse`. |
| Scanner tools | `@axe-core/cli`, `lighthouse` via `npx` | Missing tools cause scanner-path failures. |
| OS scripts | Windows PowerShell + POSIX shell | Wrapper scripts are provided for both. |
| Agent adapters | Codex, Claude, Gemini, Copilot | Installed via `scripts/install-agent.py`. |
| MCP server | Python 3.12+, `mcp>=1.2,<2` | Hash-pinned lock file at `mcp-server/requirements.lock`. MCP tools are read-only (audit + suggest); `apply-fixes` is not exposed via MCP. |
| Release packaging | Python stdlib `zipfile`, local filesystem write access | `scripts/package-release.py` builds deterministic ZIP bundles, checksums, and release manifest assets. |

## Baseline prerequisites

- Python dependencies from project setup are installed.
- Node.js and `npx` are installed and callable from terminal.
- Network and local file permissions allow scanner invocation on target files.

## Clean release-consumer support

- Windows: PowerShell with `Expand-Archive`, `Get-FileHash`, and `python` in `PATH`.
- macOS: POSIX shell plus `python` in `PATH`; release bootstrap uses Python stdlib for download, zip extraction, and checksum verification.
- Linux: POSIX shell plus `python` in `PATH`; release bootstrap uses Python stdlib for download, zip extraction, and checksum verification.
- All clean-smoke environments must allow temporary-directory write access for bundle extraction, installer staging, audit artifacts, and smoke-summary output.

## Dependency lock and version-capture guidance

### Local workflow

1. Lock Python tooling for repeatable audits:
   - `python -m pip install --upgrade pip`
   - `python -m pip install pyyaml pip-audit`
   - `python -m pip freeze > .ci/requirements-lock.txt`
2. Lock scanner tooling with explicit versions:
   - `mkdir -p .ci/scanner-toolchain`
   - `npm install --prefix .ci/scanner-toolchain --package-lock-only @axe-core/cli@4.10.2 lighthouse@12.3.0`
3. Capture resolved versions for triage evidence:
   - `python skills/libro-wcag/scripts/run_accessibility_audit.py --preflight-only`
   - Preserve `checks[].version`, `checks[].resolved_command`, and `checks[].version_provenance` in build artifacts.

### CI workflow

- Pin Python and Node versions in workflow config (`actions/setup-python`, `actions/setup-node`).
- Install Python tooling from a committed lock file when available.
- Generate and audit scanner lock files in CI before running WCAG scans.
- Store preflight JSON output and dependency audit logs with the same retention policy as WCAG reports.

## Supply-chain triage evidence minimum

When opening a dependency/security triage ticket, include:

- Python runtime version and lock reference (`requirements-lock.txt` or equivalent).
- Node runtime version and scanner lock reference (`package-lock.json` path).
- `run_meta.preflight.tools.*.version` and `run_meta.preflight.tools.*.version_provenance` from the failing run.
- Raw dependency audit outputs (`pip-audit`, `npm audit`) with timestamp and commit SHA.

## Not guaranteed

- Legacy Python versions below 3.12.
- Node versions outside active LTS maintenance.
- Environments that block subprocess execution for scanner commands.
- Release packaging lanes that cannot write local ZIP/checksum assets under the selected output directory.
- GA publish attempts that skip the documented release workflow or bypass retained smoke/package artifacts.
