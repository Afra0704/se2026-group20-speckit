# HTTP / UI Contract

本文件為 #19 設計；保留既有路由、快照及確認契約。所有路由教師專用，沿用 session、CSRF、HTML／JSON 錯誤包裝；不放寬學生權限。

## 目前／歷史結果入口

`classroom.js` 為顯示中的所選 activity 建立「預覽回填講義」POST 表單，action 為下列既有路由。使用當下結果選取 ID，附 CSRF；不得從 localStorage 最近活動、current_activity_id、活動名或課堂碼補選。晚到回覆不可將按鈕改綁其他活動；準備／搶答中呈現「活動尚未結束」而不允許寫入。

## POST /teacher/notes/export-previews

- HTML：僅 `activity_id`、`csrf_token`；JSON：僅 `activity_id`，CSRF header 沿用既有規則。
- 勝組、座標、講義／結算版本等額外欄位均拒絕，不能由前端指定。
- 順序：驗教師→原堂／版本→已結束快照→原堂勝組→讀來源／辨識→再驗權與原結果→短交易保存。
- 成功 HTML 303 到既有 preview URL，JSON 201，增加 [顯示投影](display-context.md)。只讀來源，不寫入。
- 全無勝組仍可 201 產生全 skip 預覽；頁面顯示「沒有勝組可回填」，停用確認。部分無勝組逐題略過。

## GET /teacher/notes/export-previews?activity_id=...

作為 PR14 授權安全返回／建立失敗後的重試頁。先驗權，顯示指定活動及 hidden activity_id 與「讀取來源並建立預覽」；不要求手輸 ID，不讀 Google、不建立預覽。無 query 時顯示已保存預覽的活動脈絡及「從課堂結果選擇活動」導引，不自動取最近活動。已存清單項目各自驗權，不能藉清單洩漏其他課程資料。

## GET /teacher/notes/export-previews/{preview_id}

由保存資料查原活動，驗來源教師及活動／課程教師歸屬；不重新結算、不讀 Google、不換最新版本。回原資料＋activity_context＋勝組 labels。無效勝組保留既有預覽與安全診斷，呈現 context error 並停用新確認；不能當作無勝組。

## 返回原活動結果

預覽與報告由伺服器根據原活動脈絡產生 `activity_context.result_url`：`/teacher/workspace/courses/{course_id}/classrooms/{classroom_id}?activity_id={activity_id}`。三個識別均取自已驗權原資料並編碼；不接受前端 return_to 或 localStorage 決定活動。此為既有 workspace.classroom 路由新增只讀選取參數，與 Sheets 重新授權返回 allowlist 分開，不需要放寬後者。

workspace.classroom GET 須先驗教師及 course／classroom／activity 同屬關係；activity_id 限單一、非空且符合既有識別長度／控制字元規則。無效參數回 400 INVALID_REQUEST；不存在或跨堂回 404 ACTIVITY_NOT_FOUND；未授權沿用既有拒絕規則，均不自動改選目前活動。合法值交給頁面 data-selected-activity-id，classroom.js 在原堂清單載入後選取並讀取該活動結果，保留 query 讓刷新可重現；後續結果請求仍由 API 驗權，晚到回應不能更換選取。

已關課仍允許原教師讀原活動；沒有 activity_id 時維持原頁面行為。舊非課堂活動沒有 workspace 路徑，顯示「返回教師頁」而不宣稱已恢復原課堂結果。不為返回而讀寫 Sheets 或重建回填預覽。

## POST /teacher/notes/export-previews/{preview_id}/confirm

保留 `confirm`、`overwrite_item_ids`、原冪等鍵／CSRF 契約及 HTTP 回應；新增原堂勝組檢查後才可新增 operation／寫入，且每批寫入前與既有 `_snapshot` 校驗一起重驗。重送既有 key 可讀同一報告，不重寫。全 skip 的既有低階確認相容行為保持，寫入數為零。

## GET /teacher/notes/operations/{operation_id}

由 owned_operation→原 preview→原 activity 建投影。JSON 增加 context 及 label，HTML 使用一致標籤。已保存操作的 mapping 錯誤不遮蔽報告：200 回原紀錄及 `context_error`，明示資料錯誤、停用恢復；缺權限仍依原規則拒絕。原 get_report 的過期租約轉 recovering 行為保留，不新增 Google 讀寫。

## POST /teacher/notes/operations/{operation_id}/recovery-preview

沿用無額外業務欄位＋CSRF，原堂驗權／勝組校驗後先回讀再建立恢復預覽，HTML 303／JSON 201。使用原 origin/root／快照／勝組；不能改 activity 或 result_version。原已同意覆寫及新衝突仍分開提示。

## 錯誤與授權返回

| 情境 | HTTP／code | UI／副作用 |
| --- | --- | --- |
| 輸入欄位或額外勝組／座標 | 400 INVALID_REQUEST | 不讀寫來源 |
| 未結束 | 409 ACTIVITY_NOT_ENDED | 活動尚未結束 |
| 無可用結算 | 409 RESULT_NOT_READY | 結果尚未結算完成 |
| 有勝組 ID 但缺失／跨堂／無法格式化 | 422 RESULT_INVALID；安全 context.reason=WINNER_GROUP_SCOPE_MISMATCH | 顯示「勝組資料與原課堂不一致，無法回填」；不新增讀來源／寫入 |
| 未登入、學生或其他教師 | 沿用原 401／403／404 及既有 code | 不回受限 context、來源或答案；不新增對外存在性線索 |
| 來源／版本／覆寫／租約錯誤 | 沿用 SOURCE_CHANGED、PREVIEW_STALE、RESULT_VERSION_CHANGED、OVERWRITE_CONFIRMATION_REQUIRED、SOURCE_BUSY 等 | 保留原活動及安全返回 |
| Sheets 授權失效 | 沿用 PR14 既有 code 與重連元件 | 返回 allowlist 中的原 activity query／preview／operation；成功後由教師明確接續，不自動重送寫入 |

RESULT_INVALID 的 reason 是本輪擬新增診斷欄位，非 #16 輸入錯誤。#16 的 INVALID_GROUP_NUMBER（400）保持其原功能責任。
