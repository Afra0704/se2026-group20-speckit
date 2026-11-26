# 009 與 003／001 的交接契約

**狀態：003具體函式／介面／分工仍依T003核對，未自行發訊。** 使用者於2026-11-26回報C1雙組行為與C2新版圖意皆已確認，含D16→D22學生禁讀行為；姓名／獨立連結未提供。此行為確認不代替下表具體技術核對，本輪不改quiz／notes程式、不替同學定順位或結算演算法。

## 受理

現有 `quiz/submission_gateway.submit()` 在 write_transaction 內呼叫 `activities.submission_context`，再呼叫 ACCEPT_SUBMISSION(db,context,answers)。正式 003 應保留同一 db／transaction，不自行 commit 或另開寫交易。確認 classroom OPEN、指定 activity 為該堂當前且 LIVE、原 membership／group 屬同堂、題目及 items 屬固定版本後才接受。不能由 code 或最新活動替換原 activity_id。先關課確認則拒絕；先接受 commit 的答案即使之後關課仍保留原歸屬。

組內排序、去重及結算由 003 定義，D02 截止語意不變；R8 驗證需與正式 003 測試一起重跑。無 provider 維持 QUIZ_UNAVAILABLE，不新增示範答案、假順位或假勝組。

## 結果及恢復

`classroom_membership` 拆 scoped identity 與 OPEN content guard，`group_for` 預設僅允許 OPEN。state 的 CLOSED 最小提示獨立走身份 helper，禁止透過 state_view 洩漏題目。GET classroom results 及 GET activity results 都須 guard；直接指定活動同樣檢查原課堂 OPEN，不可只檢活動 CLOSED。

結果DTO與授權在同一read transaction完成，交易開始即查權威原課堂狀態／身份；關課commit後新開始的內容讀取交易一律拒絕，不沿用其他請求的OPEN判定。關課前已於同交易合法驗證OPEN的回應可晚到，但前端確認CLOSED後不得再套用。學生只能讀D06的勝組與own，LIVE不含別組資料，pending不回假結果。交易驗得整堂CLOSED時即使已結算／proof未過期仍拒絕。學生偽造 X-Activity-Role:teacher 須經 require_teacher＋owned_classroom，header 不授權。

## 教師歷史／001 回填

- 教師仍可由原 classroom_id／activity_id 列出全部原活動，讀已結算結果；不套學生 OPEN guard。
- get_activity_reference／get_ended_snapshot 保持原 teacher_context、activity_id、import_id／version、result_version 關係。未結束 ACTIVITY_NOT_ENDED；已結束未結算 RESULT_NOT_READY。關課不等於結算已完成。
- 001 不因碼重用改 catalog／活動快照／勝組，不清來源 Sheets、不重送未知寫入；原 preview／operation／report 及先回讀恢復規則保持。
- 關課重送不再 transition、結算或通知新的勝組；結算任務冪等仍由 003 負責，但不得依 code 定位資料。

## 請同學逐項核對

| 項目 | 核對證據／狀態 |
| --- | --- |
| 受理 callback 共用交易，關課先後的 R8 | 待正式 003 指定函式、測試案例與版本。 |
| 全部直接結果路徑使用 OPEN content guard | 待核對是否另有匯出／預載／訂閱／快取入口，不能漏學生資料出口。 |
| 關課觸發結算且重送不重做 | 待 003 明確原有排程／重試方式，不在 009 擅自設計新 worker。 |
| CLOSED 與 settled 分離，教師原快照／001 不受學生禁讀影響 | 待整合測試與正式 provider 證據。 |
| 原 CLOSED result-access 204→409、closed state 最小化 | 需共同調整舊004測試預期；新版圖意及OpenSpec D16／D22行為同步已由使用者回報確認，具體入口／技術核對及具名來源依本表追蹤。 |

研究確認舊 test_classroom_results 明確期待 CLOSED 恢復及結果，test_classroom_close 期待 closed activity 與新加入409；後續更新這些受影響預期，保留教師歷史、非課堂002及課堂仍OPEN的活動結果測試，不能只刪失敗測試。

## 009 本機落點／正式整合邊界（2026-11-26）

現有`submission_gateway.submit`沿用write_transaction內submission_context→ACCEPT_SUBMISSION(db,context,answers)，受控測試驗close先拒絕及accept先保留原activity／group；沒有重寫正式003。學生room state以identity_for提供CLOSED三欄最小提示；room results與activity results以group_for要求OPEN，後者由db.read_view提供同交易授權／DTO。教師原owned_classroom及get_ended_snapshot不套學生guard。

`test_classroom_results`與`test_classroom_close`舊授權預期已更新，OPEN堂活動結果仍可讀；`test_classroom_notes_integration`保留教師關課後的原快照／回填預覽。受控Google測試不是正式003或真實Sheets結果。

PR9 head31b0e23之接口與責任已按使用者指示檢查，見[pr9-review.md](../pr9-review.md)。正式合流仍待T051：try_pending可開寫交易，必須先重試結算、再開最終read transaction重新驗權並讀取結果，不能直接以本分支read_view包住PR9原view。保留003 Idempotency-Key、QuizSubmission及pending／unavailable語意；本分支僅在該靜態資產存在時掛載，未引入其演算法。003-D22／009-D22編號待整合統一，不代表重新質疑已確認行為。
