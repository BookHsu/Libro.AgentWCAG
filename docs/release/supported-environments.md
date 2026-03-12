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

## Baseline prerequisites

- Python dependencies from project setup are installed.
- Node.js and `npx` are installed and callable from terminal.
- Network and local file permissions allow scanner invocation on target files.

## Not guaranteed

- Legacy Python versions below 3.12.
- Node versions outside active LTS maintenance.
- Environments that block subprocess execution for scanner commands.
