# Libro.AgentWCAG

Libro.AgentWCAG is a cross-agent WCAG web accessibility skill repository. It uses one vendor-neutral contract so Codex, Claude, Gemini, and Copilot can audit accessibility, propose fixes, and apply safe first-pass fixes in a consistent way when explicitly authorized.

## Purpose

The hard part of web accessibility work is usually not finding a tool. It is keeping workflows, outputs, and remediation expectations consistent across different agents and teams. Libro.AgentWCAG turns that into an installable, verifiable, releasable workflow.

- One shared contract across multiple AI agents
- One consistent task model for audit, suggestion, and partial remediation
- One release path for installation, verification, and versioned delivery

## What It Helps You Do

- Quickly identify WCAG accessibility issues on pages and components
- Produce issue summaries and remediation guidance in a consistent format
- Apply safe first-pass fixes to supported local files when modification is explicitly requested
- Keep cross-agent accessibility work aligned across teams

## Prerequisites

Python 3 is required.

```powershell
python --version
```

```sh
brew install python3                         # macOS
sudo apt update && sudo apt install python3 # Ubuntu / Debian
winget install Python.Python.3.12           # Windows
```

## Install

### Claude Marketplace (Claude Code)

Coming soon - pending marketplace availability.

```text
/plugin marketplace add BookHsu/Libro.AgentWCAG
/plugin install libro-wcag@libro-wcag-marketplace
```

### npm CLI

```powershell
 npm install -g librowcag-cli
libro install claude   # Claude Code
libro install gemini   # Gemini CLI
libro install copilot  # Copilot
libro install codex    # Codex
libro doctor claude    # verify Claude installation
```

### Clone + CLI

```powershell
git clone https://github.com/BookHsu/Libro.AgentWCAG.git
cd Libro.AgentWCAG
python .\scripts\libro.py install claude
python .\scripts\libro.py doctor claude
```

Verification and removal:

```powershell
python .\scripts\libro.py doctor claude --verify-manifest-integrity
python .\scripts\libro.py doctor claude --check-scanners   # verify Node.js/npx/axe/lighthouse
python .\scripts\libro.py remove claude
```

## CLI Quick Start

After installation, you can run audits directly from the CLI without going through an AI agent:

```powershell
# Audit a URL
python .\scripts\libro.py audit https://example.com

# Audit a local file with custom output directory
python .\scripts\libro.py audit ./src/index.html --output-dir out/wcag

# Audit with remediation suggestions (suggest-only mode)
python .\scripts\libro.py audit ./src/index.html --execution-mode suggest-only

# Auto-fix supported issues
python .\scripts\libro.py audit ./src/index.html --execution-mode apply-fixes

# Check scanner toolchain availability
python .\scripts\libro.py audit --preflight-only
```

After a run completes, outputs appear in `out/`:

- `wcag-report.json` — structured JSON report
- `wcag-report.md` — Markdown summary table

## Use

Libro.AgentWCAG is not just a single command. It is a shared skill contract that different AI agents can follow. In practice, you choose whether you want to audit only, get suggestions, or apply fixes.

Three working modes:

| Mode | Finds issues | Gives fix suggestions | Edits files |
|---|---|---|---|
| `audit-only` | Yes | No | No |
| `suggest-only` | Yes | Yes | No |
| `apply-fixes` | Yes | Yes | Yes, only for supported local files |

Usage examples:

```text
Audit only
Use audit-only mode to review https://example.com for WCAG 2.1 AA.

Suggest only
Use suggest-only mode to review src/page.html and provide fix suggestions without editing files.

Apply fixes
Use apply-fixes mode to review src/page.html and apply safe fixes to supported local issues.
```

- Start with `audit-only` when you want a clean accessibility review
- Use `suggest-only` when you want remediation ideas before changing files
- Move to `apply-fixes` only when you want the changes carried out

This keeps review and modification separate, which makes the workflow easier to control.

> **MCP note**: The MCP server provides read-only audit (`audit-only`) and suggestions (`suggest-only`) only; `apply-fixes` is not exposed via MCP. Use the CLI directly for auto-fix. Production deployments can use `mcp-server/requirements.lock` for hash-pinned dependencies.

## License

MIT. See [LICENSE](LICENSE).
