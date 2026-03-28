# 批次掃描與彙總報告功能 — 待辦事項

> 規劃時間：2026-03-28
> 目標：讓使用者對目錄、檔案清單等多目標輸入產出彙總無障礙報告，涵蓋缺失數量、嚴重度分級、合規率、可修正性分析等決策所需資訊。
> 相關文件：[20260328_todo.md](20260328_todo.md)（主待辦清單）

---

## 架構：兩層分離設計

```
                    輸入                        處理                        輸出
              ┌──────────────┐          ┌────────────────┐         ┌──────────────────┐
  目錄/清單 → │ libro scan   │ → 多份   │ libro report   │ →       │ 彙總報告          │
  glob 模式   │ (批次掃描)    │   JSON   │ (彙總分析)      │         │ JSON / MD / 終端  │
              └──────────────┘          └────────────────┘         └──────────────────┘
```

- **Layer 1 — `libro scan`（批次掃描）**：接受目錄 / glob / 檔案清單，對每個目標呼叫現有 `run_accessibility_audit.py`，各自產出 `wcag-report.json`。
- **Layer 2 — `libro report`（彙總報告）**：讀取多份 `wcag-report.json`，產出彙總分析報告。JSON 為唯一資料源，其他格式皆為 renderer。

建議先做 Layer 2（`libro report`），因為 `scan` 只是 audit 的 for-loop 包裝，而 `report` 才是真正的新價值。

---

## A. 報告內容區段（依優先級排列）

- [x] **A1** **總覽（Executive Summary）**：掃描範圍（目標數、WCAG 版本/等級）、總缺失數、合規率（無缺失目標 / 總目標）、結論（pass / fail / needs-review）。
  > 📋 **優先級：P0。** 最核心的數字，立即有用。
  > ✅ 實作於 `aggregate_report.py:_build_scope()`

- [x] **A2** **嚴重度分級（Severity Breakdown）**：critical / serious / moderate / minor / info 各數量與佔比；橫條圖視覺化；與上次基線比較的變化（如有 baseline）。
  > 📋 **優先級：P0。**
  > ✅ 實作於 `aggregate_report.py:_build_severity()` + `report_renderers.py` 橫條圖

- [x] **A3** **可修正性分析（Fixability Analysis）**：auto-fix / assisted / manual 各數量與佔比；預估「跑一次 apply-fixes 可解決 X% 問題」的修復覆蓋率。
  > 📋 **優先級：P0。** 本系統的差異化價值。
  > ✅ 實作於 `aggregate_report.py:_build_fixability()`

- [x] **A4** **各目標明細（Per-Target Breakdown）**：每個目標的缺失數、嚴重度分佈、狀態標記（✓ clean / ⚠ issues / ✗ critical）；可折疊的個別 finding 清單。
  > 📋 **優先級：P0。** 開發者最需要知道「改哪裡」。
  > ✅ 實作於 `aggregate_report.py:_build_targets()` + `report_renderers.py` `<details>` 折疊

- [x] **A5** **WCAG SC 涵蓋分析（Success Criteria Coverage）**：有觸發的 SC 清單；按 WCAG 四原則分群（Perceivable / Operable / Understandable / Robust）各原則缺失佔比；未涵蓋的 SC（掃描器無法檢測，需人工審核）。
  > 📋 **優先級：P1。** 合規報告必備。
  > ✅ 實作於 `aggregate_report.py:_build_wcag_principles()` + 兩種 renderer

- [x] **A6** **熱點分析（Top Issues）**：Top N 規則（出現次數排序）；Top N 目標（缺失最多的頁面）；跨目標重複出現的系統性問題。
  > 📋 **優先級：P1。** 幫助決定修復優先級。
  > ✅ 實作於 `aggregate_report.py:_build_top_rules()` + 兩種 renderer

- [x] **A7** **自動修正機會（Auto-Fix Opportunity）**：可修正清單、按框架分群建議（React / Vue / Next.js）、預計修正後殘餘缺失數、建議執行指令。
  > 📋 **優先級：P1。**
  > ✅ 實作於 `aggregate_report.py:_build_auto_fix_opportunity()` — 含 framework_groups

- [ ] **A8** **修復生命週期（Remediation Lifecycle）**：planned → implemented → verified 各階段數量；已修復但未驗證的項目；需要人工審核的項目；修復進度百分比。
  > 📋 **優先級：P2。** 追蹤修復進度。

- [ ] **A9** **趨勢與基線比較（Trend / Baseline Diff）**：新增的缺失（本次出現、上次沒有）；已解決的缺失；持續存在的債務；債務 waiver 狀態（已過期？即將過期？）；折線圖。
  > 📋 **優先級：P2。** 需要歷史資料，第二階段做。

- [ ] **A10** **掃描器健康狀態（Scanner Health）**：axe / lighthouse 版本與狀態；是否有 scanner failure / fallback findings；掃描耗時。
  > 📋 **優先級：P3。** 除錯用。

---

## B. 輸出格式（依實作順序）

- [x] **B1** **JSON 輸出**：彙總報告的機器可讀格式，作為所有其他格式的唯一資料源。包含 `scope`、`severity`、`fixability`、`wcag_principles`、`top_rules`、`targets`、`remediation_lifecycle`、`baseline_diff`、`auto_fix_opportunity` 等頂層 key。
  > 📋 **優先級：P0。** 基礎資料結構，其他格式都從它轉換。
  > ✅ 實作於 `aggregate_report.py:build_aggregate_report()` + `write_aggregate_json()`

- [x] **B2** **Terminal 輸出**：開發者即時查看的終端格式，含色彩標記、橫條圖、嚴重度圖示。預設格式（`--format terminal`）。
  > 📋 **優先級：P0。**
  > ✅ 實作於 `report_renderers.py:render_terminal()`

- [x] **B3** **Markdown 輸出**：可直接貼到 GitHub PR comment / issue 的格式，含表格、emoji 嚴重度標記、`<details>` 折疊。`--format markdown`。
  > 📋 **優先級：P0。**
  > ✅ 實作於 `report_renderers.py:render_markdown()`

- [ ] **B4** **HTML 輸出**：單一自包含 HTML 檔（inline CSS + inline SVG 圓餅圖/橫條圖，零外部依賴），可瀏覽器開啟、email 附件、存檔交付。`--format html --output wcag-dashboard.html`。
  > 📋 **優先級：P1。** 對外交付最有說服力。

- [ ] **B5** **CSV 輸出**：每個 finding 一行，含 target / rule_id / severity / fixability / sc / status / changed_target，Excel 可直接篩選排序。`--format csv`。
  > 📋 **優先級：P2。**

- [ ] **B6** **Badge 輸出**：Shields.io endpoint JSON 格式，可嵌入 README 顯示合規標章（色彩依合規率變化）。`--format badge --output badge.json`。
  > 📋 **優先級：P3。** 錦上添花。

---

## C. CLI 入口

- [x] **C1** **`libro report` 子命令**：接受目錄或多個 `wcag-report.json` 路徑，產出彙總報告。`--format <terminal|json|markdown|html|csv|badge>`、`--output <path>`、`--baseline <prior-report.json>`。
  > 📋 **優先級：P0。** 核心新功能。
  > ✅ 實作於 `scripts/libro.py:handle_report()` — 支援 `--format json|terminal|markdown`、`--output`、`--language`

- [x] **C2** **`libro scan` 子命令**：接受目錄 / glob / `--targets <file>` 清單，對每個目標呼叫 `run_accessibility_audit.py`，支援 `--parallel <N>` 並行、`--output-dir` 指定輸出根目錄。錯誤收集與部分失敗處理。
  > 📋 **優先級：P1。** `libro report` 可先用手動跑多次 `libro audit` 的結果。
  > ✅ 實作於 `scripts/libro.py:handle_scan()` — 支援 `--parallel`、`--output-dir`、`--targets`、`--execution-mode`

---

## D. JSON 輸出結構草案

```jsonc
{
  "report_type": "aggregate",
  "generated_at": "2026-03-28T15:00:00Z",
  "standard": { "wcag_version": "2.1", "conformance_level": "AA" },

  // A1: 總覽
  "scope": {
    "total_targets": 12,
    "targets_with_issues": 9,
    "clean_targets": 3,
    "compliance_rate": 0.25
  },

  // A2: 嚴重度
  "severity": {
    "critical": { "count": 8, "percentage": 17.0 },
    "serious": { "count": 21, "percentage": 44.7 },
    "moderate": { "count": 12, "percentage": 25.5 },
    "minor": { "count": 6, "percentage": 12.8 },
    "info": { "count": 0, "percentage": 0.0 }
  },

  // A3: 可修正性
  "fixability": {
    "auto-fix": { "count": 32, "percentage": 68.1 },
    "assisted": { "count": 9, "percentage": 19.1 },
    "manual": { "count": 6, "percentage": 12.8 }
  },

  // A5: WCAG 原則
  "wcag_principles": {
    "perceivable":    { "count": 20, "sc": ["1.1.1", "1.3.1", "1.4.3"] },
    "operable":       { "count": 12, "sc": ["2.1.1", "2.4.3", "2.4.4"] },
    "understandable": { "count": 10, "sc": ["3.1.1", "3.3.2"] },
    "robust":         { "count": 5,  "sc": ["4.1.2"] }
  },

  // A6: 熱點
  "top_rules": [
    { "rule_id": "image-alt", "count": 12, "fixability": "auto-fix", "sc": ["1.1.1"] },
    { "rule_id": "button-name", "count": 8, "fixability": "auto-fix", "sc": ["4.1.2"] }
  ],

  // A4: 各目標
  "targets": [
    {
      "target": "src/index.html",
      "total_findings": 12,
      "severity": { "critical": 3, "serious": 5, "moderate": 4 },
      "auto_fixable": 9,
      "status": "critical"
    }
  ],

  // A8: 修復生命週期
  "remediation_lifecycle": {
    "planned": 47,
    "implemented": 0,
    "verified": 0,
    "manual_review_required": 6,
    "fix_coverage": 0.0
  },

  // A9: 基線比較（可選）
  "baseline_diff": null,

  // A7: 自動修正機會
  "auto_fix_opportunity": {
    "fixable_count": 32,
    "estimated_residual": 15,
    "command": "libro scan ./src --execution-mode apply-fixes"
  }
}
```

---

## 執行批次摘要

| Batch | 項目 | 說明 |
| --- | --- | --- |
| **報告-P0** | A1, A2, A3, A4, B1, B2, B3, C1 | 核心報告引擎 + JSON/Terminal/Markdown 輸出 + libro report CLI |
| **報告-P1** | A5, A6, A7, B4, C2 | WCAG SC 分析 + 熱點 + HTML 儀表板 + libro scan CLI |
| **報告-P2** | A8, A9, B5 | 修復生命週期 + 趨勢 + CSV |
| **報告-P3** | A10, B6 | 掃描器健康 + Badge |
