# 003 搶答與結果介面契約

> **009整合覆蓋規則（2026-11-26）**：本檔原D22記為003-D22，僅處理OPEN堂的晚加入結果。下文CLOSED沿用D16／原證明的敘述保留為PR9原契約紀錄，整合時由009-D22取代：CLOSED學生recover／results／原提交重試均拒絕，state至多回最小結束提示；教師原歷史及回填快照保持。結果入口先驗權、結束預檢讀交易，再try_pending，最後以新的read transaction重新驗權並組DTO，禁止巢狀寫交易。詳見[009整合契約](../../009-release-classroom-codes/contracts/quiz-history.md)。

## 既有提交路由

`POST /activities/{activity_id}/submissions`。沿用 CSRF、活動路徑與既有答案格式。正式前端在 header 帶 `Idempotency-Key`，以 UUID 代表同一次送答。body 只含 `question_id` 及 `items[{item_id, answer_text}]`。組別、來源空格、結果順序與活動階段由後端解析。

| 情境 | 回應與效果 |
| --- | --- |
| LIVE 且新操作有效 | 201 `{"status":"accepted"}`。保存整題，取代原有效提交；序列在 commit 成功才有效。 |
| 已受理的原操作，提交內容相同 | 有原組別查閱資格時，回相同 201 與原受理內容。無新受理、無新順位；不恢復被取代的舊提交。 |
| 同一操作識別，不同答案 | 409，`SUBMISSION_REPLAY_CONFLICT`。先核對同組授權，保留有效提交。 |
| 缺少／無效操作識別、缺漏小題或空白 | 400，保留原路由的驗證語意，識別格式錯誤用 `INVALID_REQUEST`。 |
| 無既有操作且已截止／非目前活動 | 依既有活動契約拒絕，例如 409 `INVALID_PHASE`。 |
| 教師、他組或缺合法資格 | 依既有 auth/CSRF 契約拒絕，不查回其他組收據。 |

前端在操作待回覆時鎖定按鈕，保存與 key 配對的原始 payload。回應不明時呈現「重試此次送答」並保留 key。學生明確「重新提交」才建新 key，即使內容相同。回覆不公開受理序列、暫時順位或其他組資料。

送出前在分頁的 `sessionStorage` 保存未確認的 key、原始 payload 與可比對的課堂、活動、組別及題目識別。重新整理後先取得伺服端確認的活動、組別與資格；同一分頁恢復原上下文時才顯示手動重試，使用原 key 及 payload。明確受理或拒絕後移除該筆暫存。切換到其他活動、組別或資格失效時不顯示也不送出。重新整理不自動發出送答請求，不跨分頁或裝置恢復暫存，不保存憑證。

## 既有 provider

| 入口 | 責任 |
| --- | --- |
| `activities.submission_context(db, activity_id, question_id)` | 為新送答產生可信活動、組別、階段、固定題目及講義版本。既有原收據另以同一組別及活動的查閱資格核對，不將它當成寫入資格。 |
| `ACCEPT_SUBMISSION(db, context, answers)` | 沿用簽章與外層交易，正式 context 提供本次操作識別。provider 不開巢狀交易、不自行 commit。 |
| `GET_PROGRESS(db, activity_id)` | 只供 gateway 電文投影 `question_id, group_name, submitted`。由目前有效提交判定，保留已加入但未提交的組別。 |
| `GET_SETTLED_RESULTS(db, activity_id)` | 回 `{snapshot, results}` 或 `None`。查詢函式不做發布，已授權入口先呼叫獨立待辦恢復服務再讀取。 |
| `get_ended_snapshot(teacher_context, activity_id)` | 驗教師擁有權、活動階段。未結束 409 `ACTIVITY_NOT_ENDED`；已結束但無可交付快照 409 `RESULT_NOT_READY`。成功回 001 的原 v1 DTO。 |

正常啟動註冊正式 provider。測試明確提供替代值或 `None` 時保留，既有刻意模擬不可用或待結算的情境可繼續測試。

## 結果路由與角色

`GET /activities/{activity_id}/results` 沿用既有授權，課堂請求的 `X-Activity-Role` 只辨別入口，不能取代教師及資源核對。

| 狀態 | 教師 | 學生 |
| --- | --- | --- |
| PREPARING／LIVE | `active`。LIVE 回每題各組提交狀況 | `active`，空進度，不含排名或作答 |
| CLOSED，正式待辦未發布 | `pending` | `pending` |
| CLOSED，無正式歷史資料 | `unavailable`，保留歷史活動入口 | 已授權者可辨識尚無正式結果 |
| CLOSED，已發布 | `settled`。每題勝組、各組答案與名次 | `settled`。每題勝組、本組答案與名次 |

已發布每題新增 `display_number`、`no_winner`、`winner_items`，教師的 `groups[]` 及學生的 `own` 各可含 `items`。每 item 僅 `item_id`、`subitem_label`、`answer_text`。單題保留現有字串摘要，題組保留既有摘要表示，前端優先使用逐小題欄位。替代 provider 沒提供新欄位時沿用舊投影；沒有勝組時空 items、空勝組值並明確標示。學生從不收到教師版 groups，公開 DTO 不帶來源格位、內部 group_id、操作識別或受理序列。

課堂歷史沿用 `GET /classrooms/{classroom_id}/results`，列出可查的同堂 CLOSED 活動與可用狀態。依 D22，課堂 OPEN 時，後端以有效的同堂學生資格及組別篩選歷史和單一活動結果，包含該場結束後才加入者；若本組在該場沒有答案，`own` 為 null。課堂 CLOSED 時沿用 D16 的原課堂瀏覽器證明及既有恢復入口。兩個查詢入口都核對課堂、活動與 D06 投影，請求不能自行指定查閱組別。前端拒絕將切換前的非同步結果寫進新活動。

## 001 回填快照

沿用 [001 interfaces](../../001-guided-notes/contracts/interfaces.md) 的 v1。根欄位是 `contract_version, activity_id, import_id, import_version, result_version, ended, units`，其中 `contract_version` 必須是整數 `1`。每題 unit 是 `question_id, winner_group_id, no_winner, answers`，答案是 `item_id, blank_id, answer_text`。有勝組時 group ID 轉為不透明字串，所有 items 均取自同一筆有效提交。無勝組時 group 為 null、answers 為空。空格識別來自既有固定題目，答案保存原字串。

發布前，以活動保存的教師與 `import_id`、`import_version`，讀取 001 既有 `notes.repository.catalog_row` 對應的完整歷史 Catalog DTO，傳給 `notes.models.validate_snapshot`。清單即使已從工作區移除，歷史版本仍應可讀。不得改讀目前啟用的清單、新版本或重新向 Google 取資料替代固定版本。歷史版本缺失或驗證失敗時不得發布快照，待辦保留供查修。001 仍用既有預覽、確認、寫入與讀回流程。
