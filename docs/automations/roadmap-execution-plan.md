# Roadmap 執行計畫

> 決策日期：2026-03-28
> 基於 `20260328_todo.md` 掃描結果 + 用戶決策

---

## Batch 1：低成本快速修正（10 項）

預估影響：少量程式碼 + 測試，每項 1-2 個檔案

| ID | 任務 | 決策 |
|---|---|---|
| W1 | `uninstall-agent.py` 加 try/except 處理 shutil.rmtree 錯誤 | 立即修 |
| R4 | `scanner_runtime.py` 加 macOS Chrome 路徑 `/Applications/Google Chrome.app/...` | 立即加 |
| Q1 | `install-skill.yml` 改 `repository: BookHsu/Libro.AgentWCAG.clean` → `${{ github.repository }}` | 立即改 |
| Q2 | `install-skill.yml` 加 doctor 失敗時的 output | 立即加 |
| E6 | README 的 Claude Marketplace 安裝指令加「Coming soon」註記 | 保留但加註 |
| H3 | `mcp-server/requirements.txt` 加 hash-pinned lock | 立即加 |
| O2 | scanner 部分失敗時 Markdown 摘要加 ⚠️ 警告標記 | 立即加 |
| O3 | report_schema_version 與 schema 檔案版本交叉驗證 | 立即補 |
| S2 | `normalize_report.py` 路徑不存在時給友善錯誤 | 立即改善 |
| T2 | `publish-npm.yml` 加 `npm pack --dry-run` 步驟 | 立即加 |

---

## Batch 2：文件與合約更新（7 項執行 + 5 項關閉）

預估影響：Markdown 文件為主，少量程式碼

### 執行

| ID | 任務 | 決策 |
|---|---|---|
| A3 | 各 adapter prompt-template.md 加進階選項區塊 + 建立 `references/cli-reference.md` 統一文件 | A+B |
| B3 | core-spec.md 加 schema versioning policy 文件 + 程式碼層級版本比較 | A+B |
| S1 | SKILL.md / core-spec.md 文件限縮 output_language 為 en/zh-TW，保留 fallback 擴充設計 | 文件限縮 |
| I1 | SKILL.md 說明目前支援 en/zh-TW，其他語言 fallback 為 en | 文件限縮 |
| I2 | 實作 prompt 語言與 output 語言分離 | 實作分離 |
| F1 | `remediation_library.py` 加 color-contrast 明確「不支援 auto-fix」標記 + 原因 | 加標記 |

### 關閉（決策為暫不處理或維持現狀）

| ID | 原因 |
|---|---|
| D1 | 官方目前發布版本已不用 key |
| D2 | 維持現狀，重複度可接受 |
| D4 | 目前可正常使用 |
| C2 | GitHub 無法驗證 Windows |
| T1 | 維持可選，依賴極少 |
| F3 | 列為下一版 |

---

## Batch 3：程式碼重構（4 項）

預估影響：核心 Python 模組重構，需回歸測試

| ID | 任務 | 決策 |
|---|---|---|
| R1 | `auto_fix.py` 提取共用 `_fix_missing_accessible_name()` 降低 _fix_button/link/role_name 重複 | 立即重構 |
| R3 | 合併 `AXE_RULE_TO_SC` + `LIGHTHOUSE_RULE_TO_SC` 為單一 `SCANNER_RULE_TO_SC` 表 | 合併 |
| R5 | `_guess_accessible_name()` diff description 加 `(guessed from: <attr>)` 來源 | 立即加 |
| Q3 | `real-scanner.yml` 改用 CLI `--report-format sarif` 取代 import 私有 `_report_to_sarif` | 改用 CLI |

---

## Batch 4：功能實作（6 項）

預估影響：較大的功能變更，需新增測試

| ID | 任務 | 決策 |
|---|---|---|
| O1 | 實作 create mode guidance-only 降級路徑（目標不存在時產出 manual-review guidance 而非報錯） | 實作 |
| J2 | `run_accessibility_audit.py` 改用 `concurrent.futures` 平行執行 axe + Lighthouse | 改平行 |
| L1 | `install-agent.py` 實作安裝失敗時的 rollback 機制 | 實作 rollback |
| L2 | `install-agent.py` --force 加版本檢查 + 備份舊版 | 加版本檢查+備份 |
| H1 | MCP `audit_page.py` 加 path resolve + 目錄限制防路徑穿越 | 加防護 |
| P1 | `validate_skill.py` 維護 known-rules 清單驗證 policy bundle rule ID | 維護清單 |

---

## Batch 5：測試補齊（7 項）

預估影響：新增測試檔案 + fixture snapshots

| ID | 任務 | 決策 |
|---|---|---|
| C5 | 加 MCP tool 參數預設值與 SKILL.md 合約一致性測試 | 立即補 |
| V1+V2 | 在測試端加 jsonschema 驗證（非 runtime），加 jsonschema 為 test 依賴 | 測試端驗證 |
| X1 | 15 個 fixture 全部補齊 `.report.json` snapshot baseline | 全部補齊 |
| X2 | snapshot 與 adapter 範例進一步對齊 | 進一步對齊 |
| Z3 | CI 加 HTTP HEAD 檢查驗證 WCAG Understanding URL 有效性 | 加檢查 |
| T3 | `release.yml` smoke test 改為 matrix 測 4 個 agent | matrix 測全部 |
| F2 | Vue SFC `<template>/<script>` 結構完整測試 | 投入完善 |

---

## Batch 6：MCP 延後項目（4 項）

決策：保持輕量入口，等有實際使用回饋再擴充。先補 C5（已列入 Batch 5）。

| ID | 任務 | 狀態 |
|---|---|---|
| A5 | MCP 進階參數暴露 | 延後 |
| A6 | MCP apply-fixes 支援 | 延後 |
| C1 | MCP 整合測試（apply-fixes/SARIF） | 延後 |
| S4 | suggest_fixes.py 硬編碼解除 | 延後 |

---

## 執行順序建議

```
Batch 1 (快速修正) → Batch 2 (文件) → Batch 3 (重構) → Batch 4 (功能) → Batch 5 (測試)
                                                                              ↓
                                                                    Batch 6 (MCP 延後)
```

每個 Batch 完成後 commit + push + 更新 `20260328_todo.md`。
