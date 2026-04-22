# Libro.AgentWCAG

Libro.AgentWCAG is a cross-agent WCAG web accessibility skill repository. It keeps one vendor-neutral contract so Codex, Claude, Gemini, and Copilot can perform consistent audits, remediation guidance, and explicitly authorized safe first-pass fixes.

## What This Project Is For

The goal is not to add one more isolated checker. The goal is to package accessibility audit, guidance, selected auto-fixes, report output, installation, and verification into one installable and testable workflow.

- One contract across multiple AI agents
- One execution model covering audit, suggest, and apply-fixes
- One CLI for single-target audits, batch scans, and aggregate reports
- One stable Markdown + JSON report contract

## Prerequisites

- Python 3.12+
- For real scanner runs: Node.js 18+, `npx`, `@axe-core/cli`, and `lighthouse`

Check Python:

```powershell
python --version
```

Install Python:

```sh
brew install python3                         # macOS
sudo apt update && sudo apt install python3 # Ubuntu / Debian
winget install Python.Python.3.12           # Windows
```

Check scanner toolchain:

```powershell
python .\scripts\libro.py audit --preflight-only
python .\scripts\doctor-agent.py --agent codex --check-scanners
```

## Installation

### Claude Marketplace

Coming soon. Placeholder commands are kept here for future availability:

```text
/plugin marketplace add BookHsu/Libro.AgentWCAG
/plugin install libro-wcag@libro-wcag-marketplace
```

### npm CLI

```powershell
npm install -g librowcag-cli
libro install claude
libro install gemini
libro install copilot
libro install codex
libro doctor codex
```

### Clone + CLI

```powershell
git clone https://github.com/BookHsu/Libro.AgentWCAG.git
cd Libro.AgentWCAG
python .\scripts\libro.py install codex
python .\scripts\libro.py doctor codex
```

Verify and remove:

```powershell
python .\scripts\libro.py doctor codex --verify-manifest-integrity
python .\scripts\libro.py doctor codex --check-scanners
python .\scripts\libro.py remove codex
```

## CLI Quick Start

### Audit a single HTML file or URL

```powershell
python .\scripts\libro.py audit .\src\index.html
python .\scripts\libro.py audit https://example.com
python .\scripts\libro.py audit .\src\index.html --execution-mode audit-only
python .\scripts\libro.py audit .\src\index.html --execution-mode apply-fixes --dry-run
python .\scripts\libro.py audit --print-examples
```

### Batch scan

```powershell
python .\scripts\libro.py scan .\src\pages --parallel 4
python .\scripts\libro.py scan .\src\pages --execution-mode audit-only --output-dir .\wcag-reports
python .\scripts\libro.py scan --print-examples
```

### Aggregate reports

```powershell
python .\scripts\libro.py report .\wcag-reports --format terminal
python .\scripts\libro.py report .\wcag-reports --format html --output .\out\wcag-summary.html
python .\scripts\libro.py report .\wcag-reports --format terminal --no-color
python .\scripts\libro.py report --print-examples
```

### Call the core audit runner directly

```powershell
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --target .\src\index.html
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --target .\src\index.html --summary-only --artifacts minimal
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --print-examples
```

## Execution Modes and Defaults

Default contract values:

- `execution_mode=suggest-only`
- `wcag_version=2.1`
- `conformance_level=AA`
- `output_language=zh-TW`

Execution modes:

| Mode | Finds issues | Proposes fixes | Writes files |
| --- | --- | --- | --- |
| `audit-only` | Yes | No | No |
| `suggest-only` | Yes | Yes | No |
| `apply-fixes` | Yes | Yes | Yes, for supported local files only |

`apply-fixes` currently supports safe first-pass rewrites on local `.html`, `.htm`, `.xhtml`, `.jsx`, `.tsx`, and `.vue` targets.

## Report Outputs

A normal audit run writes:

- `wcag-report.json`
- `wcag-report.md`
- `artifact-manifest.json`
- `schemas/wcag-report-<version>.schema.json`

Additional files may appear when the related features are enabled:

- `wcag-report.sarif`
- `wcag-fixes.diff`
- `wcag-fixed-report.snapshot.json`
- `wcag-effective-policy.json`
- `replay-summary.json`
- `scanner-stability.json`
- `debt-trend.json`

To reduce sidecar artifacts:

```powershell
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --target .\src\index.html --artifacts minimal
```

## Documentation Entry Points

- [docs/README.md](docs/README.md): documentation index
- [docs/testing/testing-playbook.md](docs/testing/testing-playbook.md): testing and smoke guidance
- [docs/testing/test-matrix.md](docs/testing/test-matrix.md): test matrix
- [skills/libro-wcag/references/cli-reference.md](skills/libro-wcag/references/cli-reference.md): complete CLI reference

## Constraints

- The MCP server supports read-only audit and guidance, not `apply-fixes`
- `apply-fixes` only covers reviewed safe rewrite classes
- Real scans depend on local scanner tooling; use `--preflight-only` first if needed

## License

MIT. See [LICENSE](LICENSE).
