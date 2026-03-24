# Libro.AgentWCAG

Libro.AgentWCAG is a cross-agent WCAG web accessibility skill repository. It uses one vendor-neutral contract so Codex, Claude, Gemini, and Copilot can audit accessibility, propose fixes, and apply safe first-pass fixes in a consistent way when explicitly authorized.

## Why Libro.AgentWCAG

The hard part of web accessibility work is usually not finding a tool. It is keeping workflows, outputs, and remediation expectations consistent across different agents and teams. Libro.AgentWCAG turns that into an installable, verifiable, releasable workflow.

- One shared contract across multiple AI agents
- One consistent task model for audit, suggestion, and partial remediation
- One release path for installation, verification, and versioned delivery

## What It Helps You Do

- Quickly identify WCAG accessibility issues on pages and components
- Produce issue summaries and remediation guidance in a consistent format
- Apply safe first-pass fixes to supported local files when modification is explicitly requested
- Keep cross-agent accessibility work aligned across teams

## Supported AI Agents

- Codex
- Claude
- Gemini
- Copilot

## Three Working Modes

- `audit-only`: find issues only
- `suggest-only`: find issues and propose fixes
- `apply-fixes`: apply safe fixes to supported local files when explicitly authorized

## Get Started In Three Minutes

### 1. Install

```powershell
python .\scripts\install-agent.py --agent codex
```

To install for other agents:

```powershell
python .\scripts\install-agent.py --agent claude
python .\scripts\install-agent.py --agent gemini
python .\scripts\install-agent.py --agent copilot
python .\scripts\install-agent.py --agent all
```

If you do not want to clone the repository first, you can also bootstrap directly from GitHub:

```sh
curl -sL https://raw.githubusercontent.com/BookHsu/Libro.AgentWCAG.clean/master/scripts/bootstrap.sh | sh -s -- --agent claude
```

```powershell
irm https://raw.githubusercontent.com/BookHsu/Libro.AgentWCAG.clean/master/scripts/bootstrap.ps1 | iex
```

If you want to pass parameters directly in PowerShell:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/BookHsu/Libro.AgentWCAG.clean/master/scripts/bootstrap.ps1))) -Agent claude
```

`bootstrap.sh` supports `--agent / --repo / --ref / --dest / --force`, and `--agent` is required.
If `bootstrap.ps1` does not receive `-Agent`, it prompts interactively; for non-interactive installs, use the scriptblock form above so parameters can be passed explicitly.

### Claude Plugin Installation

If you use Claude Code, you can also install directly via the plugin marketplace:

```text
/plugin marketplace add BookHsu/Libro.AgentWCAG.clean
/plugin install libro-wcag@libro-wcag-marketplace
```

After installation, invoke with `/libro-wcag:libro-wcag` or let Claude activate it automatically based on context.

### Gemini Workspace Skill

If you open this repository directly in a Gemini workspace, Gemini can auto-discover `libro-wcag` from [.gemini/skills/libro-wcag/SKILL.md](/c:/Source/Libro.AgentWCAG.clean/.gemini/skills/libro-wcag/SKILL.md).

To install the same workspace skill into another project root, run:

```powershell
python .\scripts\install-agent.py --agent gemini --workspace-root .
```

### Claude add-dir / Git Submodule

If you prefer vendoring the skill into a target repository, use:

```bash
git submodule add https://github.com/BookHsu/Libro.AgentWCAG.clean.git .vendor/libro-wcag
claude --add-dir .vendor/libro-wcag
```

For a persisted sample, see [settings.add-dir.sample.json](/c:/Source/Libro.AgentWCAG.clean/docs/examples/claude/settings.add-dir.sample.json).

### GitHub Actions Reusable Workflow

Other repositories can reuse [install-skill.yml](/c:/Source/Libro.AgentWCAG.clean/.github/workflows/install-skill.yml) directly:

```yaml
jobs:
  setup:
    uses: BookHsu/Libro.AgentWCAG.clean/.github/workflows/install-skill.yml@v1
    with:
      agent: claude
```

See [install-skill-consumer-sample.yml](/c:/Source/Libro.AgentWCAG.clean/docs/examples/ci/install-skill-consumer-sample.yml) for a complete example.

### gh release download

If you prefer downloading release assets with GitHub CLI, see [gh-release-download-sample.md](/c:/Source/Libro.AgentWCAG.clean/docs/examples/ci/gh-release-download-sample.md).

### 2. Verify The Installation

```powershell
python .\scripts\doctor-agent.py --agent codex
```

### 3. Start Using It

In Codex, invoke:

```text
$libro-wcag
```

If you use Claude, Gemini, or Copilot, load the corresponding `prompt-template.md` under each adapter as the platform entrypoint.

## How To Use The Skill

Libro.AgentWCAG is not just a single command. It is a shared skill contract that different AI agents can follow. In practice, you choose whether you want to audit only, get suggestions, or apply fixes.

### In Codex

After installation, invoke:

```text
$libro-wcag
```

Common ways to use it:

- Ask it to inspect a page or component for WCAG issues
- Ask it to report issues only without changing files
- Ask it to propose fixes before you decide whether to apply them
- Ask it to apply safe fixes to supported local files only when you explicitly want changes

### In Other Agents

- `Claude`: load `skills/libro-wcag/adapters/claude/prompt-template.md`
- `Gemini`: load `skills/libro-wcag/adapters/gemini/prompt-template.md`
- `Copilot`: load `skills/libro-wcag/adapters/copilot/prompt-template.md`

The usual approach is to place the adapter's `prompt-template.md` into the instruction entrypoint for that platform, such as a project prompt, system prompt, custom instruction, or agent wrapper.

### Recommended Interaction Pattern

- Start with `audit-only` when you want a clean accessibility review
- Use `suggest-only` when you want remediation ideas before changing files
- Move to `apply-fixes` only when you want the changes carried out

This keeps review and modification separate, which makes the workflow easier to control.

## Install From A Release

If you are consuming a packaged release, install directly from release assets:

```powershell
pwsh -File .\scripts\install-latest.ps1 -ReleaseBase .\dist\release -Agent codex
```

Or install from a published GitHub Release:

```powershell
pwsh -File .\scripts\install-latest.ps1 -ReleaseBase https://github.com/<owner>/<repo>/releases/download/vX.Y.Z -Agent codex
```

The install flow automatically verifies `latest-release.json`, the release manifest, and `sha256`, then runs an integrity check after installation.

## Release readiness

- `product_version` comes from `pyproject.toml`
- `source_revision` can be injected through `LIBRO_AGENTWCAG_SOURCE_REVISION`
- release packaging is handled by `scripts/package-release.py`
- key assets include `libro-wcag-<version>-all-in-one.zip` and `libro-wcag-<version>-sha256sums.txt`
- the release-consumer shortest path uses `install-latest.ps1` and `run-release-adoption-smoke.py`
- Release-consumer shortest path and Release-consumer quickstart are documented in `docs/release/adoption-smoke-guide.md`
- release and rollback references live in `docs/release/ga-release-workflow.md`, `docs/release/ga-definition.md`, and `docs/release/rollback-playbook.md`
- the main operator guide is `docs/release/release-playbook.md`
- see these docs for scope, prompts, resilient execution, CI examples, and scanner governance:
- `docs/release/apply-fixes-scope.md`
- `docs/release/prompt-invocation-templates.md`
- `docs/release/resilient-run-patterns.md`
- `docs/examples/ci/github-actions-wcag-ci-sample.yml`
- `docs/release/real-scanner-ci-lane.md`
- `docs/release/baseline-governance.md`
- `docs/release/advanced-ci-gates.md`
- policy bundle material lives under `docs/policy-bundles/`
- use `python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity` for post-install integrity checks

## Where It Fits Best

- Teams that want accessibility review inside AI-assisted workflows
- Teams that need one shared contract across multiple agents
- Projects that need installable, verifiable, versioned skill delivery
- Adoption paths that want to start with safe, predictable remediation

## Project Structure

- `skills/libro-wcag`: installable skill payload
- `skills/libro-wcag/adapters/openai-codex`: Codex adapter
- `skills/libro-wcag/adapters/claude`: Claude adapter
- `skills/libro-wcag/adapters/gemini`: Gemini adapter
- `skills/libro-wcag/adapters/copilot`: Copilot adapter
- `scripts/install-agent.py`: installer
- `scripts/doctor-agent.py`: health check and integrity verification
- `scripts/uninstall-agent.py`: uninstaller

## Common Commands

Install:

```powershell
python .\scripts\install-agent.py --agent codex
```

Verify:

```powershell
python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity
```

Uninstall:

```powershell
python .\scripts\uninstall-agent.py --agent codex
```

Local validation:

```powershell
python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-wcag --validate-policy-bundles
```

## Documentation

- Release workflow: [docs/release/ga-release-workflow.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/ga-release-workflow.md)
- Release playbook: [docs/release/release-playbook.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/release-playbook.md)
- Install and smoke guide: [docs/release/adoption-smoke-guide.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/adoption-smoke-guide.md)
- `apply-fixes` scope: [docs/release/apply-fixes-scope.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/apply-fixes-scope.md)
- Supported environments: [docs/release/supported-environments.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/supported-environments.md)
- Test plan: [TESTING-PLAN.md](/c:/Source/Libro.AgentWCAG.clean/TESTING-PLAN.md)
