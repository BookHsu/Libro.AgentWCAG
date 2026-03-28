# `apply-fixes` 適用範圍（M16）

本文件定義生產化 `apply-fixes` 模式在下列程式中的適用邊界：

- `skills/libro-wcag/scripts/run_accessibility_audit.py`
- `skills/libro-wcag/scripts/auto_fix.py`

## 行為稽核（2026-03-12）

- `execution_mode=apply-fixes` 只有在 `target` 解析為既有本機檔案路徑時，才會嘗試核心重寫。
- 支援的本機檔案類型僅限：`.html`、`.htm`、`.xhtml`、`.jsx`、`.tsx`、`.vue`。
- 不支援的本機檔案類型與非本機目標，一律跳過核心重寫，並記錄到 `run_meta.notes`。
- 若本次執行未套用任何重寫，系統會刪除陳舊的 `wcag-fixes.diff` 與 `wcag-fixed-report.snapshot.json` 工件，以維持重複執行的穩定性。

## 適用範圍矩陣

| 規則類別 | 規則 ID | 檔案類型 | 安全等級 | 核心行為 |
| --- | --- | --- | --- | --- |
| 語言語意 | `html-has-lang`、`html-lang-valid`、`html-xml-lang-mismatch`、`valid-lang` | `.html`、`.htm`、`.xhtml`、`.tsx`（Next.js layout）、`.jsx`、`.vue` | 低風險、可確定 | 由核心工作流程自動修復 |
| 替代文字 | `image-alt`、`input-image-alt`、`area-alt` | `.html`、`.htm`、`.xhtml`、`.jsx`、`.tsx`、`.vue` | 低風險、可確定 | 由核心工作流程自動修復 |
| 無障礙名稱 | `button-name`、`link-name`、`label`、`select-name`、`aria-toggle-field-name`、`aria-tooltip-name`、`aria-progressbar-name`、`aria-meter-name` | `.html`、`.htm`、`.xhtml`、`.jsx`、`.tsx`、`.vue` | 低風險、可確定 | 由核心工作流程自動修復 |
| ARIA 有效性 | `aria-required-attr`、`aria-valid-attr-value` | `.html`、`.htm`、`.xhtml`、`.jsx`、`.tsx`、`.vue` | 低風險、可確定 | 由核心工作流程自動修復 |
| 文件／結構 | `document-title`、`list`、`listitem`、`table-fake-caption`、`td-has-header`、`th-has-data-cells` | `.html`、`.htm`、`.xhtml`、`.jsx`、`.tsx`、`.vue` | 低風險、可確定 | 由核心工作流程自動修復 |
| 時間／視口 | `meta-refresh`、`meta-viewport` | `.html`、`.htm`、`.xhtml` | 低風險、可確定 | 由核心工作流程自動修復 |

## 明確不自動修復的範圍

下列類別仍位於核心 `apply-fixes` 範圍之外，預期以 `suggest-only` 或輔助／手動修復方式處理：

- 僅提供輔助的規則類別：結構或互動重構，例如 `heading-order`、`region`、`skip-link`、`tabindex`、`presentation-role-conflict`、`nested-interactive`、`duplicate-id-aria`。
- 需人工審核的類別：WCAG 2.2 手動檢查（`wcag22-manual-*`）以及掃描器／工具失敗時的 fallback findings。
- 不支援的目標類別：非本機目標、不在支援副檔名清單內的本機檔案，以及需要專案特定意圖才能安全處理的高風險轉換。

## 合約層級的預期行為

- 只有在支援的本機目標真的被重寫時，`run_meta.files_modified=true` 與 `run_meta.modification_owner=core-workflow` 才應成立。
- `run_meta.diff_artifacts[]` 應只包含本次實際套用變更所產生的 diff 工件。
- 未自動修復的 finding 與 fix，必須保留標準化的降級中繼資料，例如 `downgrade_reason`、`fix_blockers` 與手動審核旗標。
