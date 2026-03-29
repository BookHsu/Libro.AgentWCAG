# 貢獻指南

感謝你為 Libro.AgentWCAG 做出貢獻。

這個 repository 維護的是一份可被 Codex、Claude、Gemini、Copilot 共用的 vendor-neutral WCAG skill contract。所有變更都應先維持合約穩定，再改善 adapter、工具鏈與周邊文件。

## 基本原則

- 保持 adapter 輕薄。`skills/libro-wcag/adapters/` 底下的檔案可以調整 prompt 表達方式，但不得改變合約欄位名稱、欄位順序、狀態詞彙或 JSON keys。
- 維持 vendor-neutral contract 為唯一權威來源。當合約變更時，請同步更新 `skills/libro-wcag/SKILL.md`、`skills/libro-wcag/references/core-spec.md`、schema 與測試。
- 自動修正必須安全。任何新的 `apply-fixes` 行為，都必須可證明安全、範圍明確，並具備回歸測試。
- 使用官方 W3C 引用。重大發現與文件範例應指向正式的 WCAG / Understanding URL。
- 版本資訊保持同步。`pyproject.toml` 與 `package.json` 中面向 release 的版本字串必須一致。

## 開發環境

需求：

- Python 3.12+
- `pyyaml`
- 只有在需要 scanner/runtime 或 packaging 流程時才需要 Node.js

常用指令：

```bash
python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-wcag
python scripts/libro.py doctor codex
```

## 變更類型

### 合約或 Schema 變更

當你要修改報告欄位、狀態詞彙、預設值或 schema 行為時：

1. 更新 `skills/libro-wcag/SKILL.md` 與相關 reference 中的合約內容。
2. 更新 `skills/libro-wcag/schemas/` 中的 JSON Schema。
3. 在 `skills/libro-wcag/scripts/tests/` 補上或調整回歸測試。
4. 若使用者可見輸出形狀有變化，更新 adapter examples。
5. 在 `CHANGELOG.md` 記錄這次變更。

### Adapter 變更

當你調整 adapter 文件或 prompt templates 時：

1. 保持各 adapter 的輸出合約語意一致。
2. 必要時同步更新該 adapter 的 `prompt-template.md`、`usage-example.md`、`failure-guide.md`、`e2e-example.md`。
3. 重新執行 `python scripts/validate_skill.py skills/libro-wcag`。

### Auto-Fix 變更

當你調整 `skills/libro-wcag/scripts/auto_fix.py` 或相關 rewrite helpers 時：

1. 只擴充可以安全自動重寫的模式。
2. 為成功重寫與受保護不重寫兩種情境都補上 fixture 或單元測試。
3. 確保 unified diff 仍然可讀、可審查。

## Pull Request 要求

- 保持 PR 聚焦，大小要能被清楚審查。
- 明確描述任何使用者可見的合約變更。
- 標出是否有相容性風險。
- 列出你實際執行的驗證指令。
- 若變更影響行為、合約、打包或 operator-facing 文件，請更新 `CHANGELOG.md`。

## 文件要求

- 優先更新既有權威來源，不要額外增加重複說明。
- 維運文件放在 `docs/release/`，測試文件放在 `docs/testing/`，範例放在 `docs/examples/`。
- 已被取代但仍有保存價值的內容，請移到 `docs/archive/`，不要直接刪掉有用歷史。

## Review 檢查清單

在送出 review 前，請確認：

- 已執行與此次變更相關的測試或驗證
- 合約、schema、adapters 與 examples 仍然一致
- 新檔案被放在正確的文件區段
- 沒有把不相關的產生物一起提交
