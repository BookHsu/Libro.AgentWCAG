# Libro.AgentWCAG

中文說明為預設版本。English version: [README.en.md](/c:/Source/Libro.AgentWCAG.clean/README.en.md)

Libro.AgentWCAG 是一個可安裝、可發佈的跨代理 WCAG 網頁無障礙 skill repository，支援以一致的 vendor-neutral contract 讓不同 AI agent 執行稽核、建議修正與部分自動修正。

## 專案重點

- 支援代理：Codex、Claude、Gemini、Copilot
- 安裝方式：repo 直接安裝，或從 release 資產快速安裝
- 發佈方式：可產生版本化 zip、checksum、release manifest
- 核心能力：`audit-only`、`suggest-only`、`apply-fixes`

## Repo 結構

- `skills/libro-agent-wcag`: 可安裝 skill 主體
- `skills/libro-agent-wcag/adapters/openai-codex`: Codex adapter
- `skills/libro-agent-wcag/adapters/claude`: Claude adapter
- `skills/libro-agent-wcag/adapters/gemini`: Gemini adapter
- `skills/libro-agent-wcag/adapters/copilot`: Copilot adapter
- `scripts/install-agent.py`: 直接安裝指定 agent bundle
- `scripts/doctor-agent.py`: 安裝後健康檢查與完整性驗證
- `scripts/uninstall-agent.py`: 卸載工具

## 安裝

### 從目前 repo 直接安裝

```powershell
python .\scripts\install-agent.py --agent codex
python .\scripts\install-agent.py --agent claude
python .\scripts\install-agent.py --agent gemini
python .\scripts\install-agent.py --agent copilot
python .\scripts\install-agent.py --agent all
```

### 從本地 release 資產安裝

```powershell
pwsh -File .\scripts\install-latest.ps1 -ReleaseBase .\dist\release -Agent codex
```

```sh
sh ./scripts/install-latest.sh --release-base ./dist/release --agent codex
```

### 從 GitHub 已發佈版本快速安裝

```powershell
pwsh -File .\scripts\install-latest.ps1 -ReleaseBase https://github.com/<owner>/<repo>/releases/download/vX.Y.Z -Agent codex
```

- 把 `vX.Y.Z` 換成實際 tag，例如 `v1.0.1`
- 安裝流程會自動驗證 `latest-release.json` / release manifest / `sha256`
- 安裝完成後會自動執行 `doctor-agent.py --verify-manifest-integrity`

### 預設安裝位置

- `codex`: `~/.codex/skills/libro-agent-wcag`
- `claude`: `~/.claude/skills/libro-agent-wcag`
- `gemini`: `~/.gemini/skills/libro-agent-wcag`
- `copilot`: `~/.copilot/skills/libro-agent-wcag`

## 驗證安裝

```powershell
python .\scripts\doctor-agent.py --agent codex
python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity
python .\scripts\doctor-agent.py --agent all
```

## 卸載

```powershell
python .\scripts\uninstall-agent.py --agent codex
python .\scripts\uninstall-agent.py --agent all
```

## 使用方式

共用 contract 位於：

- `skills/libro-agent-wcag/SKILL.md`
- `skills/libro-agent-wcag/references/core-spec.md`
- `skills/libro-agent-wcag/references/adapter-mapping.md`

支援的任務模式：

- `audit-only`: 只找問題
- `suggest-only`: 找問題並提出修正建議
- `apply-fixes`: 在明確要求修改時，對支援的本地檔案做安全範圍內修正

支援的任務意圖：

- `create`: 對草稿、模板、未上線頁面做檢查
- `modify`: 對既有頁面先稽核再修正

初次在 Codex 使用時可直接呼叫 `$libro-agent-wcag`。

## 本地驗證

```powershell
python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-agent-wcag --validate-policy-bundles
```

- 測試策略與覆蓋矩陣見 `TESTING-PLAN.md`

## 發佈

### 產出 release 資產

```powershell
python .\scripts\package-release.py --output-dir .\dist\release --overwrite
```

會產出：

- `libro-agent-wcag-<version>-codex.zip`
- `libro-agent-wcag-<version>-claude.zip`
- `libro-agent-wcag-<version>-gemini.zip`
- `libro-agent-wcag-<version>-copilot.zip`
- `libro-agent-wcag-<version>-all-in-one.zip`
- `libro-agent-wcag-<version>-sha256sums.txt`
- `libro-agent-wcag-<version>-release-manifest.json`
- `latest-release.json`

### GitHub Release 自動化

- `.github/workflows/release.yml` 現在支援三種入口：
  - push `v*` tag
  - 手動執行 `workflow_dispatch`
  - 在 GitHub UI 將 Release 設為 `published`
- 這代表如果先在 GitHub 手動發佈 release，也會自動補上 zip 與其他 release assets

## Release-consumer shortest path

1. Download the published release assets for `vX.Y.Z`.
2. Verify `libro-agent-wcag-X.Y.Z-sha256sums.txt`.
3. Run `install-latest.ps1` or `install-latest.sh` against the release asset directory or URL.

## Release-consumer quickstart

1. Install from release assets.
2. `install-latest.ps1` / `install-latest.sh` automatically runs `doctor-agent.py --verify-manifest-integrity` after install succeeds.
3. Run a first audit with `python .\skills\libro-agent-wcag\scripts\run_accessibility_audit.py --target <file-or-url> --output-dir out`.
4. Remove the skill with `python .\scripts\uninstall-agent.py --agent codex`.

## Release readiness

- `scripts/install-agent.py`, `scripts/doctor-agent.py`, and report artifacts derive `product_version` from `pyproject.toml`.
- `source_revision` resolves from `LIBRO_AGENTWCAG_SOURCE_REVISION` when provided, otherwise from local git `HEAD`.
- Package release assets with `python .\scripts\package-release.py --output-dir .\dist\release --overwrite`.
- Packaging emits `libro-agent-wcag-<version>-all-in-one.zip` and `libro-agent-wcag-<version>-sha256sums.txt` alongside the agent bundles.
- Clean release-consumer validation is available via `python .\scripts\run-release-adoption-smoke.py --release-dir .\dist\release --agent codex`.
- Key release references:
  - `docs/release/release-playbook.md`
  - `docs/release/ga-release-workflow.md`
  - `docs/release/ga-definition.md`
  - `docs/release/rollback-playbook.md`
  - `docs/release/adoption-smoke-guide.md`
  - `docs/release/apply-fixes-scope.md`
  - `docs/release/prompt-invocation-templates.md`
  - `docs/release/resilient-run-patterns.md`
  - `docs/examples/ci/github-actions-wcag-ci-sample.yml`
  - `docs/release/real-scanner-ci-lane.md`
  - `docs/release/baseline-governance.md`
  - `docs/release/advanced-ci-gates.md`
  - `docs/policy-bundles/`

## PR 規則與 owner bypass

- `owner can bypass` 不是 repo 檔案本身能強制控制的功能，必須在 GitHub repository settings 設定
- 建議用 branch ruleset / branch protection 設定：
  - required pull request
  - required status checks
  - 必要檢查包含 `libro-agent-wcag-real-scanner`
  - bypass list 加入 repo owner / admin 或 maintainer team
- 詳細操作說明見 [docs/release/repo-admin-setup.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/repo-admin-setup.md)

## 重要文件

- 中文首頁：`README.md`
- 英文版本：[README.en.md](/c:/Source/Libro.AgentWCAG.clean/README.en.md)
- Release 流程：[docs/release/ga-release-workflow.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/ga-release-workflow.md)
- Release 管理設定：[docs/release/repo-admin-setup.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/repo-admin-setup.md)
- Release 操作手冊：[docs/release/release-playbook.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/release-playbook.md)
- 安裝與 smoke：[docs/release/adoption-smoke-guide.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/adoption-smoke-guide.md)
- 支援環境：[docs/release/supported-environments.md](/c:/Source/Libro.AgentWCAG.clean/docs/release/supported-environments.md)

## 備註

- 深入的技術文件目前多數仍以英文撰寫，中文首頁先負責安裝、發佈與管理入口整理。
- 如果要把整套 release / testing / governance 文件全部改成雙語，下一步應該是先決定是 `README + docs/zh-TW/`，還是每份文件中英分檔。

## Codex Automation

- Use `docs/automations/test-plan-automation.md` as the execution spec for scheduled Codex test-development automation. This lane focuses only on test development, testing-plan updates, commits, and pushes.
- Use `docs/automations/test-plan-review-policy.md` as the review policy before accepting automation-generated changes.
