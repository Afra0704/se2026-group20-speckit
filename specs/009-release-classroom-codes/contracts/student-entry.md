# 009 學生獨立入口、恢復與狀態契約

學生使用碼＋組別，無 Google 登入。以固定內部 ID 在 URL 導航，使用者不需要輸入或選擇 ID。下列頁面路由與技術回應為本輪設計，未實作。

## 頁面

| 入口 | 行為 |
| --- | --- |
| GET /student | 純加入頁，清楚欄位／送出／錯誤與重試；已有資格也不背景重送或自動加入。首頁「我是學生」指向此頁。 |
| GET /student/classrooms/{classroom_id} | 固定該堂的無內容 shell；未驗權前不 SSR 題目／結果。有效資格後讀狀態，OPEN 顯示課堂，CLOSED 顯示結束頁。沒有 join 表單／常駐登入提示。 |
| 加入其他課堂按鈕 | 明確導航 /student，不自動送舊碼或舊組別、不清教師 session。舊堂 URL／其他分頁不改向新堂。 |

加入 POST 成功 201 後才使用伺服器 classroom_id 導航；pending 防重送，失敗不改目前 grant／proof、不轉頁。返回、窄螢幕、Tab／Enter、錯誤焦點與狀態播報納入人工驗收。

## API／授權

| 入口 | 原資格有效且 OPEN | CLOSED | 無權／不符 |
| --- | --- | --- | --- |
| GET /classrooms/{id}/state（student） | 原欄位、原組、當前活動及可見題目；同 read transaction 驗權及組 DTO。 | 原身份有效才回 200 最小 `{classroom_id,classroom_state:CLOSED,state_version}`；不帶 activity、questions、group_name、結果或碼。 | 401 AUTH_REQUIRED／403 FORBIDDEN，不回是否存在或 CLOSED 的內容。 |
| POST /classrooms/{id}/result-access | 以該堂原 path proof 驗證、在寫入交易檢 OPEN，204 發新可讀／可提交 grant，適用原組；不接受 body 指定組別。 | 409 CLASSROOM_CLOSED，零新 grant、零 Set-Cookie／session 更新。 | 403 RECOVERY_DENIED；body 指定 group_id／group_name 回400 INVALID_REQUEST。 |
| GET /classrooms/{id}/results | 經 OPEN guard，列同堂已結算活動；未結算不偽造結果。 | 409 CLASSROOM_CLOSED，錯誤 body 無內容。 | 原 401／403。 |
| GET /activities/{id}/results | 由該活動原 classroom_id 找原學生授權，OPEN 才按 D06。 | 409 CLASSROOM_CLOSED，禁止回題目／winner／own／groups。 | 原 401／403；不依同碼／同名推權限。 |

`result-access` 名稱保留以避免破壞既有路由，語意改為僅開放課堂的恢復；原 CLOSED 恢復功能刻意移除。closed state tombstone 是提示，不是內容權限。Teacher state／history 分支只驗教師 ownership，不套學生 OPEN guard。

grant 過期而 proof 有效時，可依固定堂 ID 明確恢復一次，再讀 state；若已關課即停止並顯示結束。proof 缺少／失效須回獨立加入流程，不以碼回復。CSRF 驗證及 limit_attempts 沿用，不能忙碌時無限恢復。

## Cookie／session

保留 session `classroom_grant`，proof 為 HttpOnly、SameSite=Lax、沿用 SESSION_COOKIE_SECURE 及 RECOVERY_SECONDS，path 維持 `/classrooms/{id}/result-access`。proof／grant 不進 URL、DOM、localStorage、console 或日誌。教師登出不清學生 session；學生換堂不動教師。CLOSED 依狀態拒權，不必刪歷史 grant／proof。

單一目前 grant 可被明確加入 B 取代；A 頁仍固定 A，session 不符則顯示資格變更／回加入頁，不轉投 B。A 原 proof 若尚有效且 A 仍 OPEN 可明確恢復；如另頁正在切換，任何舊回應只可造成重新驗證，不得擴權。多堂歷史資格介面不在範圍。

## 畫面狀態與晚回

`JOIN_IDLE → JOIN_PENDING → ROOM_CHECK → OPEN_ROOM → CLOSED_NOTICE`；另有 RECONNECTING、REAUTH_REQUIRED。CLOSED_NOTICE 對該堂為 terminal，只有明確導航加入頁才能離開。

- 每個請求攜帶本地 generation、固定 room ID；活動結果／提交另固定 activity ID。回應套用前檢查相同世代、room、activity、state_version，晚回不跨頁套用。
- 得知 CLOSED 即增加 generation、取消舊 fetch、清題目、答案 DOM／草稿／結果及可提交能力；不再載入歷史結果或自動 result-access。僅留「課堂已結束」與「加入其他課堂」。
- pageshow（含 BFCache）與重新可見先隱藏舊內容、重新驗權，成功 OPEN 才顯示；pagehide 清敏感內容，closed terminal 不被較早 OPEN／results 回應覆蓋。純網路錯誤顯示重連而非常駐登入提示，停用提交，無法驗證時不顯示快取內容。
- 每次學生內容讀取在同一read transaction開始即查權威原課堂狀態／身份，並在該交易組裝DTO；不得沿用其他請求的OPEN判定或舊快照。關課成功commit後新開始的內容讀取交易一律拒絕；交易驗得CLOSED時只回最小結束提示或409，不帶題目／結果。關課前已於同交易合法驗證OPEN的回應可能晚到，前端一旦確認CLOSED即清內容並以terminal／generation拒絕套用，包括這類合法舊回應。無法收回先前已合法閱讀／自行保存的內容，不承諾即時遠端抹除。
- no-store 沿用所有受保護 HTML／JSON，無前端含學生資料快取或 service worker 新增。
