# Phase 1 Data Model

本輪無新表、migration 或歷史轉換；以下為教師只讀投影與現有關係。

| 投影／既有實體 | 欄位與來源 | 關係／限制 |
| --- | --- | --- |
| ActivityExportContext | activity_id/title/phase（activities＋classroom_activities）；course_id/title、classroom_id/title/state | 原活動永久歸屬；課堂碼不作 join key；教師與課程／活動 owner 一致 |
| ActivityTimes | classroom_activities.created_at/started_at/closed_at | 分別標建立／開始／結束；缺值按事件狀態及 #20 呈現；無獨立結算時間不補造 |
| LectureReference | activities.import_id/import_version；notes_catalogs、notes_sources、notes_catalog_names | 原版本固定；講義名稱與來源分頁分開；不以最新版本或清單可見狀態替換 |
| WinnerLabels | 原 classroom_id、snapshot.units[].winner_group_id、#16 組號／formatter | 一次批次查原堂；所有非空勝組須找到且可合法格式化；組 ID 與組號分開 |
| ExportPreview | notes_export_previews.preview_id/activity_id/import_id/import_version/result_version/snapshot/created_at/status | 快照不加 label/context；教師 DTO 外加投影；created_at 僅預覽時間 |
| WriteOperation | notes_write_operations.operation_id/preview_id/origin_operation_id/root_operation_id/status/updated_at | 原活動／版本從 preview 取；updated_at 僅作業更新時間 |
| WriteItem | notes_write_items.question_id/item_id/blank_id/status/verified_at | 依原快照／講義綁定；verified_at 是回讀驗證時間 |

## Validation Rules

1. 每次 context 讀取先 require_teacher，沿用 requested_activity／owned_classroom 驗原堂／課程。教師關課歷史可讀；學生無此投影。
2. Preview activity/import/version 與原 reference 一致；snapshot 保持 validate_snapshot 嚴格 v1 形狀與 digest。
3. 正式課堂 snapshot 的勝組 ID 為 canonical 正整數字串；只做無損轉換查 INTEGER id，輸出保持原字串。不把 ID 當組號，不接受帶前導零或浮點值猜測。
4. 有 ID 查無／跨堂／組號無法合法格式化：回 RESULT_INVALID（reason=WINNER_GROUP_SCOPE_MISMATCH），阻止新 preview／confirm／recovery write。報告仍顯原操作明細與錯誤，不把資料錯誤改成 no_winner。
5. 不移除舊獨立活動模式及其測試；其 groups／teacher ownership 路徑保持，無課堂時顯示「非課堂活動」，不借用任意課堂。不為舊名稱轉組號。

## State Transitions

- Activity PREPARING／LIVE → 新預覽拒絕 ACTIVITY_NOT_ENDED。
- CLOSED＋無可用已結算快照 → RESULT_NOT_READY，保留原不可用資料提示。
- CLOSED＋已結算＋全 no_winner → 全 skip 預覽，明示沒有勝組，教師 UI 停用確認；原低階確認仍可完成 skip，零來源寫入。
- CLOSED＋已結算＋部分勝組有效 → preview ready；no_winner 題 skip。
- ready → consumed，與既有 operation／source lease 同交易；invalidated／consumed 不當新確認。
- operation queued／writing → completed 或 needs_attention；中斷後 recovering，保留既有租約判定。
- needs_attention／recovering → 先回讀 → 新恢復 preview；沿用 origin/root、原快照與覆寫同意，不重送 verified 或目前已匹配答案的題。
- context 錯誤是顯示／新操作驗證狀態，不改持久化 operation status、winner 或 snapshot。
