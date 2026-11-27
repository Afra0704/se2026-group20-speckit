# 012 驗證紀錄

2026-11-27（台北時間），Codex 在本機分支 codex/012-tab-classroom-membership 上核對最新 master 與基底皆為 e9a29c7。PR #22 仍開啟且為草稿，012 新版圖表複核見 diagram-review.md。Python 測試 fixtures 使用空白暫存資料庫。

預期基線測試全數通過。實際 Node 72 項、相關 Python 29 項通過，退出碼均為 0。此紀錄對應 012 實作前基線。

```powershell
node --test tests/*.test.cjs
python -m pytest tests/contract/test_classroom_memberships.py tests/contract/test_classroom_recovery_009.py tests/contract/test_classroom_presence.py tests/contract/test_classroom_results.py tests/integration/test_classroom_join_races.py tests/integration/test_classroom_submission_races_009.py tests/integration/test_classroom_history_009.py tests/integration/test_classroom_code_schema.py -q -p no:cacheprovider
```

## T005 附加資料表

2026-11-27（台北時間），Codex 在 `e9a29c7` 基底的本機 012 工作樹驗證。預期 008／009 測試庫既有資料、外鍵與測試分頁資格在重跑初始化後保留；實際均符合。課堂 schema 升級與故障回滾 14 項通過，重新執行上方 Python 基線範圍 30 項全數通過，Node 72 項全數通過，退出碼均為 0。

```powershell
python -m pytest tests/integration/test_classroom_code_schema.py tests/integration/test_classroom_schema_failures.py -q -p no:cacheprovider
```

本輪完成 T005，只有新增表與啟動初始化。學生分頁端點尚未接入。PR #22 核對時仍為開啟的 Draft，依 T002 計畫在接入 #16 加入介面前重新核對。

## T006／T007 實作前測試

2026-11-27（台北時間），Codex 在 012 本機工作樹以暫存資料庫驗證新增的六個分頁契約與整合案例。四個測試檔合計 14 項既有測試通過、6 項新增測試如預期因缺少分頁實作失敗，退出碼 1。

- 五個新案例由加入回應缺少 resume_id 擋下。接線後將繼續核對跨堂、同堂同組去重、無效組號保留原資格、失聯後換組令舊世代失效、跨瀏覽器與關課授權，以及送答 CSRF 與原順位保留。
- 並行異組加入目前兩筆都回 201，預期是一筆 201、一筆 409 CLASSROOM_GROUP_IN_USE。此測試在收到首個心跳前檢查。
- T006／T007 勾選表示已撰寫並驗證失敗路徑。功能接線後須重跑，6 項均通過才算達成。

## T008–T017 實作與自動驗證

2026-11-27（台北時間），Codex 於合併 PR #22 後的 `80510a6` 基底上，以本機 012 工作樹與測試暫存資料庫驗證。最後一次執行七個課堂契約、整合及 schema 檔案，共 39 項通過，含原本 6 項預期失敗案例、過期索引、撤回與文件資格更新。原送答測試使用無效的 idempotency key，已依既有 003 介面改成 UUID，確認關閉前 201、關閉後拒絕重送，教師仍見原組順位。

Node 80 項通過，含複製文件另取資格、回覆遺失以同一請求重試、返回快取驗證、關課清理、撤回前確認及未決送答作用域。

```powershell
node --test tests/*.test.cjs
python -m pytest tests/contract/test_classroom_memberships.py tests/contract/test_classroom_results.py tests/contract/test_classroom_recovery_009.py tests/contract/test_classroom_presence.py tests/integration/test_classroom_join_races.py tests/integration/test_classroom_submission_races_009.py tests/integration/test_classroom_code_schema.py -q
```

完整 Python 套件的執行尚無結果。T018 真人驗收待完成。本機目前未設置有效 Google Web client 憑證檔案，未用真實教師登入及兩組學生演練，也未取得真實瀏覽器的複製分頁判定或在線延遲數據。
