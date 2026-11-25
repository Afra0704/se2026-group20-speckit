# PR #6 合流與修補紀錄

日期：2026-11-25。執行者：Codex，依使用者明確授權修正、上傳及合併。起點為 004 `ce883a4` 與 001 `418365f`，在獨立工作樹整合，保留兩位作者及既有 commit 歷史。這是開發進度合流，不是完整專題的最終驗收。

## 審查問題與修正

1. 教師狀態輪詢失敗會停用按鈕，但相同 state_version 不重抓活動清單；第一次清單失敗也因已快取版本而永不重試。以 historyNeedsRefresh 保留重試需求，成功渲染才清除；historyRequest＋selection 拒絕晚到的舊清單。
2. 合併 db.py／conftest 的兩個文字衝突。保留 001 autocommit=True＋SQL COMMIT／ROLLBACK，加入 004 新 DB 模式檢查、course／classroom schema 與兩邊 fixtures。004 狀態讀取改 SQL ROLLBACK，以免沿用 app context 時留下交易；init-db 在兩模式均可重跑，來源 DB 不清空。
3. 自動合併產生兩份 get_activity_reference，移除舊重複定義，保留同時支援 legacy／classroom 的版本。
4. 001 顯示名稱與 004 課堂重複使用 D12。保留課堂 D12–D16，顯示名稱改 D17，保留原確認狀態與歷史來源。004 任務路徑改為實際 classroom_routes／classroom_membership／classroom.js／classroom.html，未改功能範圍。

## Analyze（唯讀檢核後修補）

以各 feature 的 spec／plan／tasks、憲章及契約為依據，使用 SPECIFY_FEATURE_DIRECTORY 執行各自 prerequisites。兩份必要文件齊備，001 checklist 16／16、004 checklist 5／5，未改核取標記；沒有 extensions.yml，沒有 hooks。

| ID | 類別／影響 | 依據與結論 |
| --- | --- | --- |
| A1 | HIGH，一致性 | D12 一號兩義，已拆為顯示名稱 D17；不宣稱該擴充獲新增雙組確認。 |
| A2 | HIGH，實作一致性 | SQLite autocommit 與 rollback 呼叫不一致，已統一顯式 SQL，補同 context 可繼續寫入測試。 |
| A3 | MEDIUM，可用性 | 斷線或清單失敗後無重試，修正並補失敗／復線／反序回應測試。 |
| A4 | MEDIUM，追溯 | 004 任務檔路徑與實作不同，已對齊，保留原需求與任務編號。 |

FR-001 課程講義與版本、FR-002 加入／組別、FR-003 同步、FR-004 單 LIVE 與舊提交、FR-005 關課、FR-006 結果及原瀏覽器、FR-007 空白 DB 均有既有任務／測試對應。001 的 FR-001–FR-015 仍由既有測試及待辦追蹤；未把待驗收項目誤列為已完成。此次沒有新增需另走 specify 的功能。

## Converge

outcome=tasks_appended。僅在 tasks 追加：004 Phase 7 的 T027–T031，以及 001 Phase 11 的 T070。然後回到 implement 完成 004 T027–T030；T031／001 T070 保留正式 003、真人及真實來源的交付缺口，原人工任務不代勾。

這個開發合併仍不具有「全功能 converged」或「最終交付完成」聲明。新結算業務不在本次修補範圍，不能為了清空待辦而注入假結果到正式啟動設定。

## 自動驗證

- 修補前在獨立 VM 重現兩種斷線恢復問題；修補後 classroom-recovery.test.cjs 三案例通過：狀態讀取失敗恢復、第一次清單失敗重試、舊清單回應被忽略。
- test_classroom_notes_integration.py 使用真實 course_service／001 course_catalogs／SQLite／活動與加入路由，來源 Sheets 與結果供應使用受控替代。驗證課程內匯入、跨課程拒絕、同堂兩活動且學生只加入一次、結束後固定原活動的回填、同 context 交易釋放及 init-db 保留 catalog。
- 初次整合全套：209 passed、98 subtests、1 failed；唯一失敗是舊測試假設清除 provider override 代表模組缺少。現在 001 已存在，清除 override 應回到真實 provider，找不到該測試 import 回 404；修正測試驗證 404 fallback，另用不可呼叫 provider 明確驗證 503，不放寬跨課程拒絕。
- 修正 fallback 測試後完整執行 `.venv/Scripts/python.exe -m pytest tests -q --maxfail=2`：**210 passed、98 subtests passed，80.32 秒，退出碼 0**。四項 JavaScript 測試（classroom-sync、classroom-recovery、activity-sync、notes-ui）均通過。PlantUML CLI 重渲染 004 三類圖，退出碼 0；001 圖未改動，沿用既有產物。git diff --check 通過，extensions.yml 前後皆不存在。

## 仍待完成

正式 003 受理／排名／不可變結算及真實 Sheets 副本回填、教師加兩組學生的完整人工驗收、新圖意的同學審查及最終交付證據仍待完成。沒有操作使用者正式 DB 或真實 Sheets，沒有修改 Google 登入流程。

## 合流後啟動

原 002／001 DB 保留；004 請用新的 `instance/classroom-004.sqlite3`。CMD 範例：

```bat
cd /d D:\os_final
set "GUIDED_NOTES_CLASSROOM_MODE=1"
set "GUIDED_NOTES_DATABASE=D:\os_final\instance\classroom-004.sqlite3"
set "GUIDED_NOTES_DEMO_CATALOG=0"
```

沿用原本 SECRET_KEY、NOTES_GOOGLE_CLIENT_SECRETS、NOTES_GOOGLE_TOKEN 與正確 NOTES_GOOGLE_TEACHER_ID。新 DB 只需初始化一次教師（目前 004 密碼至少 4 字元），既有教師不重建。`init-db` 冪等保留本模式資料；舊模式 DB 不能直接當 004 DB 開啟。

```bat
.venv\Scripts\python.exe -m flask --app guided_notes:create_app init-db
.venv\Scripts\python.exe -m flask --app guided_notes:create_app init-teacher teacher
.venv\Scripts\python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

教師登入後建課程，選課程再按「在目前課程匯入講義」，回教師頁重新選課程取得講義版本，建立課堂與活動。新 DB 的教師 ID 以 init-teacher 輸出為準，不假設舊 DB 的 ID 一定相同。正式 003 尚未接入時會維持 QUIZ_UNAVAILABLE／RESULT_NOT_READY，屬已記錄限制。
