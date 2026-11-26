# 007 本人 Google Sheets 授權契約（計畫）

本輪只保留貼 Sheets 連結的能力，不含 Drive 選檔。登入身分、Sheets 授權、某檔實際存取權分開判定。

## 路由與 UI

| 路由 | 契約 |
| --- | --- |
| POST `/teacher/google/sheets/connect` | 需有效教師＋CSRF，server 記錄 expected teacher/grant/sub 及 purpose=sheets，303 Google。可接受固定 allowlist 返回位置，不接受任意 URL。 |
| GET `/auth/google/callback` | 沿用登入 callback 驗證，另要求 sub 與目前教師相同、原 grant/epoch 仍有效、實際 spreadsheets scope 與可持續 refresh credential 齊。 |
| GET `/teacher/google/sheets/status` | 需教師，僅回 not_connected/connected/reauth_required/unavailable 與安全提示，不回 subject/client/token 或私有檔路徑。 |

連接／重連按鈕放教師管理頁與 notes 頁；未連接不阻止管理課程，只停用講義讀寫並說明原因。connect 可用 login_hint 幫助選帳號，但它不能替代 callback 同 sub 核對。錯帳號不把教師切換，也不認領其他 Google 授權。

## Scope 與保存

使用同一 Web client，要求 openid/email/profile 及 `https://www.googleapis.com/auth/spreadsheets`，access_type=offline、include_granted_scopes=true；首次／失效重連可 prompt=consent。不請 Drive 全權、不啟用 Picker。

以實際 token response/granted_scopes 確認 spreadsheets；不能拿 requested scopes 假裝已同意。無法確認時明確失敗，scope 缺漏不標 connected。Google 對 email/profile scope 的等價名稱由 provider 正規化，Sheets scope 仍需確實存在。

SDK scope-change warning 必須在 provider 局部處理並保留實際授予集合，不能直接誤報 Google 故障，也不能全域放寬後假裝所有 scope 已取得。只接受由固定 HTTPS 交換取得的已解析 token，仍完整驗 ID token／nonce／owner；沒有可確認 scope 時 fail closed。相關本機 source 差異見 research R2。

credential 與 instance UUID、teacher、canonical issuer/sub、Web client 完整綁定，token/refresh/expiry/scope 存 Fernet 密文 BLOB。新 grant 無 refresh token時，只保留同 owner/client/instance 的舊有效 refresh；不存在就提示重新同意。沒有 Desktop token／全域 profile fallback。新 DB 即使 teacher_id=1 也不能使用舊 token。

## 內部介面

- `get_google_identity(TeacherContext)`（實作由 repository.identity 搭 require_teacher／active 檢查組合）：查已驗映射與 active，沒有則拒絕；不改 TeacherContext 形狀。
- `sheets_authorization_status(TeacherContext)`（實作名 sheets_service.authorization_status）：核對 owner/instance/client/密文是否可讀，僅返回狀態，不為查狀態自動開始 OAuth 或刷新網路。
- `get_teacher_sheets_credentials(TeacherContext)`（實作名 sheets_service.credentials）：先 require_teacher 與 context 相同，再查本人 credential／解密綁定，必要時只經 sheets_service 顯式刷新；回傳不可自行刷新的 access-token 快照供 SheetsGateway 使用，完整 refresh credential 不傳給傳輸或瀏覽器。
- `notes.gateway(teacher)`：測試替代端只在 TESTING 明確注入；正式 Google 模式只走上者，不使用 NOTES_GOOGLE_TEACHER_ID／NOTES_GOOGLE_TOKEN／Desktop authorize 作 fallback。
- 原 SheetsGateway、parse_sheets_url、預覽確認與回填的外部介面不改；僅新增本地快照送出前拒絕的狹窄例外映射，保留原寫後回讀／未知狀態語意。notes.index configured 改成本人 status，移除要求 Web 使用者跑 Desktop CLI 的提示。

## I1：傳輸不得隱性刷新或 replay

`google_login/transport.py` 提供最小 Google Credentials 相容快照，僅帶 access token／真實 expiry／必要 scopes，不帶 refresh token、client secret 或 refresh handler。valid/expired 隨時間重新判定；before_request 只能驗時效／目前資格並 apply header，refresh 一律拒絕且不得發網路請求，不能用 expiry=None 偽裝永不過期。

build_google_service 只接此快照；保留既有 AuthorizedHttp 的 refresh_status_codes=()、max_refresh_attempts=0 及 execute(num_retries=0)。這些傳輸旗標只處理回應後刷新，不能代替 before_request 的快照限制。

快照於取得後、HTTP 送出前變成不可用時，專用 CredentialSnapshotExpired 例外在 SheetsGateway 內轉成 GOOGLE_CREDENTIALS_REFRESH_REQUIRED；該次 HTTP 計數為零，寫入分類為 failed（未送出），不是 unknown。這是唯一新增的狹窄本地例外保留，不以一般 Exception 推斷未送出。傳輸收到真正 401 時維持原重連提示，不刷新／重送。後續重試必須重新進入 service，寫入仍遵循原 idempotency、部分成功、回讀與恢復流程，不自動 replay 已成功或未知的單元。

## 失敗／競態

| HTTP/code | 行為 |
| --- | --- |
| 409 SHEETS_CONNECT_REQUIRED | 登入有效但未連接，顯示連接按鈕。 |
| 409 SHEETS_REAUTH_REQUIRED | refresh 失效／被撤／期限已到，教師仍登入，提示重連。 |
| 409 GOOGLE_ACCOUNT_MISMATCH | connect 回另一 sub，拒絕；保留原有效 credential。 |
| 403 SHEETS_SCOPE_REQUIRED | 未取得 scope，提示需授權；不破壞原有效 credential。 |
| 503 GOOGLE_CREDENTIALS_UNAVAILABLE | key／密文／client/instance 歸屬錯誤，fail closed，不自動換 key或借 token。 |
| 503 GOOGLE_REFRESH_BUSY | lease 被占用，Retry-After:1，前端可重試，不顯示已授權失效。 |
| 503 GOOGLE_REFRESH_TIMEOUT | 刷新網路逾時或超過 20 秒結果接受期限，Retry-After:1；保留原狀態與密文，只釋放仍屬自己的 lease，不誤報必須重連。 |
| 503 GOOGLE_CREDENTIALS_REFRESH_REQUIRED | 傳輸快照送出前失效，HTTP 尚未送出；提示透過原操作／恢復流程重試，以重新進入顯式刷新服務，不自動重送寫入。 |
| 403 SOURCE_READ_FORBIDDEN | 本人連接有效但來源未共用／不可編輯，沿用來源權限提示。 |

一切錯誤經 notes 原 envelope 翻譯，不回完整 Google message／credential。登入 callback 錯誤與 Sheets 權限錯誤不混淆。

## I2：刷新時間預算與清理

- lease 固定 30 秒（持久 UTC），claim 成功後建立 monotonic 20 秒結果接受 deadline。整個 refresh，包括必要的新 ID-token 憑證取得／驗證，都共用這個預算，不在各子步驟重新起算。
- 最多一次 token POST（自動重試次數 0）、必要時最多一次憑證 GET；兩者只用固定端點，不跟隨 HTTP redirect。明確停用／攔截 SDK、HTTP adapter、服務層的額外呼叫及 backoff，不依賴 SDK 預設；不呼叫私有 SDK 函式或全域放寬旗標來達成。
- 每個網路步驟前檢查剩餘預算，connect/read 個別上限仍為 3/10 秒，且依剩餘預算縮短；傳輸不得在剩餘預算不足時再開始。回應返回、驗證後、DB finalize 前再驗 deadline。20 秒是結果能否被接受／提交的期限，不保證 Python 能硬中斷所有已阻塞 I/O；晚回結果必須丟棄，不能使用或保存。
- timeout／deadline／暫時性網路錯誤時不做同次重試；只有 credential_id/revision/lease_id 都仍相同時才釋放自己的 lease，清理不修改 credential 狀態／revision／密文，不碰新 connect。過期 lease 可由下一請求安全重新 claim；後續 retry 是新的服務呼叫，不是自動重送 Sheets 寫入。
- final CAS 重查 owner/client/instance、目前教師資格、generation/revision/lease 且尚在期限；新 connect 使舊結果失效。期限內明確 invalid_grant 才可 CAS 清密文／revision++／reauth_required；timeout 不得當 invalid_grant。刷新無新 ID token 時依原綁定，有新者驗簽章/iss/aud/exp/sub，不要求新 login nonce。

登入／connect 的 code exchange 仍用其 300 秒 attempt 期限及有界網路 timeout，不套用 refresh lease；兩種 purpose 均不得重送已消耗的 code。

一般 logout 不呼叫 Google revoke，保留該教師本人已連接資料供下次登入；後續 request 必查新 grant。已送往 Google 的外部寫入不能藉登出取消，沿用寫後回讀／未知狀態恢復，不承諾跨系統原子撤銷。
