# 介面契約

## A 匯入

沿用講義工作區及既有匯入交握。空白、不合法 URL 與 INVALID_SHEETS_URL 對應可讀的欄位錯誤，使用 aria-invalid 與 aria-describedby。權限不足及暫時失敗可辨識，修正後可送出並清掉舊提示。

| 訊號 | 顯示與處理 |
| --- | --- |
| 空白、瀏覽器 URL 格式錯誤、`INVALID_SHEETS_URL` | 欄位旁顯示修正提示。空白與格式錯誤有各自文案。 |
| `SOURCE_READ_FORBIDDEN`、`SOURCE_NOT_FOUND` | 操作區提示檢查分享權限、Google 帳號或來源是否存在。 |
| `GOOGLE_REAUTH_REQUIRED`、`GOOGLE_CREDENTIALS_REFRESH_REQUIRED` | 提示重新授權，沿用既有授權流程。 |
| `SOURCE_READ_UNAVAILABLE`、`GOOGLE_RATE_LIMITED` 或網路請求失敗 | 操作區提示暫時無法讀取並可稍後重試。 |

保留教師輸入的原始連結。依實際回應的錯誤碼分類，同時涵蓋匯入流程狀態所回傳的讀取錯誤。修正後重新提交時清除舊提示。

## C 結果

學生沿用 `GET /student/classrooms/{id}` 與獨立的課堂狀態輪詢；`GET /activities/{activity_id}/results` 及 `GET /classrooms/{id}/results` 沿用 003／009 授權。課堂 OPEN 時可查當前與合法同堂歷史。整堂 CLOSED 時，狀態只提供結束資訊，學生結果入口拒絕讀取；由狀態同步終止請求、清除內容並顯示關課通知。教師保留歷史與回填。pending 持續自動查詢，unavailable 顯示無正式資料並停止該次自動查詢，settled 停止該次自動查詢並渲染 display_number、winner_items、groups[].items 或 own.items。保留舊答案格式與換行。教師已授權結果可含 groups；依 D06，學生取得勝組名稱與答案，以及本組答案與順位。讀取失敗顯示錯誤並提供同目標重試，切換後晚到的結果與錯誤皆須丟棄。

手動選取歷史活動後，該選取優先顯示；當前活動的自動查詢即使晚到也不得覆蓋歷史結果或錯誤狀態。偵測到下一活動時撤銷舊選取與請求，恢復新活動主畫面。學生仍可手動再次選取同堂歷史。

## B 在線

教師組別入口在授權後提供各組在線估計，資料失敗時顯示過期或錯誤，關課時顯示已關閉。更新在線需有效課堂參與證明，組別由伺服器授權資料取得。統計綁定內部課堂 ID，加入碼重用不轉移在線狀態。學生以現有授權呼叫 `POST /classrooms/{id}/presence`，body 只接受 `page_id`，成功回 204。每頁每 3 秒更新，伺服器 25 秒逾時。教師組別 API 回傳 `classroom_state` 與各組 `online_count`，整堂 CLOSED 時人數為 null，學生更新回 409。加入與重連、關頁與斷線的端到端目標分別為 5 秒與 30 秒。
