# AGENTS.md

This file provides guidance to all AI agents when working with code in this repository.

## 專案概述

Libro.AgentWCAG 是一套跨代理的 WCAG 網頁無障礙 skill repository。它用同一份 vendor-neutral contract，讓 Codex、Claude、Gemini、Copilot 能以一致方式執行無障礙稽核、提出修正建議，並在明確授權下套用安全範圍內的自動修正。核心商業邏輯以 Python 實作，各 AI 平台僅有薄薄一層 prompt 語法轉接器（adapter）。

## 建置與測試指令

```bash
# 執行所有單元測試
python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"

# 執行單一測試檔案
python -m unittest skills.libro-wcag.scripts.tests.test_workflow

# 執行單一測試方法（點分隔路徑）
python -m unittest skills.libro-wcag.scripts.tests.test_workflow.TestWorkflow.test_some_method

# 驗證 skill 合約（檔案結構、schema、policy）
python scripts/validate_skill.py skills/libro-wcag

# 安裝 skill 至代理平台（claude | codex | gemini | copilot | all）
python scripts/libro.py install codex

# 驗證安裝完整性
python scripts/libro.py doctor codex
```

需要 Python 3.12+。建置時唯一的 Python 相依套件為 `pyyaml`。

## 架構

### Vendor-Neutral Contract

一切以 `skills/libro-wcag/SKILL.md` 為中心——這是所有代理必須遵循的標準輸入/輸出合約。輸入為 JSON 物件，包含 `task_mode`、`execution_mode`、`wcag_version`、`conformance_level`、`target`、`output_language`。輸出一律為 Markdown 表格 + JSON 報告，格式固定。

### 主要目錄結構

- **skills/libro-wcag/scripts/** — 核心 Python 邏輯：工作流程編排（`wcag_workflow.py`）、掃描器執行（`run_accessibility_audit.py`）、自動修正引擎（`auto_fix.py`）、修正策略庫（`remediation_library.py`）、報告正規化（`normalize_report.py`）、共用常數（`shared_constants.py`）、重寫輔助函式（`rewrite_helpers.py`）。
- **skills/libro-wcag/adapters/{claude,copilot,gemini,openai-codex}/** — 各平台 prompt 模板。每個包含 `prompt-template.md`、`usage-example.md`、`failure-guide.md`、`e2e-example.md`。Adapter 不得改變核心輸出語意。
- **skills/libro-wcag/references/** — 共用規格：`core-spec.md`（欄位定義）、`wcag-citations.md`（W3C 官方 URL）、`adapter-mapping.md`（跨平台對應規則）、`framework-patterns-*.md`（React/Vue/Next.js 指引）。
- **skills/libro-wcag/schemas/** — 報告驗證用 JSON Schema（`wcag-report-1.0.0.schema.json`）。
- **mcp-server/** — FastMCP 伺服器，公開 `libro_wcag_audit`、`libro_wcag_suggest`、`libro_wcag_normalize` 工具。
- **scripts/** — CLI 安裝器（`libro.py`、`install-agent.py`）、驗證（`doctor-agent.py`）、移除、發佈腳本。
- **bin/libro.js** — Node CLI 進入點（npm 套件名稱：`librowcag-cli`）。

### 執行模式

三種模式決定 skill 的行為：

- `audit-only` — 僅掃描並回報問題
- `suggest-only`（預設）— 回報問題 + 修正建議，不修改檔案
- `apply-fixes` — 掃描、建議，並對支援的本地檔案（`.html`、`.htm`、`.xhtml`、`.jsx`、`.tsx`、`.vue`）套用安全重寫

### 自動修正引擎

`auto_fix.py` 針對一組已驗證安全的規則執行 HTML/CSS/JS 重寫（缺少 lang、alt 文字、按鈕/連結名稱、表單標籤、文件標題、清單語意、表格標題、meta refresh 移除、不安全的 viewport 設定）。它會產出 unified diff 以供驗證。擴充自動修正時，僅限可證明安全的模式，並須加上對應測試。

### 出處追蹤（Provenance）

`shared_constants.py` 追蹤產品版本、git revision 與建置時間戳。`package-provenance.json` 在 `npm prepack` 時產生，用於發佈完整性驗證。版本來源以 `pyproject.toml` 為主，fallback 依序為 `package.json` 和 `package-provenance.json`。

## 關鍵不變式

- **Adapter 純淨性**：Adapter 僅包含 prompt 語法。不得加入會改變核心輸出欄位名稱、欄位順序、狀態詞彙或 JSON key 的商業邏輯。
- **輸出合約穩定性**：Markdown 欄位順序（`Issue ID | Source | WCAG Version | Level | SC | Current | Fix | Changed Target | Citation | Status`）與 JSON 頂層 key（`run_meta`、`target`、`standard`、`findings[]`、`fixes[]`、`citations[]`、`summary`）皆為固定格式。
- **預設值**：`execution_mode=suggest-only`、`wcag_version=2.1`、`conformance_level=AA`、`output_language=zh-TW`。
- **雙版本同步**：`pyproject.toml` 與 `package.json` 的版本字串須保持一致。
- **W3C 引用**：每個重大發現都必須附上官方 WCAG Understanding URL。

## CI

GitHub Actions（`test.yml`）：在 push 至 master 及所有 PR 時執行單元測試 + skill 合約驗證。發佈工作流（`release.yml`）在 `v*` tag push 時觸發：驗證、打包、冒煙測試，然後以 OIDC provenance 發佈至 npm。
