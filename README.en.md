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

## Install

Using Claude Marketplace (Claude Code)

```text
/plugin marketplace add BookHsu/Libro.AgentWCAG
/plugin install libro-wcag@libro-wcag-marketplace
```

```powershell
git clone https://github.com/BookHsu/Libro.AgentWCAG.git
cd Libro.AgentWCAG
python .\scripts\libro.py install claude
python .\scripts\libro.py doctor claude
```

Verification and removal:

```powershell
python .\scripts\libro.py doctor claude --verify-manifest-integrity
python .\scripts\libro.py remove claude
```

If you prefer wrappers:

```powershell
.\scripts\libro.ps1 install claude
.\scripts\libro.ps1 doctor claude
```

```sh
./scripts/libro.sh install claude
./scripts/libro.sh doctor claude
```

### Other Command Entrypoints

If you prefer wrappers:

```powershell
.\scripts\libro.ps1 install claude
.\scripts\libro.ps1 doctor claude
```

```sh
./scripts/libro.sh install claude
./scripts/libro.sh doctor claude
```

## Use

Libro.AgentWCAG is not just a single command. It is a shared skill contract that different AI agents can follow. In practice, you choose whether you want to audit only, get suggestions, or apply fixes.

Three working modes:

| Mode | Finds issues | Gives fix suggestions | Edits files |
|---|---|---|---|
| `audit-only` | Yes | No | No |
| `suggest-only` | Yes | Yes | No |
| `apply-fixes` | Yes | Yes | Yes, only for supported local files |

- Start with `audit-only` when you want a clean accessibility review
- Use `suggest-only` when you want remediation ideas before changing files
- Move to `apply-fixes` only when you want the changes carried out

This keeps review and modification separate, which makes the workflow easier to control.
