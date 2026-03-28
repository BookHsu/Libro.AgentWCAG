# 真實掃描器 CI 通道

本指南定義目前正式作為 PR gate 的即時 real-scanner GitHub Actions 通道，用於依賴真實掃描器的驗證流程。

## 工作流程合約

- 工作流程路徑：[`.github/workflows/libro-wcag-real-scanner.yml`](../../.github/workflows/libro-wcag-real-scanner.yml)
- 工作流程名稱：`libro-wcag-real-scanner`
- Job 名稱：`libro-wcag-real-scanner`
- 觸發事件：
  - `pull_request`
  - `workflow_dispatch`
- 分支保護所需的 check 名稱：`libro-wcag-real-scanner`

這條通道只允許使用即時 real-scanner 執行，不會退回到 mock scanner payloads。

## 執行期策略

- Runner：`ubuntu-latest`
- 瀏覽器策略：確認 runner 上已存在受支援的 Chrome/Chromium binary；工作流程中不得自行安裝 Chrome
- 固定掃描器版本：
  - `@axe-core/cli@4.10.2`
  - `lighthouse@12.3.0`
- 固定目標：
  - `docs/testing/realistic-sample/mixed-findings.html`

## Fail-Fast 策略

只要出現下列任一情況，工作流程必須立即失敗：

- Python 或 Node.js 設定失敗
- 固定掃描器工具鏈安裝失敗
- 瀏覽器可用性驗證失敗
- 掃描器 preflight 失敗
- `axe` 執行失敗
- `lighthouse` 執行失敗
- 未產出預期的報告工件
- 工件上傳步驟失敗

此 PR gate 不允許使用 mock payloads 或 deterministic fallback。

## 工件合約

通道證據應儲存在 `out/real-scanner` 之下。

所有工件一律保留 `14` 天。

預期的 triage 工件如下：

- raw logs：
  - `raw/python.version.log`
  - `raw/node.version.log`
  - `raw/axe.version.log`
  - `raw/lighthouse.version.log`
  - `raw/browser.version.log`
- preflight：
  - `preflight.json`
- normalized summary：
  - `normalized-summary.live.json`
- capability negotiation：
  - `capability-negotiation.json`
- normalized report outputs：
  - `live/wcag-report.json`
  - `live/wcag-report.md`
  - `live/wcag-report.sarif`
  - `live/artifact-manifest.json`

上傳到 GitHub 的 artifact 名稱為 `libro-wcag-real-scanner-artifacts`。

## 能力協商工件

`capability-negotiation.json` 是交接索引，必須包含下列欄位：

- `lane_mode`
- `scanners_available`
- `required_check`
- `target`
- `summary_artifacts`
- `report_artifacts`
- `raw_scanner_logs`

## Triage 交接

建立 triage 項目時，應一併附上：

1. `capability-negotiation.json`
2. `normalized-summary.live.json`
3. `live/wcag-report.json`
4. `live/wcag-report.sarif`
5. 執行期診斷所需的任何原始版本／瀏覽器日誌

這樣可以讓 PR 審查與本機重現保持一致。
