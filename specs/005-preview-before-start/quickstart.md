# 005 驗證指南（實作後執行）

實作已提供，以下人工驗收仍待組員執行；自動驗證結果見 [validation.md](validation.md)，不代表真人驗收已通過。

## 前提及啟動

Python 3.13 `.venv`、Node，使用專用空白 classroom 開發 DB。沿用 [合流啟動設定](../../docs/pr6-integration-validation.md#合流後啟動) 及本機 SECRET_KEY／Google profile，不貼憑證。本次無新 Google 授權。使用者允許丟棄舊開發資料，不做遷移；本文件本身不執行刪除。

在設定完成的 CMD：

```bat
cd /d D:\os_final
set "GUIDED_NOTES_CLASSROOM_MODE=1"
set "GUIDED_NOTES_DATABASE=D:\os_final\instance\classroom-005.sqlite3"
set "GUIDED_NOTES_DEMO_CATALOG=0"
.venv\Scripts\python.exe -m flask --app guided_notes:create_app init-db
.venv\Scripts\python.exe -m flask --app guided_notes:create_app init-teacher teacher
.venv\Scripts\python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

首次使用時確認 classroom-005.sqlite3 為本次專用且尚無需保留的資料；若已存在即沿用，不靠重跑指令清空。init-teacher 僅新 DB 首次執行，之後略過。依輸出教師 ID 重新綁定本機 Google profile、建立課程並重新匯入講義，OAuth 憑證及來源 Sheets 不刪。若選擇刪除舊 DB，先停止對應服務並核對精確檔案路徑，不刪整個 instance。若舊伺服器佔用 5000，先在其 CMD 按 Ctrl+C。

## 教師及兩組人工驗收

Chrome 一般視窗為老師、Edge 為甲組、Chrome 無痕為乙組；兩組加入同一課堂一次。

1. 建立單題活動後，兩組 5 秒內看到正確名稱、題號及停用作答欄，提示尚未開放。
2. 準備中不能再建；老師結束準備後可建題組活動，核對主題號、小題標號及全部欄位。
3. 開啟搶答後兩組 5 秒內可輸入，不需重加；此時仍不能建立下一活動。
4. 結束後建立下一活動，自動換成新預覽，舊活動仍在歷史；刷新、短暫斷線及復線後狀態正確。
5. 關課後無未結束活動，學生不能加入或提交。
6. 重新啟動／重跑 init-db 後，本次建立的課程、活動與歷史仍保留，單活動限制有效；不驗收舊多準備活動的遷移。

記錄姓名、日期、commit、預期、實際及截圖。正式 003 尚未接入時，只驗收預覽／階段，不把 QUIZ_UNAVAILABLE 或待結算寫成成功排名。

## 自動驗證（待新增測試後）

另開測試 CMD，避免手動模式影響 fixture：

```bat
cd /d D:\os_final
set "GUIDED_NOTES_CLASSROOM_MODE="
set "GUIDED_NOTES_DEMO_CATALOG="
.venv\Scripts\python.exe -m pytest tests -q
node --test tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs
```

classroom-preview 測試已新增，涵蓋雙獨立連線建立、提前提交、回滾、權限、名稱安全顯示、準備中結束、目前指標一致性及晚到狀態。使用臨時空白 DB，不寫真實 Sheets。
