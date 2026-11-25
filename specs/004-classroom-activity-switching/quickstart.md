# Phase 1 驗證指南

2026-11-25 PR #6 合流更新：001 真實課程與講義介面已接上，正常匯入使用 GUIDED_NOTES_DEMO_CATALOG=0；下方 DEMO_CATALOG=1 仍僅供示範。210 項 Python 測試、98 子測試及四項 JavaScript 測試通過，正式 003／真實 Google 副本／兩組真人驗收仍待完成。合流啟動與分析／收斂紀錄見 [pr6-integration-validation](../../docs/pr6-integration-validation.md)。

在專案根目錄開新的 PowerShell 視窗，使用獨立的空白資料庫。本機示範提供一份兩版本的清單，兩份講義的驗收由契約測試替代資料提供。

```powershell
uv sync --python 3.13
$env:GUIDED_NOTES_CLASSROOM_MODE = '1'
$env:GUIDED_NOTES_DATABASE = Join-Path (Get-Location) 'instance/classroom-004.sqlite3'
$env:GUIDED_NOTES_DEMO_CATALOG = '1'
$env:GUIDED_NOTES_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
uv run flask --app guided_notes:create_app init-teacher teacher
uv run flask --app guided_notes:create_app run --host 127.0.0.1 --port 5001
```

本機教師密碼至少 4 個字元。若該課堂資料庫已初始化教師，跳過 `init-teacher` 並沿用原密碼。開啟 `http://127.0.0.1:5001/teacher` 登入，建立課程與課堂。新課堂碼為兩個大寫英文字母加三個數字，例如 `AB123`。既有課堂碼仍可使用。兩組學生分別使用獨立的瀏覽器工作階段到 `http://127.0.0.1:5001/` 加入一次。教師用版本 1、2 建立並依序啟動活動。示範模式可提交測試答案，正式結算、歷史結果與 Sheets 回填須接入 001／003。可用替代結算測試驗證歷史欄位。

| 驗收 | 操作與預期 |
| --- | --- |
| FR-001／002 | 教師在一門課程選兩份講義並開上午和下午課堂。同講義可重用，兩個加入碼和同名組別獨立。無關教師直接請求遭拒。 |
| FR-001／004 | 同一位教師嘗試用 B 課程的講義版本在 A 課程建立活動，須拒絕且無活動紀錄。使用 A 的版本才可建立。走 001 匯入時，成功的講義只出現在原課程，竄改課程或使用他人的預覽確認均遭拒。 |
| FR-003 | 兩組各加入一次，走完兩個不同或同名活動。重整或重連時仍回到本堂、原組和當前活動。故意延後前一活動狀態回應，畫面不倒退。 |
| FR-004／005 | 以兩條 SQLite 連線同時啟動不同活動，最多一個成功。確認關課與受理競爭時，只有關閉前已提交成功的答案計入，其他加入／提交遭拒。 |
| FR-006 | 關課後以原瀏覽器選看兩場已結算結果，跨瀏覽器或跨堂遭拒。另直接請求跨堂、同堂未結算及同堂已結算的活動，預期分別為 403、只有結算狀態、只有 D06 允許欄位。教師取得指定活動快照，未結束與未結算錯誤分開。 |
| FR-007 | 004 以新空白資料庫初始化兩次，關課後歷史保留。用舊 002 資料庫啟動 004 應拒絕且原檔不變，改用原 002 模式可啟動並建立活動及加入。來源 Sheets 保持原狀。 |

待 001／003 合流，以真實講義完成同堂切換與指定活動回填。組員的教師與兩組學生實際操作仍待記錄。

## 本機自動驗證紀錄

2026-11-25，Codex 在本機課堂改版工作樹執行。使用暫存 SQLite 和課程講義、受理、結果的替代提供者。

| 指令 | 實際結果 |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q` | 26 項通過，含 002 回歸、課堂權限與切換、結果欄位、短碼撞碼重試、4 字元教師登入、登入限流及兩個課堂頁載入共用樣式。 |
| `node tests/classroom-sync.test.cjs` | 較晚抵達的舊課堂狀態未覆蓋新活動。 |
| `node tests/activity-sync.test.cjs` | 既有 002 階段反序回應驗證通過。 |

真實 001／003 接線及 Google Sheets 讀寫尚未執行。

### 人工驗收，2026-11-25

使用者回報於本機 `codex/004-classroom-activity-switching` 的課堂示範環境驗收。教師已登入，學生以課堂碼加入，教師可開啟搶答，學生頁可填寫答案，結束後顯示「結算中」，符合尚未接上正式 003 的預期。本次未提供提交受理訊息、兩組連續切換、重連、原瀏覽器恢復或結算公布的人工結果，這些情境仍待補驗。
