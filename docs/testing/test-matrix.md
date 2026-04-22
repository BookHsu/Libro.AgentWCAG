# Testing Matrix

此文件定義 `Libro.AgentWCAG` 目前公開維護的主要測試矩陣，特別聚焦在 CLI、報告輸出、安裝流程與文件一致性。

## Test Matrix

| Test Type | Applies | Automation Target | Repo Areas | Current Status | Coverage Mode | Coverage Asset |
| --- | --- | --- | --- | --- | --- | --- |
| Unit Test | Yes | Yes | workflow、remediation、helpers | Implemented | Automated | `test_workflow.py`, `test_remediation_library.py`, `test_rewrite_helpers.py` |
| Component Test | Yes | Yes | `run_accessibility_audit.py`, `scripts/libro.py`, installer scripts | Implemented | Automated | `test_runner.py`, `test_cli_flows.py`, `test_repo_scripts.py` |
| Integration Test | Yes | Yes | install -> doctor -> audit/report | Implemented | Automated | `test_install_agent.py`, `test_repo_scripts.py`, `test_repo_invocation.py` |
| System Test | Yes | Yes | repo as installable skill product | Implemented | Automated + Scripted Manual | `test_matrix_completion.py`, `docs/testing/testing-playbook.md` |
| End-to-End Test | Yes | Yes | install -> invoke -> output artifacts | Implemented | Automated + Scripted Manual | `test_cli_flows.py`, `test_matrix_completion.py`, `docs/testing/testing-playbook.md` |
| Regression Test | Yes | Yes | CLI、contract、release、reporting | Implemented | Automated | full `test_*.py` suite |
| Static Contract Test | Yes | Yes | repo structure、schema、docs、adapter contract | Implemented | Automated | `test_repo_contracts.py`, `validate_skill.py` |
| Documentation Consistency | Yes | No | README、docs、public commands | Implemented | Scripted Manual | `test_release_docs.py`, `docs/testing/testing-playbook.md` |
| Compatibility Test | Yes | Yes | agents、wrappers、cross-platform entrypoints | Implemented | Automated + Scripted Manual | `test_install_agent.py`, `test_repo_scripts.py` |
| Security / Boundary Test | Yes | Yes | invalid target、overwrite、path handling | Implemented | Automated | `test_runner.py`, `test_cli_flows.py`, install overwrite tests |
| Performance / Scalability | Yes | No | normalization、batch scan、artifact emission | Implemented | Scripted Manual | `test_matrix_completion.py`, `docs/testing/testing-playbook.md` |

## Repo Mapping

### CLI 與報告輸出

- `skills/libro-wcag/scripts/run_accessibility_audit.py`
- `scripts/libro.py`
- `skills/libro-wcag/scripts/aggregate_report.py`
- `skills/libro-wcag/scripts/report_renderers.py`

覆蓋重點：

- 單檔 HTML / URL 稽核
- `summary-only` JSON
- SARIF 輸出
- `--print-examples`
- `--artifacts minimal`
- `libro report --no-color`

### 安裝與驗證工具

- `scripts/install-agent.py`
- `scripts/doctor-agent.py`
- `scripts/uninstall-agent.py`
- `scripts/libro.ps1`
- `scripts/libro.sh`
- `bin/libro.js`

覆蓋重點：

- install / doctor / remove
- wrapper 是否指向正確 Python entrypoint
- scanner preflight 狀態
- workspace 安裝路徑

### Contract 與報告結構

- `skills/libro-wcag/SKILL.md`
- `skills/libro-wcag/references/core-spec.md`
- `skills/libro-wcag/schemas/wcag-report-1.0.0.schema.json`

覆蓋重點：

- 頂層 JSON key 穩定
- Markdown 固定欄序
- schema version 對齊
- adapter / repo contract 不漂移

## Already Implemented

- Automated CLI, report, installer, and contract coverage
- Scripted Manual coverage for docs UX, broader smoke, and exploratory scenarios
- Static validation through `validate_skill.py`

## Still Worth Adding

- More real-scanner CI assertions once scanner environments are stable
- More doc contract coverage for bilingual companion files
- Wider batch-scan and aggregate-report regression fixtures

## 最小驗證命令

```powershell
python -m unittest skills.libro-wcag.scripts.tests.test_cli_flows
python -m unittest skills.libro-wcag.scripts.tests.test_repo_scripts
python scripts/validate_skill.py skills/libro-wcag
```

## 完整驗證命令

```powershell
python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-wcag
```

## 文件與公開介面檢查

變更公開 CLI 或 README 後，至少確認：

- README 範例命令存在且可執行
- wrappers 支援 README 中提到的公開命令
- `audit`、`scan`、`report` 三條路徑都有對應 smoke
- 中文主檔與英文副本同步
