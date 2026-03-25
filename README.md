# Libro.AgentWCAG

Libro.AgentWCAG 是一套跨代理的 WCAG 網頁無障礙 skill repository。它用同一份 vendor-neutral contract，讓 Codex、Claude、Gemini、Copilot 能以一致方式執行無障礙稽核、提出修正建議，並在明確授權下套用安全範圍內的自動修正。

## 為什麼是 Libro.AgentWCAG

做網頁無障礙，真正麻煩的通常不是「找不到工具」，而是不同 agent、不同流程、不同輸出格式之間缺乏一致性。Libro.AgentWCAG 的目標，是把這件事整理成可安裝、可驗證、可發佈、可落地的標準工作流。

- 同一份 contract，可對接多種 AI agent
- 同一套任務模式，可涵蓋稽核、建議與部分修正
- 同一條 release 路徑，可支援安裝、驗證與版本管理

## 能幫你做到什麼

- 快速檢查頁面是否存在 WCAG 無障礙問題
- 以一致格式產出問題摘要與修正建議
- 在明確要求修改時，對支援的本機檔案執行安全的一階修正
- 讓團隊在不同 agent 之間維持相同的工作方式與輸出預期

## 支援的 AI agent

- Codex
- Claude
- Gemini
- Copilot

## 三種工作模式

- `audit-only`：只找出問題
- `suggest-only`：找出問題並提出修正建議，但不改檔
- `apply-fixes`：在明確授權下，對支援的本機檔案套用安全修正

## 快速開始

### 最短路徑

```powershell
git clone https://github.com/BookHsu/Libro.AgentWCAG.clean.git
cd Libro.AgentWCAG.clean
python .\scripts\libro.py install claude
python .\scripts\libro.py doctor claude
```

安裝到指定 skill 位置時，三大 agent 都用同一組命令：

```powershell
python .\scripts\libro.py install claude
python .\scripts\libro.py install gemini
python .\scripts\libro.py install copilot
```

驗證與移除：

```powershell
python .\scripts\libro.py doctor claude --verify-manifest-integrity
python .\scripts\libro.py remove claude
```

### 其他命令入口

如果你偏好 wrapper：

```powershell
.\scripts\libro.ps1 install claude
.\scripts\libro.ps1 doctor claude
```

```sh
./scripts/libro.sh install claude
./scripts/libro.sh doctor claude
```

### 進階安裝與整合

如果你不想先 clone repo，也可以直接 bootstrap：

```sh
curl -sL https://raw.githubusercontent.com/BookHsu/Libro.AgentWCAG.clean/master/scripts/bootstrap.sh | sh -s -- --agent claude
```

```powershell
irm https://raw.githubusercontent.com/BookHsu/Libro.AgentWCAG.clean/master/scripts/bootstrap.ps1 | iex
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/BookHsu/Libro.AgentWCAG.clean/master/scripts/bootstrap.ps1))) -Agent claude
```

如果你需要 workspace MCP，`mcp-server/server.py` 提供單一 `libro-wcag` MCP server，可同時服務 Claude、Copilot、Gemini。

```powershell
python -m pip install -r .\mcp-server\requirements.txt
python .\scripts\libro.py install claude --workspace-root . --emit-mcp-config claude
python .\scripts\libro.py install gemini --workspace-root . --emit-mcp-config gemini
python .\scripts\libro.py install copilot --workspace-root . --emit-mcp-config copilot
```

Sample config：

- Claude: [mcp.sample.json](/c:/Source/Libro.AgentWCAG.clean/docs/examples/claude/mcp.sample.json)
- Copilot: [mcp.sample.json](/c:/Source/Libro.AgentWCAG.clean/docs/examples/copilot/mcp.sample.json)
- Gemini: [settings.mcp.sample.json](/c:/Source/Libro.AgentWCAG.clean/docs/examples/gemini/settings.mcp.sample.json)

## Skill 使用方式

Libro.AgentWCAG 的核心不是單一指令，而是一套可被不同 AI agent 共用的 skill contract。實際使用時，你可以依照目前任務選擇「只稽核」、「提出建議」或「直接修正」。

### 在 Codex 中使用

安裝完成後，可直接呼叫：

```text
$libro-wcag
```

常見使用方式：

- 請它檢查某個頁面或元件的 WCAG 問題
- 請它只列出問題，不修改檔案
- 請它先提出修正建議，再由你決定是否套用
- 在你明確授權下，請它對支援的本機檔案執行安全修正

### 在其他 agent 中使用

- `Claude`：載入 `skills/libro-wcag/adapters/claude/prompt-template.md`
- `Gemini`：載入 `skills/libro-wcag/adapters/gemini/prompt-template.md`
- `Copilot`：載入 `skills/libro-wcag/adapters/copilot/prompt-template.md`

做法是把對應 adapter 的 `prompt-template.md` 放進你使用的平台指令入口，例如 project prompt、system prompt、custom instruction 或 agent wrapper，讓該平台依同一份 contract 執行。

### 建議的互動方式

- 稽核頁面時，先用 `audit-only`
- 想看修法但還不想改檔時，使用 `suggest-only`
- 確認要落地修改時，再使用 `apply-fixes`

這樣可以先把問題看清楚，再進入修改流程，避免過早自動改動。

## 從 release 安裝

如果你是 release 使用者，建議直接從已封裝好的資產安裝：

```powershell
pwsh -File .\scripts\install-latest.ps1 -ReleaseBase .\dist\release -Agent codex
```

或從已發佈的 GitHub Release 安裝：

```powershell
pwsh -File .\scripts\install-latest.ps1 -ReleaseBase https://github.com/<owner>/<repo>/releases/download/vX.Y.Z -Agent codex
```

安裝流程會自動驗證 `latest-release.json`、release manifest 與 `sha256`，並在完成後執行完整性檢查。

## Release readiness

- `product_version` 來源是 `pyproject.toml`
- `source_revision` 可由 `LIBRO_AGENTWCAG_SOURCE_REVISION` 注入
- release 封裝腳本是 `scripts/package-release.py`
- 主要資產包含 `libro-wcag-<version>-all-in-one.zip` 與 `libro-wcag-<version>-sha256sums.txt`
- release consumer shortest path 使用 `install-latest.ps1` 與 `run-release-adoption-smoke.py`
- Release-consumer shortest path 與 Release-consumer quickstart 參考 `docs/release/adoption-smoke-guide.md`
- 釋出與回滾流程參考 `docs/release/ga-release-workflow.md`、`docs/release/ga-definition.md`、`docs/release/rollback-playbook.md`
- 詳細操作手冊參考 `docs/release/release-playbook.md`
- `apply-fixes` 範圍、prompt 樣板、resilient run pattern、CI 範例與 real scanner lane 分別在：
- `docs/release/apply-fixes-scope.md`
- `docs/release/prompt-invocation-templates.md`
- `docs/release/resilient-run-patterns.md`
- `docs/examples/ci/github-actions-wcag-ci-sample.yml`
- `docs/release/real-scanner-ci-lane.md`
- `docs/release/baseline-governance.md`
- `docs/release/advanced-ci-gates.md`
- policy bundle 說明位於 `docs/policy-bundles/`
- 檢查命令關鍵字：`doctor-agent.py --verify-manifest-integrity`
- 安裝後可用 `python .\scripts\libro.py doctor claude --verify-manifest-integrity` 驗證完整性

## 適合哪些情境

- 想把無障礙檢查納入 AI 協作流程的團隊
- 想在多種 agent 之間共用同一套規格與輸出格式的團隊
- 需要可安裝、可驗證、可版本化管理的 skill 發佈流程
- 希望先從安全、可預期的自動修正開始導入的專案

## 專案結構

- `skills/libro-wcag`：可安裝的 skill 主體
- `skills/libro-wcag/adapters/openai-codex`：Codex adapter
- `skills/libro-wcag/adapters/claude`：Claude adapter
- `skills/libro-wcag/adapters/gemini`：Gemini adapter
- `skills/libro-wcag/adapters/copilot`：Copilot adapter
- `scripts/install-agent.py`：安裝工具
- `scripts/doctor-agent.py`：健康檢查與完整性驗證
- `scripts/uninstall-agent.py`：卸載工具
- `scripts/libro.py`：統一 CLI 入口

## 常用指令

安裝：

```powershell
python .\scripts\libro.py install claude
```

驗證：

```powershell
python .\scripts\libro.py doctor claude --verify-manifest-integrity
```

卸載：

```powershell
python .\scripts\libro.py remove claude
```

本地驗證：

```powershell
python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-wcag --validate-policy-bundles
```

## 文件入口

- Release 流程：[docs/release/ga-release-workflow.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/ga-release-workflow.md)
- 發佈操作手冊：[docs/release/release-playbook.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/release-playbook.md)
- 安裝與 smoke 指引：[docs/release/adoption-smoke-guide.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/adoption-smoke-guide.md)
- `apply-fixes` 範圍說明：[docs/release/apply-fixes-scope.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/apply-fixes-scope.md)
- 支援環境：[docs/release/supported-environments.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/supported-environments.md)
- 測試計畫：[TESTING-PLAN.md](/c:/Source/Libro.AgentWCAG.clean/TESTING-PLAN.md)

## 英文版

- [README.en.md](/c:/Source/Libro.AgentWCAG.clean/README.en.md)
