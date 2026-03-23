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

- [ ] 新增 real-scanner workflow 檔案
- [ ] 將 workflow `name` 固定為 `libro-agent-wcag-real-scanner`
- [ ] 將主要 job `name` 固定為 `libro-agent-wcag-real-scanner`
- [ ] workflow 加入 `pull_request` trigger
- [ ] workflow 加入 `workflow_dispatch` trigger
- [ ] 文件中明確記錄 branch protection required check 名稱為 `libro-agent-wcag-real-scanner`
- [ ] 確保 workflow 與 job 名稱不會因 artifact/step 調整而改動
- [ ] 在文件中明確定義此 lane 失敗即阻擋 PR merge

#### 2.2 Scanner 工具安裝與版本固定

- [ ] 固定 workflow 使用的 Python 版本
- [ ] 固定 workflow 使用的 Node.js 版本
- [ ] 固定 `@axe-core/cli` 版本字串
- [ ] 固定 `lighthouse` 版本字串
- [ ] 將 Python 版本設定寫入 workflow 單一位置
- [ ] 將 Node.js 版本設定寫入 workflow 單一位置
- [ ] 將 scanner 版本設定寫入 workflow 單一位置
- [ ] workflow 加入 Python 依賴安裝 step
- [ ] workflow 加入固定版本 scanner 安裝 step
- [ ] workflow 加入版本輸出 step，記錄 Python/Node/axe/lighthouse 版本
- [ ] 版本資訊納入 triage artifact 或 preflight log
- [ ] 確保 scanner 升級只需修改單一設定區塊

#### 2.3 Live Scanner 環境要求

- [ ] workflow runner 固定為 `ubuntu-latest`
- [ ] 新增 browser availability 驗證 step
- [ ] browser 驗證 step 只檢查可用性，不額外安裝 Chrome
- [ ] 明確驗證 headless Chrome/Chromium 可供 Lighthouse 啟動
- [ ] 明確驗證 `npx --no-install @axe-core/cli --version`
- [ ] 明確驗證 `npx --no-install lighthouse --version`
- [ ] 若 browser 不可用，workflow 直接 fail
- [ ] 若 axe 不可用，workflow 直接 fail
- [ ] 若 lighthouse 不可用，workflow 直接 fail
- [ ] 將「browser/scanner 不可用即 fail」規則寫入文件

#### 2.4 掃描目標與範圍

- [ ] 將 live scanner target 固定為 `docs/testing/realistic-sample/mixed-findings.html`
- [ ] workflow 內 target 路徑集中在單一 env 或單一 step 變數
- [ ] 測試與文件共用同一個 target 路徑字串
- [ ] 初期只掃描單一 fixture，不擴展第二個 target
- [ ] 文件中註明此 target 旨在覆蓋 mixed findings / manual review / apply-fixes 行為
- [ ] 若要新增第二個 target，必須另開 TODO，不在本輪順手加入

#### 2.5 Workflow 內的執行步驟

- [ ] 加入 repository checkout step
- [ ] 加入 Python setup step
- [ ] 加入 Node.js setup step
- [ ] 加入 Python dependencies install step
- [ ] 加入固定版本 scanner install step
- [ ] 加入 browser availability verify step
- [ ] 加入 scanner preflight step
- [ ] scanner preflight step 執行 `--preflight-only`
- [ ] 加入 live audit step
- [ ] live audit step 指向固定 mixed-findings target
- [ ] live audit step 產出 `wcag-report.json`
- [ ] live audit step 產出 `wcag-report.md`
- [ ] live audit step 產出 `wcag-report.sarif`
- [ ] live audit step 產出 raw scanner outputs
- [ ] live audit step 產出 capability negotiation 相關 artifact
- [ ] 加入 artifact upload step
- [ ] 任一步驟非零退出時 job 直接 fail，不做 fallback

#### 2.6 Artifact 與 Triage 輸出

- [ ] upload `axe.raw.json`
- [ ] upload `lighthouse.raw.json`
- [ ] upload `normalized-summary.live.json`
- [ ] upload `capability-negotiation.json`
- [ ] upload `wcag-report.json`
- [ ] upload `wcag-report.md`
- [ ] upload `wcag-report.sarif`
- [ ] upload preflight log 或版本輸出 artifact
- [ ] artifact retention 固定為 `14` 天
- [ ] upload step 使用 `if: always()` 以保留失敗時 triage 資訊
- [ ] artifact 名稱在 workflow 與文件中保持一致
- [ ] 文件列出每個 artifact 的用途

#### 2.7 Fail-Fast 與阻擋條件

- [ ] 定義 Python/Node/scanner install 失敗即 fail
- [ ] 定義 browser verification 失敗即 fail
- [ ] 定義 scanner preflight 失敗即 fail
- [ ] 定義 axe 執行失敗即 fail
- [ ] 定義 lighthouse 執行失敗即 fail
- [ ] 定義 report artifact 缺失即 fail
- [ ] 定義 artifact upload step 自身失敗即 fail
- [ ] 明確禁止 mock/fallback 取代 live scanner gate
- [ ] 文件化 fail-fast matrix 與對應 triage artifact

#### 2.8 與現有 Deterministic Lane 的關係

- [ ] 保留既有 deterministic lane workflow 不刪除
- [ ] 文件明確區分 deterministic lane 與 live lane 用途
- [ ] 確保 deterministic lane 不是 required check
- [ ] 確保 `libro-agent-wcag-real-scanner` 是 required check
- [ ] 確保兩條 lane 的 artifact 名稱不衝突
- [ ] 確保 reviewer 能從名稱分辨 mock lane 與 live lane
- [ ] 補測試或文件以防止之後把兩條 lane 混成同一條

#### 2.9 文件與 Repo 契約同步

- [ ] 更新 `docs/release/real-scanner-ci-lane.md`
- [ ] 在文件中寫明 workflow / job / required check 名稱
- [ ] 在文件中寫明 runner 為 `ubuntu-latest`
- [ ] 在文件中寫明 browser 策略為「驗證可用，不額外安裝」
- [ ] 在文件中寫明 target 固定為 mixed-findings fixture
- [ ] 在文件中寫明 artifact retention 為 `14` 天
- [ ] 在文件中寫明固定保留 `wcag-report.sarif`
- [ ] 更新 `docs/release/resilient-run-patterns.md`
- [ ] 視需要更新 `docs/release/release-playbook.md`
- [ ] 視需要更新 `README.md`
- [ ] 確保文件反映「PR gate、live-only、scanner 不可用即 fail」最終決策

#### 2.10 測試與驗證

- [ ] 更新 `test_real_scanner_ci_lane.py`
- [ ] 新增/更新 workflow 名稱與 job 名稱 contract 測試
- [ ] 新增/更新 required check 名稱 contract 測試
- [ ] 新增/更新 artifact retention contract 測試
- [ ] 新增/更新 `wcag-report.sarif` artifact contract 測試
- [ ] 視需要更新 `test_release_docs.py`
- [ ] 視需要更新 workflow contract 測試
- [ ] 驗證 workflow 路徑與 repo 內實際檔案一致
- [ ] 驗證 artifact 名稱與文件一致
- [ ] 驗證 required check 名稱與 workflow 定義一致

#### 2.11 建議實作順序

- [ ] 第一步：先落 workflow 名稱 / job 名稱 / trigger / required check
- [ ] 第二步：固定 Python / Node / axe / lighthouse 版本
- [ ] 第三步：加入 browser verify + preflight + live audit step
- [ ] 第四步：補齊 artifact upload 與 retention
- [ ] 第五步：同步文件與 contract tests
- [ ] 第六步：在 PR 上驗證 required check 與 fail-fast 行為

#### 2.12 最小交付標準

- [ ] PR 開啟時會自動觸發 `libro-agent-wcag-real-scanner`
- [ ] `workflow_dispatch` 可手動重跑 `libro-agent-wcag-real-scanner`
- [ ] lane 失敗時會阻擋 PR
- [ ] browser / scanner 不可用時不降級為 mock，直接 fail
- [ ] mixed-findings target 可穩定執行
- [ ] `wcag-report.sarif` 與其他 triage artifact 皆可保留
- [ ] retention 設定為 `14` 天
- [ ] 文件與測試已同步更新

#### 2.13 最終驗收條件

- [ ] `libro-agent-wcag-real-scanner` 已成為正式 required PR check
- [ ] 固定版本的 scanner toolchain 可重現
- [ ] scanner / browser / preflight 失敗時有足夠 artifact 可排查
- [ ] 現有 deterministic lane 仍可正常運作
- [ ] repo 文件已完整反映此 CI gate 決策

## 暫緩，作為下一步討論方向

以下項目目前刻意暫緩，待前兩個主方向完成後，再作為下一輪討論 backlog。

### 3. 補完整產品化輸出介面

狀態：暫緩。目前尚未進入可發佈階段。

討論 TODO：

- [ ] 決定專案何時要從 repo-native 使用模式進入可發佈狀態
- [ ] 定義穩定對外介面應該是 CLI、package entrypoint，或兩者都要
- [ ] 決定是否需要補強 packaging metadata、extras、以及 install UX
- [ ] 確認對外發佈前需要達到哪些 adoption 保證
- [ ] 定義內部工程工具與對外產品介面的邊界

### 4. 提升高價值但目前仍屬 manual/assisted 的 remediation 能力

狀態：暫緩，待重構與 CI 自動化後再討論。

討論 TODO：

- [ ] 盤點哪些 assisted/manual rule family 若改善，會帶來最高使用價值
- [ ] 評估下一步應該優先做更好的 remediation guidance、structured patch proposal，或有限度 deterministic fix
- [ ] 檢視高影響候選項，例如 `heading-order`、`region`、`skip-link`、`tabindex`、`nested-interactive`
- [ ] 在擴大 remediation 能力之前，定義可接受的安全邊界
- [ ] 決定後續改善應聚焦在 framework-aware hints、 richer reports，還是實際檔案修改能力
