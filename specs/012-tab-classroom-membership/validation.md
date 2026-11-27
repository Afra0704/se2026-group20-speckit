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


## 2026-11-28 最新master整合審查

於隔離分支codex/review-24-integrated將PR24的07a9f15合入master 2c43854，保留已合併#19／#20。兩功能012圖檔衝突以本功能改名012-tab-classroom-membership-*解決；共同需求雙方段落均保留。三張PNG以Java24、PlantUML1.2026.10 CLI重新產生，退出碼0且PNG簽章正確，圖意未改。

整合後Python完整回歸619 passed、1 Windows POSIX skip、98 subtests passed（114.11秒）；Node88 passed。非真人Google或原生複製分頁證據，T018／T019仍待真人驗收及最後收斂。完整人工矩陣與審查紀錄見docs/pr24-issue17-integration-review.md。


## 真實瀏覽器自動補驗

2026-11-28，獨立headless Chrome 158.0.8127.37、真Flask HTTP與臨時fixture DB，7項斷言通過：雙堂並存；前景F5保持原堂原組；單頁離線／恢復不換另一堂；同來源opener複製sessionStorage後取得獨立操作作用域且教師在線計1；同堂異組拒絕；關原頁另一頁仍計1；取消保留草稿、確認只清本頁並回碼／組號空白加入頁，另一堂仍保持。

此為Codex自動操作真Chrome，並非真人Google驗收；opener複製不是瀏覽器選單「複製分頁」，亦未量測關最後頁的5秒目標。早期測試腳本曾在載入前送表單或在背景操作輸入框，修正為等待頁面腳本就緒及先切前景後，本輪完整通過，沒有因此修改產品程式。原生複製、真Google、真人兩組、最後頁離線延遲仍待M01～M12。

人工啟動器已以--check核對憑證檔路徑存在及獨立DB初始化，未啟動Google授權或修改原DB；未執行的人工項目仍保持未完成。


2026-11-28 真人發現關課後F5顯示缺資格，已補最小終態標記修正及回歸；完整Node90項通過。前述自動88項為整合基線；關課F5尚待真人重驗。M12回填預覽使用者已明確回報通過，其他逐步回報與3組待驗工作見docs/pr24-issue17-integration-review.md，T018／T019保持未完成。


## 2026-11-28 最終人工驗收與收斂

整合基底master 2c43854 + PR24 07a9f15；關課F5修正提交5a27264。使用者已逐步確認跨堂分頁、原生複製及在線去重、重新加入草稿／pending、教師登入登出、關課終態及修正重驗、歷史與#19／#20預覽。操作者為本對話使用者，未提供姓名、瀏覽器版本或獨立截圖，不補造。人數歸零及離線恢復均為使用者估計1秒內，符合5秒目標。

最後一組已明確回覆「是」：兩個獨立瀏覽器／訪客視窗加入QA17-B第2／6組，教師各見在線1人；第2組先完整提交同題、第6組再交不同答案，結束後教師及兩學生結果正確，第2組順位1且勝出、第6組順位2，各自原答案及F5結果保留。未藉此宣稱測試了兩個不同自然人。

自動完整Python整合基線619 passed、1 Windows POSIX skip、98 subtests passed；前端修正後完整Node90 passed。真Chrome自動補驗7項與真人原生複製分開。權限、資格到期、世代、CSRF、競態、課堂碼重用、晚到回覆及重試key依既有受控契約／整合／Node證據。瀏覽器封鎖送答用於pending介面驗收，不冒稱Google自然失敗或伺服器已寫入後丟失回覆。本輪回填只驗證預覽，未另操作真Sheets寫入；既有回填回歸保留。

Converge對照5 FR、3 SC、規格三組情境、計畫中的分頁授權／原子換組／恢復交接／在線去重／送答作用域／資料保留、19任務與六項憲章原則，未發現missing／partial／contradicts／unrequested產品缺口。前後extensions.yml皆不存在。Converge本身未改tasks或追加空階段；此段及T018／T019勾選為獲授權交付文件收尾，與唯讀檢核分開。

✅ Converged — the implementation satisfies the spec, plan, and tasks.

三圖保留後端權限、固定堂／組及本頁清除責任；關課修正僅以非授權終態標記延續圖中CLOSED分支，不新增身分或資料可見範圍。圖檔已依功能重命名並CLI重繪、核對；同學原先審圖回報保留，本輪整合與F5修正尚待同學互審，不冒稱已取得新的APPROVED。未推送、未合併master或關閉Issue #17。
