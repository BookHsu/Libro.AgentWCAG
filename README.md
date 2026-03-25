# Libro.AgentWCAG

Libro.AgentWCAG 是一套跨代理的 WCAG 網頁無障礙 skill repository。它用同一份 vendor-neutral contract，讓 Codex、Claude、Gemini、Copilot 能以一致方式執行無障礙稽核、提出修正建議，並在明確授權下套用安全範圍內的自動修正。

## 專案的用途與說明

做網頁無障礙，真正麻煩的通常不是「找不到工具」，而是不同 agent、不同流程、不同輸出格式之間缺乏一致性。Libro.AgentWCAG 的目標，是把這件事整理成可安裝、可驗證、可發佈、可落地的標準工作流。

- 同一份 contract，可對接多種 AI agent
- 同一套任務模式，可涵蓋稽核、建議與部分修正
- 同一條 release 路徑，可支援安裝、驗證與版本管理

## 能幫你做到什麼

- 快速檢查頁面是否存在 WCAG 無障礙問題
- 以一致格式產出問題摘要與修正建議
- 在明確要求修改時，對支援的本機檔案執行安全的一階修正
- 讓團隊在不同 agent 之間維持相同的工作方式與輸出預期

## 前置需求

需先安裝 Python 3。

```powershell
python --version
```

```sh
brew install python3                         # macOS
sudo apt update && sudo apt install python3 # Ubuntu / Debian
winget install Python.Python.3.12           # Windows
```

## 安裝方式

### Claude Marketplace (Claude Code)

```text
/plugin marketplace add BookHsu/Libro.AgentWCAG
/plugin install libro-wcag@libro-wcag-marketplace
```

### npm CLI

```powershell
npm install -g libro-cli
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

驗證與移除：

```powershell
python .\scripts\libro.py doctor claude --verify-manifest-integrity
python .\scripts\libro.py remove claude
```

## 使用方式

Libro.AgentWCAG 的核心不是單一指令，而是一套可被不同 AI agent 共用的 skill contract。實際使用時，你可以依照目前任務選擇「只稽核」、「提出建議」或「直接修正」。

三種工作模式：

| 模式 | 會找問題 | 會給修正建議 | 會改檔 |
|---|---|---|---|
| `audit-only` | 是 | 否 | 否 |
| `suggest-only` | 是 | 是 | 否 |
| `apply-fixes` | 是 | 是 | 是，僅限支援的本機檔案 |

使用範例：

```text
Audit only
請用 audit-only 模式檢查 https://example.com，WCAG 2.1 AA。

Suggest only
請用 suggest-only 模式檢查 src/page.html，並提供修正建議，但不要改檔。

Apply fixes
請用 apply-fixes 模式檢查 src/page.html，並在安全範圍內直接修正可處理的問題。
```

- 稽核頁面時，先用 `audit-only`
- 想看修法但還不想改檔時，使用 `suggest-only`
- 確認要落地修改時，再使用 `apply-fixes`

這樣可以先把問題看清楚，再進入修改流程，避免過早自動改動。
