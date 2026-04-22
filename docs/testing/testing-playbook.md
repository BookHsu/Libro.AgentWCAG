# Testing Playbook

此文件整理公開專案最常用的測試、smoke、文件一致性驗證與人工檢查路徑。

## 最小回歸集合

修改 CLI、報告輸出、README 或 wrappers 後，至少執行：

```powershell
python -m unittest skills.libro-wcag.scripts.tests.test_cli_flows
python -m unittest skills.libro-wcag.scripts.tests.test_repo_scripts
python scripts/validate_skill.py skills/libro-wcag
```

若只改單一區塊，可先跑對應最小集合：

```powershell
python -m unittest skills.libro-wcag.scripts.tests.test_cli_flows.CliFlowTests.test_run_accessibility_audit_summary_only_prints_compact_json
python -m unittest skills.libro-wcag.scripts.tests.test_repo_scripts.RepoScriptTests.test_libro_audit_preflight_only_returns_json
```

## CLI Smoke 路徑

### 1. Preflight

確認 Python CLI 與 scanner toolchain 狀態可被讀取：

```powershell
python .\scripts\libro.py audit --preflight-only
```

### 2. 單檔 HTML 稽核

```powershell
python .\scripts\libro.py audit .\docs\testing\realistic-sample\mixed-findings.html --skip-axe --skip-lighthouse --summary-only --output-dir .\out\smoke
```

預期：

- stdout 為 compact JSON
- `wcag-report.json` 與 `wcag-report.md` 會寫入 output dir
- `run_meta.product` 與 `report_schema` 資訊存在

### 3. Artifact 縮減模式

```powershell
python .\skills\libro-wcag\scripts\run_accessibility_audit.py --target .\docs\testing\realistic-sample\mixed-findings.html --skip-axe --skip-lighthouse --summary-only --artifacts minimal --output-dir .\out\minimal
```

預期：

- 核心報告仍存在
- `debt-trend.json`、`scanner-stability.json` 等 sidecar 不應被寫出

### 4. 彙總報告

```powershell
python .\scripts\libro.py report .\out\smoke\wcag-report.json --format terminal --no-color
python .\scripts\libro.py report .\out\smoke\wcag-report.json --format html --output .\out\wcag-summary.html
```

預期：

- `--no-color` 不應輸出 ANSI escape
- terminal 模式可在 Windows CP950 終端顯示
- HTML 模式可成功輸出彙總報告

## 使用體驗檢查

CLI / README 改動後，人工確認：

- `python .\scripts\libro.py audit --print-examples`
- `python .\scripts\libro.py scan --print-examples`
- `python .\scripts\libro.py report --print-examples`
- `python .\skills\libro-wcag\scripts\run_accessibility_audit.py --print-examples`

檢查項目：

- 範例命令與實際支援旗標一致
- README / docs 與 CLI help 沒有互相矛盾
- wrapper (`libro.ps1`, `libro.sh`, `bin/libro.js`) 可覆蓋公開命令

## 公開文件一致性

修改正式 human-facing docs 後，確認：

- `README.md` 與 `README.en.md` 結構一致
- `docs/README.md` 與 `docs/README.en.md` 可作為文件入口
- `docs/testing/testing-playbook.md` 與 `docs/testing/testing-playbook.en.md` 對齊
- `docs/testing/test-matrix.md` 與 `docs/testing/test-matrix.en.md` 對齊
- `CHANGELOG.md` 已記錄外部可見行為變更

## 較完整驗證

需要較高信心時，執行完整測試：

```powershell
python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-wcag
```

若變更含 release / packaging / docs 相關內容，另外執行：

```powershell
python -m unittest skills.libro-wcag.scripts.tests.test_release_docs
python -m unittest skills.libro-wcag.scripts.tests.test_release_packaging
python -m unittest skills.libro-wcag.scripts.tests.test_release_workflow
```

## 人工檢查場景

### Acceptance / UAT

- 安裝 skill 到目標 agent
- 實際跑一次 `audit-only`、`suggest-only`、`apply-fixes`
- 確認報告欄位、狀態、引用與修改說明可理解

### Exploratory

- 嘗試本機 HTML、URL、錯誤 scheme、缺 scanner 的情況
- 確認錯誤訊息可指向下一步，而非只丟 traceback

### Documentation

- 從 README 開始，不依賴口頭說明完成一次 install -> audit -> report
- 確認新使用者能看懂單檔稽核、批次掃描、報告彙總三條路徑

## Legacy Matrix Labels

下列名稱保留在正式文件中，讓既有 contract / repo 測試能持續對應：

- Acceptance Test / UAT
- End-to-End Test
- Decision Table
- Performance Test
- Concurrency Test
- Beta Test
