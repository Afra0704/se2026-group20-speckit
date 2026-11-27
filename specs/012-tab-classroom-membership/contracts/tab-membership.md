# 012 課堂分頁契約

以下為 012 的實作契約。既有教師與獨立活動的授權介面沿用。新學生入口在加入請求帶上 `page_protocol: 1`。使用瀏覽器專用 cookie 或帶 `X-Classroom-Protocol: 1` 的學生請求只接受分頁授權。所有 POST 沿用 CSRF。

| 操作 | 成功與限制 |
| --- | --- |
| 加入 | `POST /classroom-memberships` 接受 `code`、字串 `group_name`、`page_protocol`、本次文件的 `page_id` 與 `request_id`。成功 201 回 `classroom_id`、`group_id`、`resume_id`。由目標課堂頁啟用短效文件資格。#16 無效組號回 400 `INVALID_GROUP_NUMBER`；同堂已有異組活躍分頁回 409 `CLASSROOM_GROUP_IN_USE`，原頁資格保留。 |
| 分頁啟用／恢復 | `POST /classrooms/{classroom_id}/tab-access` 接受 `resume_id`、當前文件新產生的 `page_id`、`request_id`。重整主張可附 `handoff_id` 作本機操作交接的證據。成功 200 回固定堂組、新頁 `resume_id`、`page_token`、`expires_at` 及 `continued_operation_scope` 是否可沿用。同一請求重試不得建立第二個頁面。 |
| 狀態、歷史、結果、作答、在線 | 學生以 `X-Classroom-Tab` 傳本頁的 `page_token`。從伺服器資料核對 cookie、固定課堂、原組、世代及端點允許的狀態。學生請求缺少／無效文件資格回 401 `CLASSROOM_TAB_REQUIRED`；跨堂或瀏覽器不符回 403。教師沿原授權路徑。 |
| 本頁重新加入 | `POST /classrooms/{classroom_id}/tab-access/revoke` 使用目前 `X-Classroom-Tab` 與 `request_id`。有草稿或未決答題先警告；取消無副作用。成功或同頁同操作已完成均回 204。才清本頁並回空白加入頁；無法確認時保留重試識別。 |
| 關頁與重整 | 保留 `POST /classrooms/{classroom_id}/presence/leave` 與 010 逾時備援。Beacon 在 POST body 送 `page_id`、`page_token`、`csrf_token` 及選填的一次性 `handoff_id`，只有離線端點接受此形式。通知只標記在線離開與交接資訊，保留可恢復資格。 |

過期、撤回或世代失效且無法恢復回 401 `CLASSROOM_REJOIN_REQUIRED`。已關課的狀態讀取只回 CLOSED 終態，其他學生操作回 409 `CLASSROOM_CLOSED`。成功授權回應使用 no-store；`resume_id` 與 `page_token` 不寫入 URL 或日誌。加入／恢復／撤回的重試紀錄以操作、瀏覽器、課堂與 `request_id` 綁定，重試使用原請求內容。持久資料中的原答案、勝組、順位與回填不可因撤回修改。

文件資格最長 15 分鐘，恢復索引沿用初始化時的既有 7 日上限。當前文件以原 `X-Classroom-Tab` 及原恢復索引呼叫啟用端點時，伺服器逐一驗證兩者指向同一文件，再於同一交易中移轉在線保留與未決操作作用域。

JS 在加入頁啟用前確認專屬 HttpOnly 瀏覽器 cookie 已於學生頁回應建立。加入與恢復的衝突判定都須使用該穩定識別，不能用加入請求臨時給的值消除衝突。請求識別重用但語意內容不同回 409 `CLASSROOM_TAB_REQUEST_CONFLICT`。重試成功回到同一邏輯分頁，並在原權限仍有效時取得可用文件資格。

送答明確拒絕與結果未知依 #18 契約接續。回覆未知時註明伺服器可能已受理；重新加入不改既有作答順位或歷史。


## 關課後重新整理（2026-11-28 驗收修正）

已從伺服器確認CLOSED的頁面，清除恢復索引與記憶體資格，僅於本頁sessionStorage固定內部課堂ID下留下{closed:true}顯示標記。F5依此顯示終態，不重新申請資格或讀取題目、結果與在線資料。此標記不是授權、不得用於查詢新課堂，不以課堂碼作key；另一課堂的儲存及資格保持。未曾取得終態且無有效資格的全新頁面仍要求重新加入。
