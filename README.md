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

## 安裝方式

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

## 使用方式

Libro.AgentWCAG 的核心不是單一指令，而是一套可被不同 AI agent 共用的 skill contract。實際使用時，你可以依照目前任務選擇「只稽核」、「提出建議」或「直接修正」。

三種工作模式：

- `audit-only`：只找出問題
- `suggest-only`：找出問題並提出修正建議，但不改檔
- `apply-fixes`：在明確授權下，對支援的本機檔案套用安全修正

Codex 安裝完成後可直接呼叫：

```text
$libro-wcag
```

- 稽核頁面時，先用 `audit-only`
- 想看修法但還不想改檔時，使用 `suggest-only`
- 確認要落地修改時，再使用 `apply-fixes`

這樣可以先把問題看清楚，再進入修改流程，避免過早自動改動。
