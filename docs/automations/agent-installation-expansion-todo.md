# Agent Installation Expansion TODO

此文件整理後續安裝能力擴充的實體檔案待辦。現階段主軸已收斂為：

- 三大 agent `Claude`、`Gemini`、`Copilot` 都要能簡單安裝
- 對外以單一 CLI 入口為主，不再讓使用者先理解多條安裝腳本
- README 要優先呈現最短安裝路徑，進階模式退到次要段落
- 不新增 package manager distribution，維持 repo 內簡單交付

## 目前狀態

- [x] Phase 1 已完成：Gemini workspace skill、Claude plugin manifests、reusable workflow、submodule/add-dir 與 `gh release download` 文件樣板已落地
- [x] Phase 2 已完成：`stdio` MCP server 與三個 tool wrapper 已落地
- [x] Phase 3 已完成：Claude/Copilot/Gemini MCP sample configs、installer MCP config emission、README/adapter 文件同步已落地
- [ ] 下一階段改為產品化安裝體驗：單一 CLI、簡化 README、Claude repo-open 即用

## 原則

- `Libro.AgentWCAG` repo/product 名稱維持不變。
- canonical skill id 維持 `libro-wcag`。
- 新機制優先避免複製多份核心 contract；若必須複製，需補一致性檢查。
- Claude plugin / marketplace 與 Gemini extension 機制是否可正式採用，仍需先做手動驗證。
- 使用者主路徑應優先是簡短指令，而不是 Python 腳本檔名。

## 新主線：Unified CLI + Simple Install

目標：讓 `Claude`、`Gemini`、`Copilot` 使用者都能用一組簡短命令完成安裝與驗證，並讓 repo 首頁優先呈現這條路。

### 實體檔案 TODO

- [ ] 新增 `scripts/libro.py`
- [ ] 新增 `scripts/libro.ps1`
- [ ] 新增 `scripts/libro.sh`
- [ ] 更新 `README.md`，改成以 unified CLI 為主的 quick start
- [ ] 更新 `README.en.md`，改成以 unified CLI 為主的 quick start
- [ ] 更新 `skills/libro-wcag/adapters/claude/usage-example.md`
- [ ] 更新 `skills/libro-wcag/adapters/gemini/usage-example.md`
- [ ] 更新 `skills/libro-wcag/adapters/copilot/usage-example.md`
- [ ] 視需要更新 `skills/libro-wcag/adapters/openai-codex/usage-example.md`
- [ ] 新增 unified CLI contract tests 到 `skills/libro-wcag/scripts/tests/test_repo_scripts.py`
- [ ] 新增 unified CLI / README 靜態檢查到 `skills/libro-wcag/scripts/tests/test_repo_contracts.py`

### CLI 功能範圍

- [ ] `install <agent>`：安裝 skill
- [ ] `doctor <agent>`：驗證安裝
- [ ] `remove <agent>`：移除安裝
- [ ] 支援 `claude`、`gemini`、`copilot`、`codex`、`all`
- [ ] 支援 `--workspace-root`
- [ ] 支援 `--emit-mcp-config`
- [ ] 支援 `--dest`
- [ ] 支援 `--force`

### 文件目標

- [ ] README 首屏只保留「安裝」「驗證」「Claude repo-open / plugin」「進階選項入口」
- [ ] 將 bootstrap / reusable workflow / MCP / submodule 等收斂到 secondary sections
- [ ] 對三大 agent 提供最短指令示例
- [ ] 明確標出 `Claude`、`Gemini`、`Copilot` 的最推薦安裝路徑

## Claude Repo-Open 體驗

目標：repo 被 Claude 開啟後，盡量不必先跑 installer 就能發現 `libro-wcag`。

### 實體檔案 TODO

- [ ] 新增 `.claude/skills/libro-wcag/SKILL.md`
- [ ] 規劃 `.claude/skills/libro-wcag/SKILL.md` 與 `skills/libro-wcag/SKILL.md` 的同步策略
- [ ] 新增一致性檢查測試到 `skills/libro-wcag/scripts/tests/test_repo_contracts.py`
- [ ] 更新 `README.md`
- [ ] 更新 `README.en.md`

### 手動驗證 TODO

- [ ] 驗證 clone repo 後 Claude 可直接發現 `.claude/skills/libro-wcag/SKILL.md`
- [ ] 驗證與 `.claude-plugin/` 路徑並存時的優先順序與 namespace 行為

## B. Gemini Workspace Skill

目標：讓使用者 clone repo 後，Gemini workspace 可以直接發現 skill，不必先跑 installer。

### 實體檔案 TODO

- [x] 新增 `.gemini/skills/libro-wcag/SKILL.md`
- [x] 規劃 `.gemini/skills/libro-wcag/SKILL.md` 與 `skills/libro-wcag/SKILL.md` 的同步策略
- [ ] ~~若採 build 產物策略，新增產生腳本~~ — 不採用，改為複製內容 + 一致性測試
- [x] 新增一致性檢查測試到 `skills/libro-wcag/scripts/tests/test_repo_contracts.py`（驗證兩份 SKILL.md 核心 contract 段落一致）
- [x] 視策略更新 `scripts/install-agent.py`，讓 `--agent gemini` 可選擇安裝到 workspace 級 `.gemini/skills/`
- [x] 更新 `README.md`
- [x] 更新 `README.en.md`
- [ ] 視需要新增 `docs/examples/gemini/` 內的 workspace 設定範例

### 設計決策

- [x] 決定採用「複製內容」 ✔ **已決定**
- [ ] ~~決定採用「symlink」~~ — 不採用
- [ ] ~~決定採用「單一來源 + build 產物」~~ — 不採用
- [ ] ~~若採單一來源，定義 Gemini adapter 指令如何合併進 workspace `SKILL.md`~~ — N/A
- [x] 確認 `.gemini/skills/` 應直接 commit（複製內容策略，手寫維護，需 commit）

## D-1. Claude Plugin

目標：若 Claude plugin / marketplace 流程可行，讓 repo 本身能作為 plugin 來源。

### 實體檔案 TODO

- [x] 新增 `.claude-plugin/plugin.json`
- [x] 新增 `.claude-plugin/marketplace.json`
- [x] 檢查 `skills/libro-wcag/SKILL.md` frontmatter 是否符合 plugin skill 規範
- [x] 新增版本一致性測試到 `skills/libro-wcag/scripts/tests/test_repo_contracts.py`
- [x] 更新 `README.md`
- [x] 更新 `README.en.md`
- [x] 視需要更新 `skills/libro-wcag/adapters/claude/usage-example.md`
- [ ] 視需要更新 `skills/libro-wcag/adapters/claude/prompt-template.md`

### 手動驗證 TODO

- [ ] 驗證 `/plugin marketplace add BookHsu/Libro.AgentWCAG.clean`
- [ ] 驗證 `/plugin install libro-wcag@libro-wcag-marketplace`
- [ ] 驗證 plugin 版本與 `pyproject.toml` 同步策略
- [ ] 確認 `plugin.json` 的 `"skills": "./skills/"` 路徑能正確對應到 `skills/libro-wcag/`
- [ ] 測試安裝後 skill 的 namespace 行為（是 `/libro-wcag:libro-wcag` 還是 `/libro-wcag`）

## D-3. Gemini Extension

現況：Gemini CLI 的擴充機制較適合走 MCP，不建議先做獨立 extension installer。

### 實體檔案 TODO

- [x] 在 `docs/automations/agent-installation-expansion-todo.md` 保留決策紀錄
- [x] 若正式採 MCP，新增 `docs/examples/gemini/settings.mcp.sample.json`
- [x] 更新 `README.md`
- [x] 更新 `README.en.md`

## D-4. VS Code Extension Marketplace

目標：讓 Copilot / VS Code 使用者能以 extension 或 chat participant 使用 `libro-wcag`。

### 實體檔案 TODO

- [ ] 新增 `vscode-extension/package.json`
- [ ] 新增 `vscode-extension/tsconfig.json`
- [ ] 新增 `vscode-extension/.vscodeignore`
- [ ] 新增 `vscode-extension/src/extension.ts`
- [ ] 規劃是否需要 `vscode-extension/README.md`
- [ ] 若採 monorepo 方案，更新根目錄 `pyproject.toml` 或補 Node workspace 設定
- [x] 更新 `README.md`
- [x] 更新 `README.en.md`
- [x] 視需要新增 `docs/examples/copilot/` 相關設定檔

### 設計決策

- [ ] ~~決定 extension 留在 monorepo 子目錄還是拆獨立 repo~~ — 暫緩，先走 MCP 路線
- [ ] ~~決定 extension 直接呼叫 Python scripts，還是包裝 MCP server~~ — 暫緩
- [x] 評估是否可跳過 extension 開發 ✔ **已決定：先跳過，D-5 MCP 完成後直接提供 `.vscode/mcp.json`**

## D-5. MCP Server

目標：以單一 MCP server 同時支援 Claude Code、Copilot、Gemini CLI。

### 實體檔案 TODO

- [x] 新增 `mcp-server/server.py`
- [x] 新增 `mcp-server/requirements.txt`
- [x] 新增 `mcp-server/tools/audit_page.py`
- [x] 新增 `mcp-server/tools/suggest_fixes.py`
- [x] 新增 `mcp-server/tools/normalize_report.py`
- [x] 新增 `.mcp.json` sample，例如 `docs/examples/claude/mcp.sample.json`
- [x] 新增 `.vscode/mcp.json` sample，例如 `docs/examples/copilot/mcp.sample.json`
- [x] 新增 `.gemini/settings.json` sample，例如 `docs/examples/gemini/settings.mcp.sample.json`
- [x] 若 Claude plugin 可行，更新 `.claude-plugin/plugin.json` 的 `mcpServers` 欄位
- [x] 視需要更新 `scripts/install-agent.py`，加入 MCP 設定注入選項
- [x] 新增 MCP contract tests 到 `skills/libro-wcag/scripts/tests/`
- [x] 更新 `README.md`
- [x] 更新 `README.en.md`

### 設計決策 (MCP)

- [x] 決定 transport protocol ✔ **已決定：先做 stdio（本機），Streamable HTTP 日後再議**
- [ ] 決定是否發布到 PyPI / npm — **暫緩，先不上架，透過 repo 內安裝**
- [ ] 新增 `mcp-server/pyproject.toml` 或整合到根 `pyproject.toml`（entry point 定義）

### 工具對應 TODO

- [x] `libro_wcag_audit` 對應 `skills/libro-wcag/scripts/run_accessibility_audit.py`
- [x] `libro_wcag_suggest` 對應 `skills/libro-wcag/scripts/wcag_workflow.py`
- [x] `libro_wcag_normalize` 對應 `skills/libro-wcag/scripts/normalize_report.py`

## F-1. Git Submodule + add-dir

目標：讓團隊在目標專案中以 submodule/vendor 方式嵌入 `libro-wcag`。

### 實體檔案 TODO

- [x] 更新 `README.md`
- [x] 更新 `README.en.md`
- [x] 視需要新增 `docs/examples/claude/settings.add-dir.sample.json`
- [ ] 視需要新增 `scripts/setup-submodule.sh`
- [ ] 視需要新增 `scripts/setup-submodule.ps1`

### 手動驗證 TODO

- [ ] 驗證 `claude --add-dir .vendor/libro-wcag`
- [ ] 驗證 repo 內 `skills/libro-wcag/SKILL.md` 可被正確發現
- [ ] 驗證 `.claude/settings.json` 的 `addDirs` 持久化設定是否可取代 `--add-dir` CLI flag

## F-2. GitHub Actions Reusable Workflow

目標：讓其他 repo 可透過 `workflow_call` 直接安裝 `libro-wcag`。

### 實體檔案 TODO

- [x] 新增 `.github/workflows/install-skill.yml`
- [x] 為 reusable workflow 補 contract tests 到 `skills/libro-wcag/scripts/tests/`
- [x] 更新 `README.md`
- [x] 更新 `README.en.md`
- [x] 視需要新增 `docs/examples/ci/install-skill-consumer-sample.yml`

### 發佈 TODO

- [ ] 規劃對外引用的穩定 tag，例如 `v1`
- [ ] 驗證外部 test repo 可成功 `uses: BookHsu/Libro.AgentWCAG.clean/.github/workflows/install-skill.yml@v1`
- [ ] 確認 reusable workflow 對 private fork 的存取限制（同 org 內的 private repo 才能呼叫）
- [x] workflow inputs 加上 `force` (boolean, default false)

## F-3. GitHub Release + gh CLI Download

目標：補充以 `gh release download` 為入口的文件與腳本樣板。

### 實體檔案 TODO

- [x] 更新 `README.md`
- [x] 更新 `README.en.md`
- [ ] 視需要更新 `docs/release/adoption-smoke-guide.md`
- [x] 視需要新增 `docs/examples/ci/gh-release-download-sample.md`

## 建議優先順序

### Phase 1

- [x] B. `.gemini/skills/libro-wcag/SKILL.md`
- [x] D-1. `.claude-plugin/plugin.json`
- [x] D-1. `.claude-plugin/marketplace.json`
- [x] F-1. Submodule + add-dir 文件
- [x] F-2. `.github/workflows/install-skill.yml`
- [x] F-3. `gh release download` 文件

### Phase 2

- [x] D-5. `mcp-server/`

### Phase 3

- [x] D-3. Gemini MCP 接入範例
- [x] D-4. 提供 `.vscode/mcp.json` sample（依賴 D-5 完成，不開發 VS Code Extension）

## 文件同步原則

- [ ] 若新增 `scripts/libro.py`，需同步檢查 `README.md`、`README.en.md` 與各 agent adapter 文件
- [ ] 若新增 `.claude/skills/libro-wcag/SKILL.md`，需同步檢查 `skills/libro-wcag/SKILL.md`
- [ ] 若新增 `.gemini/skills/libro-wcag/SKILL.md`，需同步檢查 `skills/libro-wcag/SKILL.md`
- [ ] 若新增 `.claude-plugin/plugin.json`，需同步檢查 `pyproject.toml` 版本
- [ ] 若新增 reusable workflow，需同步更新 `README.md` 與 `README.en.md`
- [ ] 若新增 MCP samples，需同步更新各 agent adapter 文件
