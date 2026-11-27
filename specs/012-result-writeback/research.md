# Phase 0 Research: Issue #19

日期：2026-11-27。研究本機 PR14 合併基底 `e9a29c7`，只讀程式及規格；未查憑證或操作真實來源。依技能要求，由唯讀研究代理核對回填、資料歸屬、錯誤及測試，主代理彙整。

## R1 指定活動入口

**Decision**: 沿用 `POST /teacher/notes/export-previews` 的 activity_id 與 CSRF，由所選結果表單直接提交，303 到 preview。GET 帶 activity_id 僅作安全返回／重試頁。
**Rationale**: `routes.create_export_preview` 已限制欄位並固定伺服器快照；`notes/static/notes.js` 的 `[data-current-activity]` 會填 localStorage 最近活動，不可作歷史依據。
**Alternatives considered**: GET 自動讀來源產生預覽會讓重整有副作用；以目前活動或標題查找會選錯場；另造 endpoint 複製原流程。

## R2 原活動與歷史歸屬

**Decision**: Context 按 activity_id→classroom_activities→classrooms→courses 查原教師，講義仍用原 import_id/version；不限制 classroom.state 或清單可見狀態。
**Rationale**: `teacher.get_activity_reference`、`classroom_access.requested_activity/owned_classroom` 已支援原堂權限；`notes.export_service._bundle` 按固定版本讀。不可改用供新活動選擇的講義清單查詢。
**Alternatives considered**: 新增持久 context 複本有同步與遷移成本；按加入碼或名稱會衝突。舊獨立活動模式保留原權限路徑，無課堂資料不捏造課堂。

## R3 勝組與格式

**Decision**: 按原 classroom_id＋winner_group_id 批次校驗，再呼叫 #16 formatter。保留快照原 ID，僅教師 DTO 加 label。資料錯誤沿用 `RESULT_INVALID`（422），加 `reason=WINNER_GROUP_SCOPE_MISMATCH`。
**Rationale**: 目前 classroom_groups 只有 id/classroom_id/name，尚無 #16 修改；`settlement.question_result` 將原 group ID 序列化為字串，數字 ID 不等於組號。DTO 外加顯示欄位不影響 validate_snapshot／digest。
**Alternatives considered**: 格式化 group_id、借用他堂同號組、猜舊名稱均違反契約。新增錯誤碼無必要，沿用錯誤加 reason 可減少共同契約變更。

## R4 全部無勝組

**Decision**: 保留全 skip 預覽與低階確認回 completed 的既有契約；UI 明示「沒有勝組可回填」且停用確認，不產生任何來源寫入。部分無勝組保留各題 skip。
**Rationale**: 現有 integration tests 允許全無勝組預覽／確認；Issue 要求不同提示及無勝組略過，沒有要求新的 HTTP 錯誤。現有 ACTIVITY_NOT_ENDED／RESULT_NOT_READY 已各自區分。
**Alternatives considered**: 新增 NO_WINNER 錯誤會破壞原低階測試與恢復行為；當作未結算會無限等待。全 skip 預覽仍可能讀來源，不承諾零讀取，但必須零寫入。

## R5 報告、確認及恢復

**Decision**: 在 get_saved_preview、confirm、_snapshot、recovery_preview 接線 context 校驗；壞標籤不抹除原報告，顯示錯誤並拒絕新增寫入。沿用原寫入與恢復狀態機。
**Rationale**: confirm 已有冪等、預覽消耗、來源鎖、lease、逐題組來源檢查及回讀。get_report 在租約過期時會把 writing／queued 轉 recovering，此既有本機恢復行為保持；新 context 讀取不觸發 Google 或重結算。
**Alternatives considered**: 重寫寫入器增加風險；直接整頁報錯遮蔽操作證據；僅前端驗證擋不住直接請求。

## R6 時間與相依協作

**Decision**: 以最新 `011-time-display/spec.md` 作設計輸入：台北至分鐘（YYYY-MM-DD HH:mm，截取不進位）、未知／缺值／壞值分開、來源已證明 UTC 才以 UTC 解讀；採其共用介面並保留原精度。#19 僅提供原欄位及事件語意。
**Rationale**: 現有 taipei_time 對 naive 輸入依 host 時區解讀且無壞值保護。#20 已有規劃且共同政策已依使用者回報確認；實作合流仍需核對，不能為 #19 自建另一個時間核心。
**Alternatives considered**: 全部加八小時、用 created_at 假充結算或瀏覽器另格式化皆有風險。quiz_settlements 沒有 settled_at，不新增假事件。

## 研究結論與整合條件

技術選擇已確定，無新框架或 migration。#16 formatter／儲存欄位、#20 formatter／fallback 契約及合流提交仍須實作前取得；此為明列的相依輸入，不是對方已承諾的函數名稱。#19 C1-A–C 已於 2026-11-27 依使用者回報記為雙組確認；具名技術責任、實作與真人驗收仍依原任務核對。
