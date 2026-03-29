# 安全性政策

## 回報漏洞

若你懷疑發現安全漏洞，請不要直接開公開的 GitHub issue。

請透過 repository 的 security advisory 流程，或目前 release 流程文件中記載的維護者聯絡管道，私下回報安全問題。回報時請盡量包含：

- 受影響的版本或 commit
- 重現步驟或 proof of concept
- 影響評估
- 任何建議的緩解方式或 workaround

我們會先確認收到回報，完成驗證後再協調修補與揭露時程。

## 範圍

此 repository 中較敏感的安全區域包含：

- `mcp-server/` 的指令執行與 target handling
- `skills/libro-wcag/scripts/auto_fix.py` 與檔案重寫行為
- `scripts/` 底下的 install / uninstall / packaging scripts
- `.github/workflows/` 底下的 release 與 publish workflows
- Python 與 npm artifacts 的相依與供應鏈完整性

## 支援版本

安全修補優先適用於：

- 最新已發佈版本
- 尚未發佈修補時的目前預設分支

較舊版本可能只提供指引或 workaround，不保證提供完整 patch。

## 揭露原則

- 我們偏好在修補程式或緩解措施可用後，再進行協調揭露。
- 當修補準備完成後，我們可能透過 advisory、changelog notes 或 release notes 公布。
- 若問題涉及不安全的自動重寫，我們可能先暫時縮小或停用相關 auto-fix 路徑，再提供完整修補。

## Repository Hygiene

貢獻者應：

- 避免引入新的 shell invocation 風險或 path traversal 行為
- 將 auto-fix 限制在可證明安全的重寫模式
- 保留 release tooling 中的 provenance 與 version-sync 檢查
- 在 `CHANGELOG.md` 中記錄安全相關行為變更
