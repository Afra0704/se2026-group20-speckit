# Issue #19 驗收指南

三故事已在本機接線，自動結果見 [validation.md](validation.md)。下列人工案例仍待實際執行，不因自動測試通過代勾。

## 前提與啟動

1. 本機已整合 #16 PR22 及 #20 提交 4199675；檢查目前版本與 [契約](contracts/dependency-boundaries.md)，既有未完成人工驗收仍獨立保留。
2. 停止舊服務；沿用現有 007／008 的私人環境設定、Web OAuth client 與持久 key。先備份原 DB／key；不要清庫、重建 key 或把憑證放 repo。
3. 自動測試一律用 temporary DB／受控 gateway。人工測試使用獨立空白測試 DB，教師自行登入建資料；不將既有正式資料當可刪測試資料。
4. 使用來源範本副本及另一份題數／欄列配置不同的副本，禁止直接對正式講義做試驗。

PowerShell（工作目錄固定）：

```powershell
Set-Location D:/os_final
.venv/Scripts/python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

開啟教師頁 `http://127.0.0.1:5000/teacher`。至少準備教師 A、教師 B、兩堂各有第 1 組／第 42 組；教師 A 在兩堂建立同名活動，重用講義並使用不同版本／答案。

## 自動驗證

實作後執行現有相關回歸及新增 context／classroom 測試。現有測試命令：

```powershell
Set-Location D:/os_final
.venv/Scripts/python.exe -m pytest tests/integration/test_export_previews.py tests/integration/test_export_routes.py tests/integration/test_writeback_restart.py tests/integration/test_sheets_reconnect_ui.py tests/unit/test_writeback_recovery.py tests/contract/test_result_snapshot.py -q
node --test tests/classroom-preview.test.cjs tests/classroom-recovery.test.cjs tests/classroom-sync.test.cjs tests/quiz-results.test.cjs
.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -q
```

本功能新增測試可直接執行：

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_export_context.py tests/contract/test_export_display_context.py tests/integration/test_result_writeback_entry.py tests/integration/test_export_context_history.py -q
node --test tests/result-writeback-entry.test.cjs
```

完整 Node 回歸用 PowerShell 取得 `Get-ChildItem D:/os_final/tests -Filter '*.test.cjs' -File` 後將 FullName 陣列傳給 `node --test`，避免依賴 shell wildcard。

## 人工／受控驗收矩陣

| 編號 | 操作 | 預期 |
| --- | --- | --- |
| Q01 | 目前結果與歷史結果各按預覽 | 一次操作進指定預覽，零手輸 ID；確認前無寫入 |
| Q02 | 同名活動、不同版本；預覽刷新、返回原結果後再刷新；亦驗關課歷史、無效／跨堂 activity_id | 返回 URL 帶原 activity_id，原結果保持選取，答案／版本不變；無效／跨堂拒絕且不改選最新活動，不取最近活動 |
| Q03 | 兩堂各有第 1 組，答案不同 | 各用原堂勝組，標籤皆正確，未將 ID 當組號 |
| Q04 | 原課堂結束、講義清單移除後重開歷史 | 原教師可預覽；原來源／版本仍正確 |
| Q05 | 教師 B／學生直接開 preview、report、confirm、recovery | 不越權、不漏 context 或答案、不讀寫來源 |
| Q06 | 未結束、未結算、全無勝組、部分無勝組 | 各有不同提示；全無勝組停用 UI 確認；部分略過 |
| Q07 | 受控注入缺失／跨堂勝組 ID | 新操作在來源呼叫前拒絕；舊報告保留且顯錯誤，不能續寫 |
| Q08 | 授權失效後成功／取消／失敗 | 原活動／預覽／操作脈絡保留，不自動重送 |
| Q09 | 來源原值不同、未勾覆寫／勾選後確認 | 未同意不覆寫；同意後依原目標寫入並回讀 |
| Q10 | 受控部分成功、未知、斷線／重啟後恢復 | 先回讀、原勝組／版本不變，已完成題無重送 |
| Q11 | 恢復含原已同意覆寫與新來源衝突 | 保留舊同意並標示新衝突，不無聲覆寫 |
| Q12 | 已知 UTC／offset／naive UTC、跨午夜、缺值、壞值 | 使用 #20 同一格式與提示；無假結算時間或整頁錯誤 |
| Q13 | 兩份真 Sheets 副本逐格回填／回讀 | 勝組答案位置正確，無勝組略過，其他欄位／合併／格式不變 |

Q07、Q10 的故障使用測試 fixture／gateway，不能手改正式 DB。自動替代來源結果不代替 Q13 真實來源證據。真人完整案例包含教師及至少兩組學生，確認結果後才回填測試副本。

## 證據格式

每案記錄執行者、台北日期時間、Git SHA、情境、預期、實際、通過／失敗／未執行及受控或真實來源；截圖及報告需排除憑證與真實學生資料。比較前後 activity/import/result_version、winner、rank、原答案，以及來源非目標格與格式；重試與恢復另外比對來源寫入次數。失敗修正後記錄重驗，不代勾人工案例。

## 2026-11-27 統一版本入口

使用者要求#19／#20統一版本；目前請以 `D:/os_final` 的 `codex/integrate-issues-19-20` 為準，最新master基底80510a6，兩項功能均已包含。前文分段worktree／尚未接線說明為歷史，勿再用舊011 worktree驗收此整合版。統一啟動及實際回歸見[整合紀錄](../../docs/issues-19-20-integration.md)，原人工／POSIX／真Sheets狀態不因建立整合分支而代勾。
