# 007 資料模型（007 新 DB 已建表）

沿用 SQLite、teachers、grants 與所有課堂／notes 表，新增資料都由同一 request connection／短交易處理。以下契約已落於 google_login/schema.sql 與本輪空白 DB；沒有遷移舊 DB。

## 1. auth_instance

| 欄位 | 限制 |
| --- | --- |
| singleton | INTEGER PK，只可為 1。 |
| instance_uuid | TEXT UNIQUE NOT NULL，隨新空白 DB 產生一次。 |
| created_at | UTC 時間。 |

重跑 init-db 保留 UUID；新 DB 產生不同值。Google 模式不得對既有業務 DB 自動補 instance 並認領舊資料，應要求本輪新 DB。instance UUID 不是密鑰，但綁定密文有效範圍。

## 2. teachers（既有）與 google_identities（新增）

teachers.id、active 維持；新 DB schema 中 username/password_hash 改為可 NULL，Google 教師均為 NULL，不產生可登入的本地密碼。舊 test_password fixture 可明確填值。

| google_identities 欄位 | 限制 |
| --- | --- |
| teacher_id | PK/FK teachers.id，一教師一個 Google 身分，本輪不做換綁。 |
| issuer | 固定 canonical `https://accounts.google.com`。 |
| subject | 經驗證的 sub，非空字串，與 issuer 複合 UNIQUE。 |
| display_name / email | 可空，顯示資料，永不作所有權／自動合併依據。 |
| email_verified | boolean 顯示中繼資料，不取代 sub。 |
| created_at / updated_at | UTC。 |

Google 接受的兩種 issuer 在驗證後 normalize；teacher.active=0 時拒絕登入，不能因重試新建另個教師。同一 sub 的並行首次登入，以同一 BEGIN IMMEDIATE 內查／建 teacher＋identity＋grant，唯一限制為最後防線，重試仍使用原 teacher；任一步失敗全回滾。

## 3. auth_browsers

| 欄位 | 限制 |
| --- | --- |
| binding_hash | PK，cookie 內高熵 opaque auth_browser 的 SHA256。 |
| epoch | 非負整數，由互動流程開始／完成／登出遞增。 |
| teacher_grant_hash | 可空，FK grants.token，刪 grant 時 SET NULL。 |
| created_at / expires_at | 存活期限；不早於所關聯有效 grant，過期一律拒絕。 |

cookie 只放 opaque browser binding 與既有 teacher_grant，不放 nonce/verifier/token。Google require_teacher 必須同時符合原 grant 有效、teacher active、identity 存在、browser 未過期且 server current grant == 此 cookie grant 的 hash。晚到 cookie 即使簽章有效也不能復活已撤資格。

互動 last-start-wins 僅限同 browser；不同 browser 可登入同一教師並各自登出。登出保留 browser binding，但 epoch++、刪目前教師 grant／清 server pointer，保留學生相關 session/proof。若 legacy session['grant'] 是教師 alias 才移除，不誤刪學生 alias。

## 4. google_oauth_attempts

| 欄位 | 限制 |
| --- | --- |
| attempt_id | UUID PK。 |
| state_hash | UNIQUE NOT NULL，raw state 不保存。 |
| browser_hash / browser_epoch | 綁發起者與當次世代。 |
| purpose | login 或 sheets，僅 server 儲存值決定 callback 行為。 |
| expected_teacher_id / expected_grant_hash | login 可空；sheets 必須為發起時教師與 grant。 |
| client_id / redirect_uri / instance_uuid | 固定設定與本 DB，finalize 再核對。 |
| secret_blob | pending/processing 必為 Fernet BLOB，含 nonce、PKCE verifier 與 attempt/purpose/instance/browser/epoch/client 綁定；終態清除為 NULL。 |
| status | pending / processing / succeeded / failed / expired / superseded。 |
| claim_id | processing 時的高熵 claim owner，用於 finalize CAS。 |
| created_at / expires_at / consumed_at | expires_at=建立後 300 秒；finalize 前仍需未過期。 |

狀態：pending → processing → succeeded/failed；未 claim 可過期或被新流程 supersede；processing 遇 logout／換場，finalize 因 epoch 不符而失敗。終態不可回 pending。callback 在交換 code 前原子 claim，平行／重放僅一個可繼續。網路 timeout 後須新流程，不重用原 attempt。

finalize 必驗 claim_id、epoch、原 expected grant pointer、instance/client/URI；sheets 還驗有效 teacher grant 與同 sub。login 原資格若自然到期可重新登入，但 pointer／epoch 必未被別的登入／登出改動；禁止把「原資格仍有效」當成重新登入過期 session 的前提。

## 5. google_sheets_credentials

| 欄位 | 限制 |
| --- | --- |
| teacher_id | PK/FK google_identities.teacher_id，每位教師一組目前 credential。 |
| instance_uuid / issuer / subject / client_id | NOT NULL，與目前 DB、教師映射、Web client 同值。 |
| credential_id | UUID UNIQUE，每次重新連接使用新 generation。 |
| revision | 正整數，connect／refresh 成功或狀態變更時增加。 |
| status | connected / reauth_required。 |
| granted_scopes / expires_at | 實際授予的 scope 與 access-token 期限；非純 requested scopes。 |
| secret_blob | connected 時必為 Fernet BLOB，含 token／refresh／expiry／scope 及上述 owner/generation/revision；reauth_required 可 NULL。 |
| refresh_lease_id / lease_until | 可空；30 秒 lease，不持有交易跨網路。 |
| created_at / updated_at | UTC。 |

`connected` 表示本人 scope 與可持續刷新 credential 齊，不表示某份試算表一定有編輯權。沒有列表示尚未連接。

Fernet key 在 repo 外持久 keyfile，與 SECRET_KEY 分開，不因 Flask session key 變動而重建。key 缺漏／不合法／解密失敗明確不可用，不能靜默重設。DB 密文外欄與 envelope 必逐項相同；拷貝另一教師／client／instance 的密文拒絕。只在需要外呼時解密，不回傳給瀏覽器；token 本體／nonce 等不得進日誌。

### 連接與 refresh 原子性

- connect 先完成 Google 驗證，再在短交易重檢 teacher/browse grant/epoch，以同一 Google sub 寫入完整密文及 metadata。取消／錯帳號／scope 缺少／交換失敗不覆蓋原 connected。
- 新 response 無 refresh token 時，只能保留本 DB 同 teacher/issuer/sub/client、已可解密且未標失效的舊 refresh token；完全沒有時拒絕標 connected，提示重新同意。
- refresh 先 claim `(credential_id,revision,lease_id)`，結束交易後外呼；逾時／重試有界。其他請求遇有效 lease 回可重試 busy，不自行並發 refresh。
- 本次 claim 後的結果接受期限以 monotonic 計時 20 秒，包含 token POST 與必要的新 ID-token 憑證取得／驗證。每次最多一次 token POST、最多一次必要憑證 GET；不做 SDK、HTTP adapter 或服務內重試。持久 lease 仍是 UTC 30 秒；兩種時鐘各自檢查，CAS 前必須仍在兩者期限內。網路晚回即使尚有有效 lease 也不提交，反之亦同。
- timeout／20 秒期限已到／暫時性網路錯誤時，只以 credential_id/revision/lease_id CAS 釋放自己持有的 lease，不增加 revision、不改 connected/reauth_required、不改密文／expiry。若已有新 connect 或 lease owner，清理不得碰新列；之後的新請求重讀目前列並重新 claim，不在同一次呼叫內重送。
- network 成功或 invalid_grant 後，都只能在原 generation/revision/lease 尚相同時 CAS。新 connect 會更換 credential_id／增加 revision，舊 refresh 結果整個丟棄，不能把新連接標失效。
- invalid_grant 的 CAS 同時清除失效 secret_blob 並增加 revision，狀態回 reauth_required；不留下 revision 與密文 envelope 不一致的 connected 列。lease CAS 另要求尚未到期。
- refresh 沒回新 ID token 時依原已驗 refresh 綁定，不使用過期 ID token 重驗；若有新 ID token，驗簽章／iss/aud/exp/sub，OAuth refresh 不要求新 login nonce。
- 教師登出後，不允許該 request 完成新的授權操作／提交；已送往 Google 的外部寫入不能撤回。已持久存的本人 Sheets 連接可以留待下次登入，不在一般 logout 執行 project revoke。

## 傳輸用憑證快照（記憶體物件，不新增資料表）

由 get_teacher_sheets_credentials（實作名 sheets_service.credentials）在本人驗證及必要的顯式刷新完成後產生，僅含當次 access token、真實 expiry、必要 scopes 及受控資格檢查；不含 refresh_token、client_secret 或 refresh_handler。不得將 expiry 設為 None 來假裝永不過期。

valid/expired 每次依目前時間檢查；before_request 只核對當前資格／時效及套用 Bearer header，不做網路。refresh 明確拒絕，SDK 不可繞過服務的 lease/revision/owner。送出前過期以專用本地例外標示未送出；已送出的錯誤仍沿用原寫入／回讀分類，不能自動刷新後 replay。

## 6. 保持不變

TeacherContext(teacher_id)、issue_grant、課程／課堂／分組／活動 FK、CatalogDTO v1、Display v1、ResultSnapshot v1、Submission、questions.content 及回填識別不增加 Google/token 欄位。角色選擇只導覽，不發 grant。

資料保留：本次 plan 不建／刪 DB；實作指定新的 007 DB，原 005 檔與 Google client/token 原樣保留。新 DB 仍重跑 init-db 保留本版資料；不是每次啟動都重置。
