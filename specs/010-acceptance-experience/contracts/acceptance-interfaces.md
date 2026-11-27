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

2026-11-27 使用者驗收修訂：貼連結表單先建立意圖並呼叫既有 read；格式錯誤及讀取權限／網路失敗均留在連結區，不跳失敗頁。同一連結再按「讀取講義」時先 GET 原 flow，failed 或可接手的 reading 使用 retry，已 worksheets_ready／preview_ready 則直接繼續；不自動重送。修改來源建立新 flow。授權續接後若 link 來源的 read 失敗，HTML flow 頁渲染同一連結表單、錯誤文案與原 flow 參考，保留原 course／owner／browser 授權；JSON 契約不變。預覽與雲端來源的重試流程不變。

## C 結果

學生沿用 `GET /student/classrooms/{id}` 與獨立的課堂狀態輪詢；`GET /activities/{activity_id}/results` 及 `GET /classrooms/{id}/results` 沿用 003／009 授權。課堂 OPEN 時可查當前與合法同堂歷史。整堂 CLOSED 時，狀態只提供結束資訊，學生結果入口拒絕讀取；由狀態同步終止請求、清除內容並顯示關課通知。教師保留歷史與回填。pending 持續自動查詢，unavailable 顯示無正式資料並停止該次自動查詢，settled 停止該次自動查詢並渲染 display_number、winner_items、groups[].items 或 own.items。保留舊答案格式與換行。教師已授權結果可含 groups；依 D06，學生取得勝組名稱與答案，以及本組答案與順位。讀取失敗顯示錯誤並提供同目標重試，切換後晚到的結果與錯誤皆須丟棄。

手動選取歷史活動後，該選取優先顯示；當前活動的自動查詢即使晚到也不得覆蓋歷史結果或錯誤狀態。偵測到下一活動時撤銷舊選取與請求，恢復新活動主畫面。學生仍可手動再次選取同堂歷史。

2026-11-27 案例 18 補正：`GET /classrooms/{id}/results` 歷史清單的暫時傳輸失敗只顯示局部「歷史結果清單讀取失敗，重試」，不使課堂狀態失效或清掉已載入題目／結果；暫停該清單自動重抓，按重試後接續。`/activities/{id}/results` 的單場錯誤按鈕保持。兩者如收到身分／權限或課堂 CLOSED 錯誤，仍清除受保護內容並走原驗權／終止流程；狀態輪詢獨立運作。

## B 在線

教師組別入口在授權後提供各組在線估計，資料失敗時顯示過期或錯誤，關課時顯示已關閉。更新在線需有效課堂參與證明，組別由伺服器授權資料取得。統計綁定內部課堂 ID，加入碼重用不轉移在線狀態。學生以現有授權呼叫 `POST /classrooms/{id}/presence`，body 只接受 `page_id`，成功回 204。每頁每 1 秒更新，伺服器 4 秒逾時。教師組別 API 回傳 `classroom_state` 與各組 `online_count`，整堂 CLOSED 時人數為 null，學生更新回 409。加入與重連、關頁與斷線的端到端目標均為 5 秒（2026-11-27 使用者修訂）。

2026-11-27 正常關頁增補：`POST /classrooms/{id}/presence/leave` 沿用學生授權與 CSRF，body 僅 `page_id`，成功 204。pagehide 使用獨立、keepalive 的 fetch，不綁被終止的輪詢 AbortController；只移除該瀏覽器的指定頁，不改組別與 quiz。離開標記保留 120 秒以拒絕晚到心跳復活，清理已到期標記；pageshow 恢復時使用新頁面識別。單純背景切換不呼叫 leave。教師下一輪取得最新統計；通知未送達仍以原 25 秒逾時備援。

同日 Firefox 實測修訂：離頁優先以 navigator.sendBeacon 傳送，Beacon 不支援／拒絕佇列時才用獨立 fetch keepalive；隱藏頁的每次心跳亦優先 Beacon。Form payload 接受 `page_id` 與既有 `csrf_token`，全域 CSRF 檢查先執行後移除 token 欄位，再驗證僅有 page_id；JSON header 用法保持。這能避免依賴一般離頁 fetch，仍不保證已被瀏覽器凍結的計時器能持續執行。

2026-11-27 最新計時修訂：5／5 秒取代本文件前述歷史 5／30 及 25 秒備援。heartbeat 每秒一次，TTL 4 秒，教師維持每秒輪詢。online 事件立即更新 presence，以 generation 隔離舊請求，避免被已中止但未完成的心跳阻擋；舊請求完成不可清掉新請求的 pending 狀態。
