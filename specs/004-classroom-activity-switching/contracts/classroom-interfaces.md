# Phase 1 接線契約

以下是 002 課堂改版的介面。001 在分支提交 `418365f` 提供的函式見 [交接文件](https://github.com/Afra0704/se2026-group20-speckit/blob/418365f/docs/001-course-handoff.md)。真實接線仍待兩邊合流驗證。

| 邊界 | 輸入與輸出 |
| --- | --- |
| 002 驗證課程擁有者 | `activities.course_service.get_owned_course(teacher_context, course_id)` 重新驗證教師，回 `course_id`、`teacher_id`、`title`。不存在或非本人課程回 `404 COURSE_NOT_FOUND`，登入身分不符回 403。 |
| 002 → 001 課程講義 | `notes.course_catalogs.list_course_catalogs(teacher_context, course_id)` 提供講義與版本。建立活動時呼叫 `get_course_catalog(teacher_context, course_id, import_id, import_version)`，即使兩課程屬同一教師，跨課程版本回 `404 CATALOG_NOT_FOUND` 且不得建立活動。缺少提供者回 `503 CATALOG_UNAVAILABLE`。 |
| 課程內匯入預覽 | 從選定課程連到 `/teacher/notes/courses/<course_id>`。001 建立預覽時驗證教師與課程並綁定 `course_id`，確認時以伺服器綁定的課程再查權限。 |
| 教師課程／課堂 | 列出／新增本人的課程、在指定課程建立及列出課堂，以及查看活動歷史。所有資源走後端 ownership 檢查。 |
| 學生加入與同步 | 加入輸入課堂碼與組名，回傳 `classroom_id`、`group_id`。狀態提供 `classroom_state`、`state_version`、`current_activity_id` 和活動階段，無活動時回空指標。 |
| 教師開啟、切換及關課 | 操作包含課堂與指定活動識別。已有搶答中活動或課堂已結束回 409。關課須有明確確認；成功後同一交易完成課堂與仍進行中的活動結束。 |
| 003 受理 | 使用提交時的原 `activity_id`。在寫入交易內驗證課堂開放、該活動為當前且搶答中、學生組別屬本堂，以及題目和項目符合固定版本。競爭關閉後不得寫入。 |
| 學生歷史結果 | 以原瀏覽器證明恢復課堂結果權限，清單只列出同堂已結算活動。直接請求指定活動時，從學生授權取得原課堂與組別。跨堂回 403，同堂已結束但未結算只回結算狀態，結算完成才依 D06 提供勝組及本組欄位。 |
| 002／003 → 001 快照 | `activities.teacher.get_activity_reference(teacher_context, activity_id)` 回 `activity_id`、`import_id`、`import_version`、`ended`。沿用 `get_ended_snapshot(teacher_context, activity_id)`。未結束回 `ACTIVITY_NOT_ENDED`，已結束未結算回 `RESULT_NOT_READY`。指定活動讀取不受當前活動切換影響。 |

受保護入口禁止快取，寫入入口沿用共用 CSRF。狀態或角色衝突不得把請求自動轉往目前活動。
