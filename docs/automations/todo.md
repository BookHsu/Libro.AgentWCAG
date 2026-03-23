# 自動化路線圖 TODO

此文件用來追蹤目前已討論完成的 `Libro.AgentWCAG` 下一步方向。

## 已確認優先順序

### 1. 重構 `run_accessibility_audit.py`

狀態：下一個主要工程優先項目。

目標：

- 降低核心 CLI 工作流程的維護風險
- 將 scanner runtime、policy、baseline governance、gate logic、artifact writing 分離
- 在不改變現有行為的前提下，提升可讀性與可測試性

細項 TODO：

#### 1.0 前置盤點與重構設計

- [x] 盤點 `skills/libro-agent-wcag/scripts/run_accessibility_audit.py` 目前所有責任區塊
- [x] 列出目前所有常數、CLI flags、exit codes、schema version 常數與其歸屬
- [x] 列出目前所有內部 helper 與它們之間的呼叫依賴
- [x] 標記哪些函式是純邏輯、哪些是 I/O、哪些是 orchestration
- [x] 列出目前所有會寫檔的函式
- [x] 列出目前所有會直接呼叫 subprocess 的函式
- [x] 列出目前所有會影響 CLI 契約的輸出欄位
- [x] 列出目前所有會影響 `run_meta` 的組裝函式
- [x] 建立拆分前後的函式對應表
- [x] 定義拆分後的模組邊界與檔名
- [x] 定義拆分後的 import 方向，避免循環依賴
- [x] 定義「不可變更」清單：CLI flags、exit codes、artifact 檔名、report schema、summary-only 輸出

#### 1.1 新增模組骨架

- [x] 新增 `skills/libro-agent-wcag/scripts/scanner_runtime.py`
- [x] 新增 `skills/libro-agent-wcag/scripts/policy_controls.py`
- [x] 新增 `skills/libro-agent-wcag/scripts/baseline_governance.py`
- [x] 新增 `skills/libro-agent-wcag/scripts/advanced_gates.py`
- [x] 新增 `skills/libro-agent-wcag/scripts/report_artifacts.py`
- [x] 視需要新增 `skills/libro-agent-wcag/scripts/shared_constants.py`
- [x] 確認新增檔案命名與責任清楚，不和 `wcag_workflow.py`、`auto_fix.py` 重疊

#### 1.2 Scanner Runtime 拆分

- [x] 將 `npx` resolution 相關常數與 helper 搬到 `scanner_runtime.py`
- [x] 搬移 `_resolve_npx_executable()`
- [x] 搬移 `NPX_EXECUTABLE`
- [x] 搬移 `PREFLIGHT_TOOL_CHECKS`
- [x] 搬移 `_extract_version_line()`
- [x] 搬移 `_build_version_provenance()`
- [x] 搬移 `_run_command()`
- [x] 搬移 `_is_transient_scanner_error()`
- [x] 搬移 `_run_scanner_with_retry()`
- [x] 搬移 scanner preflight 相關 helper
- [x] 搬移 axe scanner 執行 helper
- [x] 搬移 lighthouse scanner 執行 helper
- [x] 搬移 scanner capability negotiation 相關 helper
- [x] 檢查 scanner runtime 模組對外 export 清單
- [x] 更新主檔 import
- [x] 移除主檔中已搬移的 scanner runtime helper
- [x] 執行 `test_runner.py` 中 scanner runtime 相關測試
- [x] 執行 `test_real_scanner_ci_lane.py`
- [x] 驗證 Windows `npx.cmd` fallback 行為不變
- [x] 驗證 scanner timeout / missing-tool / runtime-error 分類行為不變

#### 1.3 Policy Controls 拆分

- [x] 將 policy preset/bundle 相關常數搬到 `policy_controls.py`
- [x] 搬移 `POLICY_PRESETS`
- [x] 搬移 `POLICY_BUNDLES`
- [x] 搬移 `ALLOWED_POLICY_CONFIG_KEYS`
- [x] 搬移 `POLICY_CONFIG_KEY_SPECS`
- [x] 搬移 policy preset resolve 相關 helper
- [x] 搬移 policy bundle resolve 相關 helper
- [x] 搬移 policy-config 載入與 key 驗證 helper
- [x] 搬移 include/ignore overlap 檢查 helper
- [x] 搬移 effective policy 組裝 helper
- [x] 搬移 preset discovery payload helper
- [x] 搬移 policy-config key discovery payload helper
- [x] 搬移 explain-policy 相關 helper
- [x] 搬移 write-effective-policy artifact 相關 helper
- [x] 更新主檔 import
- [x] 移除主檔中已搬移的 policy helper
- [x] 執行 `test_runner.py` 中 policy 相關測試
- [x] 執行 `test_cli_flows.py` 中 `--policy-config`、`--policy-bundle`、`--explain-policy`、`--strict-rule-overlap` 相關測試
- [x] 驗證 effective policy 結構不變
- [x] 驗證 policy 相關 CLI 錯誤訊息與行為不變

#### 1.4 Baseline Governance 拆分

- [x] 將 baseline / waiver / trend / evidence 相關常數搬到 `baseline_governance.py`
- [x] 搬移 baseline normalization mode 常數
- [x] 搬移 selector canonicalization mode 常數
- [x] 搬移 baseline evidence mode 常數
- [x] 搬移 waiver expiry mode 常數
- [x] 搬移 debt state 常數
- [x] 搬移 debt trend 相關常數
- [x] 搬移 debt waiver required fields 常數
- [x] 搬移 baseline report 載入 helper
- [x] 搬移 baseline signature 建構與 normalization helper
- [x] 搬移 baseline diff 計算 helper
- [x] 搬移 debt state transition 標記 helper
- [x] 搬移 debt waiver schema 驗證 helper
- [x] 搬移 waiver expiry review helper
- [x] 搬移 waiver gate decision helper
- [x] 搬移 debt trend payload 組裝 helper
- [x] 搬移 baseline evidence hash 計算 helper
- [x] 搬移 hash-chain 組裝 helper
- [x] 搬移 baseline evidence verification helper
- [x] 更新主檔 import
- [x] 移除主檔中已搬移的 baseline governance helper
- [x] 執行 `test_runner.py` 中 baseline / waiver / debt trend / evidence 相關測試
- [x] 執行 `test_cli_flows.py` 中 baseline hash/hash-chain、waiver expiry、debt trend 相關測試
- [x] 驗證 `run_meta.baseline_diff` 結構不變
- [x] 驗證 finding-level `debt_state` 輸出不變
- [x] 驗證 `debt-trend.json` 與 `run_meta.debt_trend` 結構不變

#### 1.5 Advanced Gates 拆分

- [x] 將 risk calibration / replay / scanner stability 相關常數搬到 `advanced_gates.py`
- [x] 搬移 risk calibration mode/schema/version 常數
- [x] 搬移 risk calibration threshold/min sample/exit code 常數
- [x] 搬移 replay verification schema/version/exit code 常數
- [x] 搬移 scanner stability mode/schema/version/window/exit code 常數
- [x] 搬移 risk calibration evidence 載入 helper
- [x] 搬移 risk calibration 評估 helper
- [x] 搬移 replay source report 載入 helper
- [x] 搬移 replay summary 組裝 helper
- [x] 搬移 replay gate decision helper
- [x] 搬移 scanner stability baseline 載入 helper
- [x] 搬移 scanner stability comparison helper
- [x] 搬移 scanner stability gate decision helper
- [x] 搬移 advanced gate exit code decision helper
- [x] 更新主檔 import
- [x] 移除主檔中已搬移的 advanced gate helper
- [x] 執行 `test_runner.py` 中 risk calibration / replay / scanner stability 測試
- [x] 執行 `test_cli_flows.py` 中對應 fail / warn / downgrade 測試
- [x] 驗證 exit code 46 / 47 / 48 維持不變
- [x] 驗證 `run_meta.risk_calibration` 結構不變
- [x] 驗證 `run_meta.replay_verification` 結構不變
- [x] 驗證 `run_meta.scanner_stability` 結構不變

#### 1.6 Artifact 與 Output 拆分

- [x] 將 artifact / schema / summary 相關常數搬到 `report_artifacts.py`
- [x] 搬移 report schema 常數
- [x] 搬移 report schema source path helper
- [x] 搬移 schema staging helper
- [x] 搬移 artifact path 蒐集 helper
- [x] 搬移 artifact manifest 組裝 helper
- [x] 搬移 checksum / size / timestamp helper
- [x] 搬移 compact summary payload 組裝 helper
- [x] 搬移 summary-only stdout 輸出 helper
- [x] 搬移 report output path 組裝 helper
- [x] 視需要搬移 effective-policy artifact path helper
- [x] 更新主檔 import
- [x] 移除主檔中已搬移的 artifact/output helper
- [x] 執行 `test_runner.py` 中 artifact manifest 測試
- [x] 執行 `test_cli_flows.py` 中 summary-only、artifact-manifest、effective-policy artifact 測試
- [x] 驗證 `artifact-manifest.json` 結構不變
- [x] 驗證 schema 輸出路徑不變
- [x] 驗證 summary-only stdout JSON 結構不變

#### 1.7 CLI 與 Orchestration 收斂

- [x] 保留 `run_accessibility_audit.py` 作為 CLI 入口
- [x] 保留 `parse_args()` 在主檔，或明確定義其最終歸屬
- [x] 清理主檔中不再需要的常數
- [x] 清理主檔中不再需要的重複 helper
- [x] 確保主檔只保留參數解析、流程協調、最終 exit code 決策
- [x] 重新整理 import 順序
- [x] 確認沒有循環依賴
- [x] 確認主檔仍容易追蹤 `main()` 流程
- [x] 檢查主檔長度是否顯著下降
- [x] 檢查 argparse help 文案未意外變更
- [x] 驗證 CLI 執行方式仍為 `python skills/libro-agent-wcag/scripts/run_accessibility_audit.py`

#### 1.8 共用常數與相依整理

- [x] 檢查哪些常數仍適合留在主檔
- [x] 檢查哪些常數應抽到 `shared_constants.py`
- [x] 若新增 `shared_constants.py`，同步更新所有模組 import
- [x] 確保 `wcag_workflow.py`、`auto_fix.py`、新模組之間沒有多餘交錯依賴
- [x] 若發現模組邊界重疊，優先調整責任而不是複製 helper

#### 1.9 測試與回歸驗證

- [x] 每完成一個模組抽離後執行對應測試
- [x] 重點執行 `test_runner.py`
- [x] 重點執行 `test_cli_flows.py`
- [x] 視需要執行 `test_repo_contracts.py`
- [x] 視需要執行 `test_release_docs.py`
- [x] 最後執行完整測試
- [x] 檢查 git diff，確認沒有意外更動 CLI 契約、文件路徑或 sample 資產
- [x] 檢查 `git status` 與變更範圍是否符合預期

#### 1.10 建議執行順序

- [x] 第一步：先抽 `scanner_runtime.py`
- [x] 第二步：再抽 `policy_controls.py`
- [x] 第三步：再抽 `baseline_governance.py`
- [x] 第四步：再抽 `advanced_gates.py`
- [x] 第五步：最後抽 `report_artifacts.py`
- [x] 第六步：回頭收斂主檔 orchestration
- [x] 每一步都先通過對應測試後再進下一步

#### 1.11 每一步的最小交付標準

- [x] 新模組已建立且命名清楚
- [x] 主檔已改用新模組 import
- [x] 對應測試已通過
- [x] `git diff` 僅包含預期重構
- [x] 未改動 CLI 契約、文件路徑、sample 資產

#### 1.12 最終驗收條件

- [x] `run_accessibility_audit.py` 顯著縮小且可讀性提升
- [x] 所有既有 CLI flags 仍可使用
- [x] 所有既有 artifact 檔名與輸出結構維持相容
- [x] 文件中提到的 CLI 行為不需大改
- [x] 既有測試維持通過
- [x] 完成後可以獨立接續第 2 項 GitHub CI 自動 real-scanner lane 工作

### 2. 將 Real-Scanner Lane 提升為自動 GitHub CI

狀態：核心重構穩定後的下一步。

目標：

- 將 real-scanner 驗證從目前的可選或手動流程，提升為可重複執行的 GitHub Actions 自動化流程
- 在 scanner 工具不可用時，仍保留 deterministic fallback 行為
- 提高專案對真實執行環境的長期信心，而不只依賴 mock regression coverage

細項 TODO：

#### 2.0 已確認決策

- [x] 觸發時機採用 `pull_request + workflow_dispatch`
- [x] 此 lane 作為正式 PR gate
- [x] scanner 安裝方式採用固定版本安裝
- [x] 掃描目標先固定為 `docs/testing/realistic-sample/mixed-findings.html`
- [x] live scanner 不可用時直接 fail，照樣阻擋 PR
- [x] required check 命名策略固定為 `libro-agent-wcag-real-scanner`
- [x] runner 固定採用 `ubuntu-latest`
- [x] browser 策略固定為「驗證可用，不額外安裝 Chrome」
- [x] artifact retention 固定為 `14` 天
- [x] 固定保留 `wcag-report.sarif`

#### 2.1 Workflow 事件與 Gate 形態

- [x] 新增 real-scanner workflow 檔案
- [x] 將 workflow `name` 固定為 `libro-agent-wcag-real-scanner`
- [x] 將主要 job `name` 固定為 `libro-agent-wcag-real-scanner`
- [x] workflow 加入 `pull_request` trigger
- [x] workflow 加入 `workflow_dispatch` trigger
- [x] 文件中明確記錄 branch protection required check 名稱為 `libro-agent-wcag-real-scanner`
- [x] 確保 workflow 與 job 名稱不會因 artifact/step 調整而改動
- [x] 在文件中明確定義此 lane 失敗即阻擋 PR merge

#### 2.2 Scanner 工具安裝與版本固定

- [x] 固定 workflow 使用的 Python 版本
- [x] 固定 workflow 使用的 Node.js 版本
- [x] 固定 `@axe-core/cli` 版本字串
- [x] 固定 `lighthouse` 版本字串
- [x] 將 Python 版本設定寫入 workflow 單一位置
- [x] 將 Node.js 版本設定寫入 workflow 單一位置
- [x] 將 scanner 版本設定寫入 workflow 單一位置
- [x] workflow 加入 Python 依賴安裝 step
- [x] workflow 加入固定版本 scanner 安裝 step
- [x] workflow 加入版本輸出 step，記錄 Python/Node/axe/lighthouse 版本
- [x] 版本資訊納入 triage artifact 或 preflight log
- [x] 確保 scanner 升級只需修改單一設定區塊

#### 2.3 Live Scanner 環境要求

- [x] workflow runner 固定為 `ubuntu-latest`
- [x] 新增 browser availability 驗證 step
- [x] browser 驗證 step 只檢查可用性，不額外安裝 Chrome
- [x] 明確驗證 headless Chrome/Chromium 可供 Lighthouse 啟動
- [x] 明確驗證 `npx --no-install @axe-core/cli --version`
- [x] 明確驗證 `npx --no-install lighthouse --version`
- [x] 若 browser 不可用，workflow 直接 fail
- [x] 若 axe 不可用，workflow 直接 fail
- [x] 若 lighthouse 不可用，workflow 直接 fail
- [x] 將「browser/scanner 不可用即 fail」規則寫入文件

#### 2.4 掃描目標與範圍

- [x] 將 live scanner target 固定為 `docs/testing/realistic-sample/mixed-findings.html`
- [x] workflow 內 target 路徑集中在單一 env 或單一 step 變數
- [x] 測試與文件共用同一個 target 路徑字串
- [x] 初期只掃描單一 fixture，不擴展第二個 target
- [x] 文件中註明此 target 旨在覆蓋 mixed findings / manual review / apply-fixes 行為
- [x] 若要新增第二個 target，必須另開 TODO，不在本輪順手加入

#### 2.5 Workflow 內的執行步驟

- [x] 加入 repository checkout step
- [x] 加入 Python setup step
- [x] 加入 Node.js setup step
- [x] 加入 Python dependencies install step
- [x] 加入固定版本 scanner install step
- [x] 加入 browser availability verify step
- [x] 加入 scanner preflight step
- [x] scanner preflight step 執行 `--preflight-only`
- [x] 加入 live audit step
- [x] live audit step 指向固定 mixed-findings target
- [x] live audit step 產出 `wcag-report.json`
- [x] live audit step 產出 `wcag-report.md`
- [x] live audit step 產出 `wcag-report.sarif`
- [x] live audit step 產出 raw scanner outputs
- [x] live audit step 產出 capability negotiation 相關 artifact
- [x] 加入 artifact upload step
- [x] 任一步驟非零退出時 job 直接 fail，不做 fallback

#### 2.6 Artifact 與 Triage 輸出

- [x] upload `axe.raw.json`
- [x] upload `lighthouse.raw.json`
- [x] upload `normalized-summary.live.json`
- [x] upload `capability-negotiation.json`
- [x] upload `wcag-report.json`
- [x] upload `wcag-report.md`
- [x] upload `wcag-report.sarif`
- [x] upload preflight log 或版本輸出 artifact
- [x] artifact retention 固定為 `14` 天
- [x] upload step 使用 `if: always()` 以保留失敗時 triage 資訊
- [x] artifact 名稱在 workflow 與文件中保持一致
- [x] 文件列出每個 artifact 的用途

#### 2.7 Fail-Fast 與阻擋條件

- [x] 定義 Python/Node/scanner install 失敗即 fail
- [x] 定義 browser verification 失敗即 fail
- [x] 定義 scanner preflight 失敗即 fail
- [x] 定義 axe 執行失敗即 fail
- [x] 定義 lighthouse 執行失敗即 fail
- [x] 定義 report artifact 缺失即 fail
- [x] 定義 artifact upload step 自身失敗即 fail
- [x] 明確禁止 mock/fallback 取代 live scanner gate
- [x] 文件化 fail-fast matrix 與對應 triage artifact

#### 2.8 與現有 Deterministic Lane 的關係

- [x] 保留既有 deterministic lane workflow 不刪除
- [x] 文件明確區分 deterministic lane 與 live lane 用途
- [x] 確保 deterministic lane 不是 required check
- [x] 確保 `libro-agent-wcag-real-scanner` 是 required check
- [x] 確保兩條 lane 的 artifact 名稱不衝突
- [x] 確保 reviewer 能從名稱分辨 mock lane 與 live lane
- [x] 補測試或文件以防止之後把兩條 lane 混成同一條

#### 2.9 文件與 Repo 契約同步

- [x] 更新 `docs/release/real-scanner-ci-lane.md`
- [x] 在文件中寫明 workflow / job / required check 名稱
- [x] 在文件中寫明 runner 為 `ubuntu-latest`
- [x] 在文件中寫明 browser 策略為「驗證可用，不額外安裝」
- [x] 在文件中寫明 target 固定為 mixed-findings fixture
- [x] 在文件中寫明 artifact retention 為 `14` 天
- [x] 在文件中寫明固定保留 `wcag-report.sarif`
- [x] 更新 `docs/release/resilient-run-patterns.md`
- [x] 視需要更新 `docs/release/release-playbook.md`
- [x] 視需要更新 `README.md`
- [x] 確保文件反映「PR gate、live-only、scanner 不可用即 fail」最終決策

#### 2.10 測試與驗證

- [x] 更新 `test_real_scanner_ci_lane.py`
- [x] 新增/更新 workflow 名稱與 job 名稱 contract 測試
- [x] 新增/更新 required check 名稱 contract 測試
- [x] 新增/更新 artifact retention contract 測試
- [x] 新增/更新 `wcag-report.sarif` artifact contract 測試
- [x] 視需要更新 `test_release_docs.py`
- [x] 視需要更新 workflow contract 測試
- [x] 驗證 workflow 路徑與 repo 內實際檔案一致
- [x] 驗證 artifact 名稱與文件一致
- [x] 驗證 required check 名稱與 workflow 定義一致

#### 2.11 建議實作順序

- [x] 第一步：先落 workflow 名稱 / job 名稱 / trigger / required check
- [x] 第二步：固定 Python / Node / axe / lighthouse 版本
- [x] 第三步：加入 browser verify + preflight + live audit step
- [x] 第四步：補齊 artifact upload 與 retention
- [x] 第五步：同步文件與 contract tests
- [x] 第六步：在 PR 上驗證 required check 與 fail-fast 行為

#### 2.12 最小交付標準

- [x] PR 開啟時會自動觸發 `libro-agent-wcag-real-scanner`
- [x] `workflow_dispatch` 可手動重跑 `libro-agent-wcag-real-scanner`
- [x] lane 失敗時會阻擋 PR
- [x] browser / scanner 不可用時不降級為 mock，直接 fail
- [x] mixed-findings target 可穩定執行
- [x] `wcag-report.sarif` 與其他 triage artifact 皆可保留
- [x] retention 設定為 `14` 天
- [x] 文件與測試已同步更新

#### 2.13 最終驗收條件

- [x] `libro-agent-wcag-real-scanner` 已成為正式 required PR check
- [x] 固定版本的 scanner toolchain 可重現
- [x] scanner / browser / preflight 失敗時有足夠 artifact 可排查
- [x] 現有 deterministic lane 仍可正常運作
- [x] repo 文件已完整反映此 CI gate 決策

## 暫緩，作為下一步討論方向

以下項目目前刻意暫緩，待前兩個主方向完成後，再作為下一輪討論 backlog。

### 3. M39 Release Artifact And GA Packaging

狀態：下一輪完整產品化主項目。

目標：

- 將 `Libro.AgentWCAG` 從 repo-native 工程資產提升為可發版、可驗證、可回滾的正式產品交付物
- 建立 GitHub Release artifact、版本 provenance、clean environment adoption smoke、以及 rollback runbook
- 收斂 installer、doctor、audit report、release docs 與 CI workflow 的產品化契約

細項 TODO：

#### 3.0 已確認範圍與完成定義

- [ ] 定義 M39 的正式完成條件
- [ ] 明確列出 GA 必備交付物清單
- [ ] 明確列出 GA 非目標與後續項目，避免 scope 膨脹
- [ ] 定義「可發版」與「GA」之間的差異
- [ ] 定義何時允許建立 release tag
- [ ] 定義何時只允許 draft release，不允許 publish
- [ ] 定義 blocker / non-blocker 缺陷分級
- [ ] 明確列出哪些檔案、腳本、文件屬於 M39 改動範圍
- [ ] 明確列出哪些既有契約不得破壞
- [ ] 建立 M39 對應 issue / milestone / owner 映射

#### 3.1 單一版本來源與 provenance 收斂

- [ ] 決定版本單一來源固定為 `pyproject.toml`
- [ ] 盤點 repo 內所有目前會顯示或應顯示版本資訊的輸出點
- [ ] 新增共用版本讀取 helper，避免各腳本重複解析版本
- [ ] 定義版本字串格式與 tag 格式關係
- [ ] 定義 dev version、release version、hotfix version 的表達方式
- [ ] 定義 source revision / commit SHA 的輸出策略
- [ ] 定義 build timestamp / packaged timestamp 的輸出策略
- [ ] 定義缺版本資訊時 CLI 的 fail-fast 行為
- [ ] 定義缺 provenance 資訊時 release workflow 的 fail-fast 行為
- [ ] 補版本與 provenance 的回歸測試

#### 3.2 Installer 版本資訊注入

- [ ] 盤點 `scripts/install-agent.py` 現有輸出與 manifest 欄位
- [ ] 在 installer 成功輸出中加入 `product_name`
- [ ] 在 installer 成功輸出中加入 `product_version`
- [ ] 在 installer 成功輸出中加入 `source_revision`
- [ ] 在 installer 成功輸出中加入 `install_timestamp`
- [ ] 在 `install-manifest.json` 中加入 `product_version`
- [ ] 在 `install-manifest.json` 中加入 `source_revision`
- [ ] 在 `install-manifest.json` 中加入 `packaged_at` 或等價欄位
- [ ] 確認 `--agent all` 的 manifest version 行為一致
- [ ] 更新 wrapper scripts 成功訊息以顯示版本
- [ ] 為 installer version injection 補測試
- [ ] 為 manifest version contract 補測試

#### 3.3 Doctor 版本與完整性契約

- [ ] 盤點 `scripts/doctor-agent.py` 現有 JSON 輸出欄位
- [ ] 在 doctor 輸出加入 `product_version`
- [ ] 在 doctor 輸出加入 `installed_version`
- [ ] 在 doctor 輸出加入 `source_revision`
- [ ] 在 doctor 輸出加入 manifest provenance 資訊
- [ ] 定義 doctor 對 version mismatch 的錯誤行為
- [ ] 定義 doctor 對 manifest 缺 provenance 欄位的錯誤行為
- [ ] 定義 doctor 對 partial install / corrupted install 的錯誤行為
- [ ] 將 `--verify-manifest-integrity` 擴充為同時驗證版本一致性
- [ ] 更新 doctor 文件以說明 healthy / unhealthy 判準
- [ ] 為 doctor version consistency 補 regression tests
- [ ] 為 manifest mismatch 補 regression tests

#### 3.4 Report artifacts 版本資訊注入

- [ ] 盤點 `run_accessibility_audit.py` 產出的 JSON / Markdown / SARIF / manifest 輸出
- [ ] 在 JSON report 中加入 tool version 欄位
- [ ] 在 Markdown report 中加入版本與 provenance 區塊
- [ ] 在 SARIF 中加入 tool version 或對應 metadata
- [ ] 在 `artifact-manifest.json` 中加入產品版本與 source revision
- [ ] 在 `summary-only` 輸出中加入最小必要版本資訊
- [ ] 定義 schema version 與 product version 的對應說明
- [ ] 定義 timestamp 欄位如何避免 snapshot 測試漂移
- [ ] 更新 sample artifacts 以反映新 metadata
- [ ] 為 report version injection 補 regression tests
- [ ] 為 artifact-manifest provenance 補 regression tests

#### 3.5 Release asset contract 設計

- [ ] 定義每次 release 必須產生的正式 assets 清單
- [ ] 定義 `codex` bundle ZIP 命名規則
- [ ] 定義 `claude` bundle ZIP 命名規則
- [ ] 定義 `gemini` bundle ZIP 命名規則
- [ ] 定義 `copilot` bundle ZIP 命名規則
- [ ] 定義 `all-in-one` bundle ZIP 命名規則
- [ ] 定義 checksum 檔命名規則
- [ ] 定義 release manifest 檔命名規則
- [ ] 定義哪些 assets 屬於公開交付物
- [ ] 定義哪些 artifacts 只屬於 CI triage，不應進 release
- [ ] 將 asset contract 文件化
- [ ] 為 asset naming 補 contract tests

#### 3.6 Packaging script 與 bundle 內容規範

- [ ] 新增 `scripts/package-release.py`
- [ ] 實作 release staging directory 建立流程
- [ ] 實作 agent-specific bundle 組裝流程
- [ ] 實作 `all-in-one` bundle 組裝流程
- [ ] 實作 package completeness validation
- [ ] 定義 bundle 內根目錄結構
- [ ] 定義 bundle 是否包含 schema artifacts
- [ ] 定義 bundle 是否包含 policy bundles
- [ ] 定義 bundle 是否包含 archive docs
- [ ] 定義 bundle 最小必要內容清單
- [ ] 確保 bundle 不混入 tests 或開發期垃圾檔
- [ ] 輸出 machine-readable packaging summary
- [ ] 為 packaging script 補單元測試
- [ ] 為 bundle completeness 補測試
- [ ] 為 deterministic packaging 補測試

#### 3.7 Checksum 與下載完整性驗證

- [ ] 決定 checksum 演算法固定為 `sha256`
- [ ] 決定 checksum file 格式為 plain text、JSON，或兩者並行
- [ ] 在 packaging script 中產出 checksum 檔
- [ ] 在 release manifest 中加入每個 asset 的 checksum
- [ ] 定義 downstream 使用者如何驗證 checksum
- [ ] 定義 checksum mismatch 的 triage 流程
- [ ] 評估 doctor 是否需要支援下載後 asset checksum 驗證
- [ ] 補 checksum 文件範例
- [ ] 為 checksum file format 補測試
- [ ] 為 checksum mismatch 補測試
- [ ] 為遺漏檔案或錯誤順序補測試

#### 3.8 GitHub Release workflow 自動化

- [ ] 在 `.github/workflows/` 新增正式 release workflow
- [ ] 定義 release workflow 觸發條件為 tag push
- [ ] 視需要加入 `workflow_dispatch`
- [ ] 定義 release workflow job 階段
- [ ] 加入 metadata validation step
- [ ] 加入測試執行 step
- [ ] 加入 packaging step
- [ ] 加入 clean smoke step
- [ ] 加入 checksum / manifest publish step
- [ ] 加入 GitHub Release 建立 step
- [ ] 加入 release asset upload step
- [ ] 定義任何 gate 失敗時不得 publish release
- [ ] 定義 release workflow logs / artifacts 保留策略
- [ ] 為 workflow 命名、觸發與 asset upload 補 contract tests

#### 3.9 GitHub Release notes 與 metadata

- [ ] 定義 release title 格式
- [ ] 定義 release body 來源策略
- [ ] 決定從 `CHANGELOG.md` 擷取對應 version section，或由 workflow 生 draft notes
- [ ] 定義 release notes 必含 highlights
- [ ] 定義 release notes 必含 breaking changes
- [ ] 定義 release notes 必含 known limitations
- [ ] 定義 release notes 必含 install / verify 指令
- [ ] 定義 release notes 必含 checksum verification 說明
- [ ] 補 release note template
- [ ] 補 hotfix release note template
- [ ] 更新 changelog discipline 文件

#### 3.10 One-click installer 體驗

- [ ] 定義「一鍵安裝」的正式交付方式
- [ ] 決定是否提供 `install-latest.ps1`
- [ ] 決定是否提供 `install-latest.sh`
- [ ] 定義 bootstrap script 支援的 flags
- [ ] 定義 bootstrap script 的 latest version resolution 行為
- [ ] 定義 bootstrap script 的指定版本下載行為
- [ ] 實作下載 release asset
- [ ] 實作 checksum 驗證
- [ ] 實作解壓到 temp dir
- [ ] 實作呼叫 installer
- [ ] 實作失敗後 temp 清理
- [ ] 實作成功後呼叫 doctor 或提示 doctor 驗證
- [ ] 定義 Python 缺失時的錯誤訊息
- [ ] 定義權限不足時的錯誤訊息
- [ ] 定義 network failure 時的錯誤訊息
- [ ] 為 bootstrap scripts 補測試或最少 smoke validation

#### 3.11 Clean environment adoption smoke

- [ ] 定義 clean environment 的正式支援矩陣
- [ ] 在文件中列出 Windows 支援條件
- [ ] 在文件中列出 macOS 支援條件
- [ ] 在文件中列出 Linux 支援條件
- [ ] 定義 clean smoke 必須從 release asset 開始，不得偷用 repo 相對路徑
- [ ] 設計 release-consumer smoke 流程
- [ ] 新增 `scripts/run-release-adoption-smoke.py`
- [ ] 支援 `--version`
- [ ] 支援 `--agent`
- [ ] 支援 `--asset-dir` 或等價離線來源
- [ ] 支援 `--keep-temp`
- [ ] 產出 `smoke-summary.json`
- [ ] 驗證 download -> checksum -> install -> doctor -> audit -> uninstall 全流程
- [ ] 定義 smoke 成功判準
- [ ] 定義 smoke 失敗時必保留的 triage 資訊
- [ ] 將 clean smoke 接入 release workflow
- [ ] 為 smoke summary contract 補測試

#### 3.12 Release workflow 與 rollback runbook

- [ ] 新增 `docs/release/ga-release-workflow.md`
- [ ] 補 pre-release checklist
- [ ] 補 version bump 流程
- [ ] 補 changelog finalize 流程
- [ ] 補 tag 建立流程
- [ ] 補 release workflow 觸發與監看流程
- [ ] 補 post-publish verification 流程
- [ ] 新增 `docs/release/rollback-playbook.md`
- [ ] 定義 rollback trigger 條件
- [ ] 定義 rollback owner / approver
- [ ] 定義 asset 壞檔時的處置
- [ ] 定義 installer 壞掉時的處置
- [ ] 定義 schema 相容性破壞時的處置
- [ ] 定義是否允許 yank release
- [ ] 定義不允許直接覆寫既有 tag 內容
- [ ] 定義 hotfix release 的命名與流程
- [ ] 補 rollback communication template
- [ ] 補 rollback 後 postmortem 要求

#### 3.13 GA definition 與相容性政策

- [ ] 新增 `docs/release/ga-definition.md`
- [ ] 定義 product scope
- [ ] 定義 intended user
- [ ] 定義 supported environments
- [ ] 定義 support boundaries
- [ ] 定義 non-goals
- [ ] 定義 GA quality gates
- [ ] 定義 compatibility promises
- [ ] 定義 known limitations 的允收標準
- [ ] 定義 semantic versioning 是否正式採用
- [ ] 定義 breaking change 的分類
- [ ] 定義 deprecation policy
- [ ] 定義 report schema versioning policy
- [ ] 定義 install-manifest 相容性政策
- [ ] 定義 adapter entrypoint path 相容性政策

#### 3.14 文件整併與入口收斂

- [ ] 更新 `README.md` 的產品化入口段落
- [ ] 在 `README.md` 補從 GitHub Release 安裝的最短路徑
- [ ] 在 `README.md` 補 install -> doctor -> first audit -> uninstall quickstart
- [ ] 更新 `docs/release/release-playbook.md` 以反映 M39 gate
- [ ] 更新 `docs/release/adoption-smoke-guide.md`
- [ ] 更新 `docs/release/supported-environments.md`
- [ ] 視需要新增 `docs/release/README.md` 或 release docs 索引
- [ ] 補 release-consumer smoke 與 repo-native smoke 的差異說明
- [ ] 收斂重複規則，避免同一決策散在多份文件
- [ ] 更新 `CHANGELOG.md` 的發版紀律說明

#### 3.15 測試矩陣與回歸覆蓋

- [ ] 更新 `TESTING-PLAN.md`，加入 M39 測試類別
- [ ] 新增 package manifest contract tests
- [ ] 新增 release asset naming tests
- [ ] 新增 bootstrap install tests
- [ ] 新增 version injection tests
- [ ] 新增 doctor version consistency tests
- [ ] 新增 release smoke tests
- [ ] 新增 checksum contract tests
- [ ] 新增 workflow contract tests
- [ ] 新增 non-happy-path 測試
- [ ] 為 snapshot 中的 timestamp / version 欄位建立 normalization 策略
- [ ] 驗證新增 metadata 不會讓既有 snapshot 不穩定
- [ ] 驗證 M39 新增測試與既有 real-scanner / CLI tests 不衝突

#### 3.16 建議實作順序

- [ ] 第一步：先完成版本單一來源與 provenance helper
- [ ] 第二步：完成 installer / doctor / report 的版本資訊注入
- [ ] 第三步：完成 packaging script 與 bundle contract
- [ ] 第四步：完成 checksum 與 release asset verification
- [ ] 第五步：完成 one-click installer 與 clean smoke
- [ ] 第六步：完成 GitHub Release workflow
- [ ] 第七步：完成 GA definition、rollback、docs 收斂
- [ ] 每一步完成後都更新測試與文件

#### 3.17 最小交付標準

- [ ] tag push 可自動產生正式 release assets
- [ ] 所有 installer / doctor / report artifacts 帶一致版本資訊
- [ ] release assets 可被 checksum 驗證
- [ ] clean environment adoption smoke 可成功執行
- [ ] rollback playbook 可供非作者依文件操作
- [ ] GA definition 文件已完成且與實作一致
- [ ] README 與 release docs 已反映正式產品化入口
- [ ] M39 新增測試已納入測試矩陣

#### 3.18 最終驗收條件

- [ ] 任一正式版本可從 GitHub Release 下載、驗證、安裝、doctor、執行 smoke、解除安裝
- [ ] release workflow 能在沒有人工補洞的情況下穩定產生完整 assets
- [ ] 版本、schema、manifest、checksum、artifact provenance 全部可追溯
- [ ] 發版失敗與發版後故障都有明確 rollback 路徑
- [ ] 外部 adopter 不需要依賴 repo 內部知識即可完成 first-run

#### 3.19 AI 執行批次總則

以下批次不是給人類 PM/工程師分派用，而是給 agent 直接執行的工作包。

每個 batch 都必須遵守：

- [ ] 只修改該 batch 明列允許的檔案範圍
- [ ] 不可破壞既有 CLI flags、exit codes、artifact 檔名、report schema version 契約
- [ ] 一律補對應測試或 contract validation
- [ ] 若變更輸出結構，必須同步更新文件與 sample artifacts
- [ ] 完成後必須留下可驗證證據：測試命令、輸出 artifact、或文件更新
- [ ] 若遇到需跨 batch 才能安全決定的契約，先補文件定義，再實作

#### 3.20 Agent Batch A: Version And Provenance Foundation

批次目標：

- 建立 M39 的共同基礎，讓 installer、doctor、report、packaging 共用同一套版本與 provenance 來源

允許修改檔案：

- [ ] `pyproject.toml`
- [ ] `skills/libro-agent-wcag/scripts/shared_constants.py`
- [ ] `skills/libro-agent-wcag/scripts/report_artifacts.py`
- [ ] `scripts/install-agent.py`
- [ ] `scripts/doctor-agent.py`
- [ ] `skills/libro-agent-wcag/scripts/tests/`
- [ ] `README.md`
- [ ] `docs/release/release-playbook.md`

主要工作：

- [ ] 盤點目前版本讀取與 provenance 來源
- [ ] 新增共用 helper，統一讀取 `product_version`
- [ ] 定義 `source_revision`、`build_timestamp` 或等價欄位
- [ ] 定義缺版本或缺 provenance 時的 fail-fast 行為
- [ ] 補單元測試與 contract tests

禁止事項：

- [ ] 不在這一批加入 release packaging
- [ ] 不在這一批新增 bootstrap installer
- [ ] 不重命名既有 artifacts

完成證據：

- [ ] 有共用 version/provenance helper 可被後續批次重用
- [ ] 測試可證明版本來源不再分散解析
- [ ] 文件已寫明版本與 provenance 來源

建議驗證命令：

- [ ] `python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"`

#### 3.21 Agent Batch B: Installer / Doctor / Report Version Injection

批次目標：

- 將 version/provenance 注入所有對外輸出與 machine-readable artifacts

允許修改檔案：

- [ ] `scripts/install-agent.py`
- [ ] `scripts/install-agent.ps1`
- [ ] `scripts/install-agent.sh`
- [ ] `scripts/doctor-agent.py`
- [ ] `skills/libro-agent-wcag/scripts/run_accessibility_audit.py`
- [ ] `skills/libro-agent-wcag/scripts/report_artifacts.py`
- [ ] `docs/testing/realistic-sample/artifacts/`
- [ ] `skills/libro-agent-wcag/scripts/tests/`
- [ ] `README.md`
- [ ] `docs/release/adoption-smoke-guide.md`

主要工作：

- [ ] installer success output 補 `product_version`、`source_revision`
- [ ] `install-manifest.json` 補版本與 provenance 欄位
- [ ] doctor JSON 輸出補版本一致性資訊
- [ ] report JSON / Markdown / SARIF / artifact manifest 補版本 metadata
- [ ] `summary-only` 輸出補最小必要版本資訊
- [ ] 更新 sample artifacts 與 snapshots

禁止事項：

- [ ] 不在這一批建立 release workflow
- [ ] 不在這一批建立 package ZIP
- [ ] 不改動 report schema version 命名策略，除非已有明確文件變更

完成證據：

- [ ] installer、doctor、report 都能輸出一致版本資訊
- [ ] sample artifacts 已反映新欄位
- [ ] regression tests 通過

建議驗證命令：

- [ ] `python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"`

#### 3.22 Agent Batch C: Release Packaging And Checksum

批次目標：

- 建立可重複的 release bundle、checksum、release manifest 產生流程

允許修改檔案：

- [ ] `scripts/package-release.py`
- [ ] `README.md`
- [ ] `docs/release/release-playbook.md`
- [ ] `docs/release/supported-environments.md`
- [ ] `docs/release/adoption-smoke-guide.md`
- [ ] `skills/libro-agent-wcag/scripts/tests/`

主要工作：

- [ ] 定義 release assets 清單與命名規則
- [ ] 實作 agent-specific bundle 組裝
- [ ] 實作 `all-in-one` bundle 組裝
- [ ] 產出 `sha256` checksum 檔
- [ ] 產出 release manifest
- [ ] 補 package completeness / deterministic packaging tests

禁止事項：

- [ ] 不在這一批接 GitHub Release API 或 workflow publish
- [ ] 不在這一批加入 remote download installer
- [ ] 不把 tests 或 archive docs 混入正式 bundle，除非文件先定義為必要內容

完成證據：

- [ ] 從 repo 根目錄可產出完整 release assets
- [ ] bundle 命名、checksum、manifest 與文件一致
- [ ] packaging tests 通過

建議驗證命令：

- [ ] `python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"`

#### 3.23 Agent Batch D: Bootstrap Installers And Clean Release Smoke

批次目標：

- 讓外部 adopter 以 release consumer 路徑完成下載、驗證、安裝、doctor、audit、解除安裝

允許修改檔案：

- [ ] `scripts/install-latest.ps1`
- [ ] `scripts/install-latest.sh`
- [ ] `scripts/run-release-adoption-smoke.py`
- [ ] `docs/release/adoption-smoke-guide.md`
- [ ] `docs/release/supported-environments.md`
- [ ] `README.md`
- [ ] `skills/libro-agent-wcag/scripts/tests/`

主要工作：

- [ ] 實作 latest / pinned version 下載流程
- [ ] 串接 checksum verify -> install -> doctor -> audit -> uninstall
- [ ] 產出 `smoke-summary.json`
- [ ] 定義 clean environment 成功判準
- [ ] 補 bootstrap / smoke tests

禁止事項：

- [ ] 不在這一批改 release workflow publish 策略
- [ ] 不跳過 checksum 驗證
- [ ] 不直接依賴 repo 相對路徑冒充 release-consumer flow

完成證據：

- [ ] clean release smoke 可在 release asset 路徑下成功執行
- [ ] 失敗時能保留 triage artifacts
- [ ] 文件已能描述 release-consumer flow

建議驗證命令：

- [ ] `python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"`

#### 3.24 Agent Batch E: GitHub Release Workflow, GA Definition, Rollback

批次目標：

- 將 release 流程正式化，形成可自動 publish、可回滾、可驗收的 GA 產品化交付鏈

允許修改檔案：

- [ ] `.github/workflows/release.yml`
- [ ] `README.md`
- [ ] `CHANGELOG.md`
- [ ] `TESTING-PLAN.md`
- [ ] `docs/release/ga-definition.md`
- [ ] `docs/release/ga-release-workflow.md`
- [ ] `docs/release/rollback-playbook.md`
- [ ] `docs/release/release-playbook.md`
- [ ] `docs/release/adoption-smoke-guide.md`
- [ ] `docs/release/supported-environments.md`
- [ ] `skills/libro-agent-wcag/scripts/tests/`

主要工作：

- [ ] 新增 release workflow
- [ ] 接上 test -> package -> clean smoke -> publish 流程
- [ ] 定義 publish gate 與 artifact retention
- [ ] 補 GA definition
- [ ] 補 rollback runbook 與禁止直接覆寫 tag 的政策
- [ ] 更新 README / changelog discipline / testing plan

禁止事項：

- [ ] 不改掉既有 required real-scanner lane 契約
- [ ] 不繞過失敗 gate 強行 publish
- [ ] 不用未文件化的人工步驟取代正式 workflow

完成證據：

- [ ] tag push 可自動建立正式 release
- [ ] workflow contract tests 通過
- [ ] GA definition 與 rollback 文件可支持非作者操作

建議驗證命令：

- [ ] `python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"`

#### 3.25 AI 執行順序

- [ ] 先執行 Batch A
- [ ] 再執行 Batch B
- [ ] 再執行 Batch C
- [ ] 再執行 Batch D
- [ ] 最後執行 Batch E
- [ ] 每個 batch 完成後都要更新相鄰文件與測試

#### 3.26 文件先行 / Code 先行原則

文件先行：

- [ ] release asset 清單與命名規則
- [ ] checksum / release manifest 格式
- [ ] GA blocker / non-blocker 定義
- [ ] rollback 禁止事項與 hotfix 原則
- [ ] clean environment 成功判準

Code 先行：

- [ ] version/provenance helper
- [ ] installer / doctor / report version injection
- [ ] `scripts/package-release.py`
- [ ] `scripts/install-latest.ps1`
- [ ] `scripts/install-latest.sh`
- [ ] `scripts/run-release-adoption-smoke.py`
- [ ] `.github/workflows/release.yml`

同步收斂：

- [ ] `README.md`
- [ ] `docs/release/release-playbook.md`
- [ ] `docs/release/adoption-smoke-guide.md`
- [ ] `docs/release/supported-environments.md`
- [ ] `TESTING-PLAN.md`

### 4. 提升高價值但目前仍屬 manual/assisted 的 remediation 能力

狀態：暫緩，待重構與 CI 自動化後再討論。

討論 TODO：

- [ ] 盤點哪些 assisted/manual rule family 若改善，會帶來最高使用價值
- [ ] 評估下一步應該優先做更好的 remediation guidance、structured patch proposal，或有限度 deterministic fix
- [ ] 檢視高影響候選項，例如 `heading-order`、`region`、`skip-link`、`tabindex`、`nested-interactive`
- [ ] 在擴大 remediation 能力之前，定義可接受的安全邊界
- [ ] 決定後續改善應聚焦在 framework-aware hints、 richer reports，還是實際檔案修改能力
