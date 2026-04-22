# Libro.AgentWCAG

Libro.AgentWCAG 是一套跨代理的 WCAG 網頁無障礙 skill repository。它用同一份 vendor-neutral contract，讓 Codex、Claude、Gemini、Copilot 能以一致方式執行無障礙稽核、提出修正建議，並在明確授權下套用安全範圍內的自動修正。

## 專案的用途與說明

這個專案的目標不是再提供另一個零散工具，而是把「稽核、建議、部分自動修正、報告輸出、安裝驗證」整理成可安裝、可測試、可發佈的標準工作流。

- 同一份 contract，可對接多種 AI agent
- 同一套執行模式，可覆蓋 audit、suggest、apply-fixes
- 同一套 CLI，可直接跑單檔頁面、批次掃描與報告彙總
- 同一份固定輸出 contract，維持 Markdown + JSON 報告一致性

## 前置需求

- Python 3.12+
- 若要執行真實掃描：Node.js 18+、`npx`、`@axe-core/cli`、`lighthouse`

確認 Python：

```powershell
python --version
```

安裝 Python：

```sh
brew install python3                         # macOS
sudo apt update && sudo apt install python3 # Ubuntu / Debian
winget install Python.Python.3.12           # Windows
```

檢查掃描器工具鏈：

```powershell
python .\scripts\libro.py audit --preflight-only
python .\scripts\doctor-agent.py --agent codex --check-scanners
```

## 安裝方式

### Claude Marketplace (Claude Code)

Coming soon. Marketplace 指令先保留占位：

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

相容性保留的既有範例：

```powershell
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
python .\scripts\libro.py install codex
python .\scripts\libro.py doctor codex
```

既有 clone + CLI 範例：

```powershell
python .\scripts\libro.py install claude
python .\scripts\libro.py doctor claude
```

驗證與移除：

```powershell
python .\scripts\libro.py doctor codex --verify-manifest-integrity
python .\scripts\libro.py doctor codex --check-scanners
python .\scripts\libro.py remove codex
```

```powershell
python .\scripts\libro.py remove claude
```

## CLI Quick Start

### 單一 HTML 或 URL 稽核

```powershell
python .\scripts\libro.py audit .\src\index.html
python .\scripts\libro.py audit https://example.com
python .\scripts\libro.py audit .\src\index.html --execution-mode audit-only
python .\scripts\libro.py audit .\src\index.html --execution-mode apply-fixes --dry-run
python .\scripts\libro.py audit --print-examples
```

### 批次掃描

```powershell
python .\scripts\libro.py scan .\src\pages --parallel 4
python .\scripts\libro.py scan .\src\pages --execution-mode audit-only --output-dir .\wcag-reports
python .\scripts\libro.py scan --print-examples
```

### 彙總報告

```powershell
python .\scripts\libro.py report .\wcag-reports --format terminal
python .\scripts\libro.py report .\wcag-reports --format html --output .\out\wcag-summary.html
python .\scripts\libro.py report .\wcag-reports --format terminal --no-color
python .\scripts\libro.py report --print-examples
```

### 直接呼叫核心 audit runner

```powershell
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --target .\src\index.html
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --target .\src\index.html --summary-only --artifacts minimal
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --print-examples
```

## 執行模式與預設值

預設 contract 值：

- `execution_mode=suggest-only`
- `wcag_version=2.1`
- `conformance_level=AA`
- `output_language=zh-TW`

三種執行模式：

| 模式 | 會找問題 | 會給修正建議 | 會改檔 |
| --- | --- | --- | --- |
| `audit-only` | 是 | 否 | 否 |
| `suggest-only` | 是 | 是 | 否 |
| `apply-fixes` | 是 | 是 | 是，僅限支援的本機檔案 |

`apply-fixes` 目前僅支援安全的一階重寫，包含 `.html`、`.htm`、`.xhtml`、`.jsx`、`.tsx`、`.vue` 等本機目標。

## 使用方式

Libro.AgentWCAG 的核心不是單一指令，而是一套可被不同 AI agent 共用的 skill contract。實際使用時，你可以依照目前任務選擇「只稽核」、「提出建議」或「直接修正」。

使用範例：

```text
Audit only
請用 audit-only 模式檢查 https://example.com，WCAG 2.1 AA。

Suggest only
請用 suggest-only 模式檢查 src/page.html，並提供修正建議，但不要改檔。

Apply fixes
請用 apply-fixes 模式檢查 src/page.html，並在安全範圍內直接修正可處理的問題。
```

## 報告輸出

單次稽核預設會輸出：

- `wcag-report.json`
- `wcag-report.md`
- `artifact-manifest.json`
- `schemas/wcag-report-<version>.schema.json`

若啟用對應功能，還可能輸出：

- `wcag-report.sarif`
- `wcag-fixes.diff`
- `wcag-fixed-report.snapshot.json`
- `wcag-effective-policy.json`
- `replay-summary.json`
- `scanner-stability.json`
- `debt-trend.json`

若要減少 sidecar artifacts，可使用：

```powershell
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --target .\src\index.html --artifacts minimal
```

## 文件入口

- [docs/README.md](docs/README.md): 文件索引
- [docs/testing/testing-playbook.md](docs/testing/testing-playbook.md): 測試與 smoke 指引
- [docs/testing/test-matrix.md](docs/testing/test-matrix.md): 測試矩陣
- [skills/libro-wcag/references/cli-reference.md](skills/libro-wcag/references/cli-reference.md): 完整 CLI 參數

## 使用限制

- MCP server 只支援唯讀稽核與建議，不支援 `apply-fixes`
- `apply-fixes` 只會處理已驗證安全的 rewrite 類型
- 真實掃描依賴本機 scanner toolchain；若缺工具，可先用 `--preflight-only`

## License

MIT. See [LICENSE](LICENSE).
