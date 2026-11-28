# 013 驗證紀錄

2026-11-28（台北時間），Codex 在 Issue #18 本機工作樹驗證。基底 a8c7b8f，包含已合併 #17。使用 Python 3.13 既有虛擬環境、Node 及 pytest fixtures 的暫存資料庫。

| 驗證 | 預期 | 實際 |
|---|---|---|
| 變更前 Node 送答、分頁與在線範圍 | 原行為通過 | 31 項通過 |
| 變更前 Python 送答契約及競態 | 原行為通過 | 5 項通過 |
| US1／US2／US3 完整 Node | 逐欄驗空、本題狀態、原樣重試、A1 衝突、晚回及不合契約的成功回應通過 | 95 項通過 |
| Python 送答契約及競態 | 拒絕不受理、保留原字串 | 6 項通過 |
| 另跑新版舊操作重送整合案例 | 201 重送不增受理，舊操作不覆蓋目前有效答案 | 1 項通過 |
| 完整 Python | 送答、課堂、教師及回填回歸 | 621 項、98 子測試通過，1 項跳過，退出碼 0 |

前端新增測試在實作前捕捉 A1 無本題提示，以及缺少逐欄驗空行為。實作後已重驗。

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$suite = Get-ChildItem tests/*.test.cjs | ForEach-Object FullName
node --test $suite
python -m pytest tests/contract/test_quiz_submission.py tests/integration/test_classroom_submission_races_009.py -q -p no:cacheprovider
python -m pytest tests -q -p no:cacheprovider --tb=short
```

真人驗收待完成。本工作階段沒有配置 Google Web client 憑證，未以一位教師和兩組學生操作。鍵盤、窄視窗及輔助技術仍須按驗收指南真人核對。
