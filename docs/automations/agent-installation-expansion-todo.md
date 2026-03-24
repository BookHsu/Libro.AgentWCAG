# Agent Installation Expansion TODO

此文件整理後續安裝能力擴充的實體檔案待辦，範圍聚焦在 Gemini workspace skill、Claude plugin、MCP server、CI reusable workflow 與相關文件樣板。

## 原則

- `Libro.AgentWCAG` repo/product 名稱維持不變。
- canonical skill id 維持 `libro-wcag`。
- 新機制優先避免複製多份核心 contract；若必須複製，需補一致性檢查。
- Claude plugin / marketplace 與 Gemini extension 機制是否可正式採用，仍需先做手動驗證。

## B. Gemini Workspace Skill

目標：讓使用者 clone repo 後，Gemini workspace 可以直接發現 skill，不必先跑 installer。

### 實體檔案 TODO

- [ ] 新增 `.gemini/skills/libro-wcag/SKILL.md`
- [ ] 規劃 `.gemini/skills/libro-wcag/SKILL.md` 與 `skills/libro-wcag/SKILL.md` 的同步策略
- [ ] ~~若採 build 產物策略，新增產生腳本~~ — 不採用，改為複製內容 + 一致性測試
- [ ] 新增一致性檢查測試到 `skills/libro-wcag/scripts/tests/test_repo_contracts.py`（驗證兩份 SKILL.md 核心 contract 段落一致）
- [ ] 視策略更新 `scripts/install-agent.py`，讓 `--agent gemini` 可選擇安裝到 workspace 級 `.gemini/skills/`
- [ ] 更新 `README.md`
- [ ] 更新 `README.en.md`
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

- [ ] 新增 `.claude-plugin/plugin.json`
- [ ] 新增 `.claude-plugin/marketplace.json`
- [ ] 檢查 `skills/libro-wcag/SKILL.md` frontmatter 是否符合 plugin skill 規範
- [ ] 新增版本一致性測試到 `skills/libro-wcag/scripts/tests/test_repo_contracts.py`
- [ ] 更新 `README.md`
- [ ] 更新 `README.en.md`
- [ ] 視需要更新 `skills/libro-wcag/adapters/claude/usage-example.md`
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

- [ ] 在 `docs/automations/agent-installation-expansion-todo.md` 保留決策紀錄
- [ ] 若正式採 MCP，新增 `docs/examples/gemini/settings.mcp.sample.json`
- [ ] 更新 `README.md`
- [ ] 更新 `README.en.md`

## D-4. VS Code Extension Marketplace

目標：讓 Copilot / VS Code 使用者能以 extension 或 chat participant 使用 `libro-wcag`。

### 實體檔案 TODO

- [ ] 新增 `vscode-extension/package.json`
- [ ] 新增 `vscode-extension/tsconfig.json`
- [ ] 新增 `vscode-extension/.vscodeignore`
- [ ] 新增 `vscode-extension/src/extension.ts`
- [ ] 規劃是否需要 `vscode-extension/README.md`
- [ ] 若採 monorepo 方案，更新根目錄 `pyproject.toml` 或補 Node workspace 設定
- [ ] 更新 `README.md`
- [ ] 更新 `README.en.md`
- [ ] 視需要新增 `docs/examples/copilot/` 相關設定檔

### 設計決策

- [ ] ~~決定 extension 留在 monorepo 子目錄還是拆獨立 repo~~ — 暫緩，先走 MCP 路線
- [ ] ~~決定 extension 直接呼叫 Python scripts，還是包裝 MCP server~~ — 暫緩
- [x] 評估是否可跳過 extension 開發 ✔ **已決定：先跳過，D-5 MCP 完成後直接提供 `.vscode/mcp.json`**

## D-5. MCP Server

目標：以單一 MCP server 同時支援 Claude Code、Copilot、Gemini CLI。

### 實體檔案 TODO

- [ ] 新增 `mcp-server/server.py`
- [ ] 新增 `mcp-server/requirements.txt`
- [ ] 新增 `mcp-server/tools/audit_page.py`
- [ ] 新增 `mcp-server/tools/suggest_fixes.py`
- [ ] 新增 `mcp-server/tools/normalize_report.py`
- [ ] 新增 `.mcp.json` sample，例如 `docs/examples/claude/mcp.sample.json`
- [ ] 新增 `.vscode/mcp.json` sample，例如 `docs/examples/copilot/mcp.sample.json`
- [ ] 新增 `.gemini/settings.json` sample，例如 `docs/examples/gemini/settings.mcp.sample.json`
- [ ] 若 Claude plugin 可行，更新 `.claude-plugin/plugin.json` 的 `mcpServers` 欄位
- [ ] 視需要更新 `scripts/install-agent.py`，加入 MCP 設定注入選項
- [ ] 新增 MCP contract tests 到 `skills/libro-wcag/scripts/tests/`
- [ ] 更新 `README.md`
- [ ] 更新 `README.en.md`

### 設計決策 (MCP)

- [x] 決定 transport protocol ✔ **已決定：先做 stdio（本機），Streamable HTTP 日後再議**
- [ ] 決定是否發布到 PyPI / npm — **暫緩，先不上架，透過 repo 內安裝**
- [ ] 新增 `mcp-server/pyproject.toml` 或整合到根 `pyproject.toml`（entry point 定義）

### 工具對應 TODO

- [ ] `libro_wcag_audit` 對應 `skills/libro-wcag/scripts/run_accessibility_audit.py`
- [ ] `libro_wcag_suggest` 對應 `skills/libro-wcag/scripts/wcag_workflow.py`
- [ ] `libro_wcag_normalize` 對應 `skills/libro-wcag/scripts/normalize_report.py`

## F-1. Git Submodule + add-dir

目標：讓團隊在目標專案中以 submodule/vendor 方式嵌入 `libro-wcag`。

### 實體檔案 TODO

- [ ] 更新 `README.md`
- [ ] 更新 `README.en.md`
- [ ] 視需要新增 `docs/examples/claude/settings.add-dir.sample.json`
- [ ] 視需要新增 `scripts/setup-submodule.sh`
- [ ] 視需要新增 `scripts/setup-submodule.ps1`

### 手動驗證 TODO

- [ ] 驗證 `claude --add-dir .vendor/libro-wcag`
- [ ] 驗證 repo 內 `skills/libro-wcag/SKILL.md` 可被正確發現
- [ ] 驗證 `.claude/settings.json` 的 `addDirs` 持久化設定是否可取代 `--add-dir` CLI flag

## F-2. GitHub Actions Reusable Workflow

目標：讓其他 repo 可透過 `workflow_call` 直接安裝 `libro-wcag`。

### 實體檔案 TODO

- [ ] 新增 `.github/workflows/install-skill.yml`
- [ ] 為 reusable workflow 補 contract tests 到 `skills/libro-wcag/scripts/tests/`
- [ ] 更新 `README.md`
- [ ] 更新 `README.en.md`
- [ ] 視需要新增 `docs/examples/ci/install-skill-consumer-sample.yml`

### 發佈 TODO

- [ ] 規劃對外引用的穩定 tag，例如 `v1`
- [ ] 驗證外部 test repo 可成功 `uses: BookHsu/Libro.AgentWCAG.clean/.github/workflows/install-skill.yml@v1`
- [ ] 確認 reusable workflow 對 private fork 的存取限制（同 org 內的 private repo 才能呼叫）
- [ ] workflow inputs 加上 `force` (boolean, default false)

## F-3. GitHub Release + gh CLI Download

目標：補充以 `gh release download` 為入口的文件與腳本樣板。

### 實體檔案 TODO

- [ ] 更新 `README.md`
- [ ] 更新 `README.en.md`
- [ ] 視需要更新 `docs/release/adoption-smoke-guide.md`
- [ ] 視需要新增 `docs/examples/ci/gh-release-download-sample.md`

## 建議優先順序

### Phase 1

- [ ] B. `.gemini/skills/libro-wcag/SKILL.md`
- [ ] D-1. `.claude-plugin/plugin.json`
- [ ] D-1. `.claude-plugin/marketplace.json`
- [ ] F-1. Submodule + add-dir 文件
- [ ] F-2. `.github/workflows/install-skill.yml`
- [ ] F-3. `gh release download` 文件

### Phase 2

- [ ] D-5. `mcp-server/`

### Phase 3

- [ ] D-3. Gemini MCP 接入範例
- [ ] D-4. 提供 `.vscode/mcp.json` sample（依賴 D-5 完成，不開發 VS Code Extension）

## 文件同步原則

- [ ] 若新增 `.gemini/skills/libro-wcag/SKILL.md`，需同步檢查 `skills/libro-wcag/SKILL.md`
- [ ] 若新增 `.claude-plugin/plugin.json`，需同步檢查 `pyproject.toml` 版本
- [ ] 若新增 reusable workflow，需同步更新 `README.md` 與 `README.en.md`
- [ ] 若新增 MCP samples，需同步更新各 agent adapter 文件
