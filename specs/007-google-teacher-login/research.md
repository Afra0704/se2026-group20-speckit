# Phase 0 Research：007 教師 Google 登入

2026-11-25（Asia/Taipei）。本機唯讀檢查，兩研究代理交叉核對；Google 功能只參考官方，套件參考其官方文件／原始碼。未讀憑證內容、未進行真實 OAuth、未改套件或 DB。

## R1 — Web code＋OIDC，分開兩個 purpose

**Decision**：server Authorization Code＋OIDC，同 Web client/fixed callback，login 只請 openid/email/profile、顯式 online；Sheets 另同意。

**Rationale**：沿用 Flask/Google SDK，按功能取得權限。[Web server](https://developers.google.com/identity/protocols/oauth2/web-server)、[granular permissions](https://developers.google.com/identity/protocols/oauth2/resources/granular-permissions)。

**Alternatives considered**：GIS JS 是官方登入按鈕方案，但多前端第三方 callback；Authlib 新增框架而現有 SDK 足夠；Desktop local-server flow 不作 Web 登入，也不用舊 Google Sign-In JS。

## R2 — 本機相容性與 SDK 預設

| 已安裝 | 版本 | 核對 |
| --- | --- | --- |
| Python / Flask | 3.13.1 / 3.1.3 | 目前專案環境。 |
| google-auth | 2.63.1 | verifier 可匯入，需顯式 audience；不自動驗 nonce。 |
| google-auth-oauthlib | 1.5.0 | Flow 跨 request 還原原 verifier；支援 S256。authorization_url 預設 offline，login 必覆寫。 |
| requests-oauthlib / oauthlib | 2.0.0 / 4.0.1 | 現有 code exchange 依賴。 |
| google-api-python-client | 2.202.0 | 沿用現有 SheetsGateway。 |
| cryptography | 50.0.2 | uv.lock/.venv 已有，Fernet 可匯入。 |

**Decision**：Google 套件沿用，crypto 改直接依賴 `>=50.0.2,<51`，實作時鎖定，不因 latest 文件就升級。

**Rationale**：實查函式簽名與套件 source，避免以 SDK 當作已包含 browser/nonce 驗證。[Flow](https://googleapis.dev/python/google-auth-oauthlib/latest/reference/google_auth_oauthlib.flow.html)、[ID token verifier](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.id_token.html)。

**Alternatives considered**：只 decode JWT 或自己做驗簽不可用；另加登入框架不必要。這些是 import／metadata／source 檢查，不是真實 Google callback 測試。

**Scope 差異核對**：本機 oauthlib 4.0.1 在實際 scope 與 requested 不同時會拋帶 token 的 Warning，Google 的額外舊授權、別名或部分同意都可能觸發。provider 須只在固定 HTTPS token exchange 的已解析 response 上處理此結構化 scope-change warning，保留實際 scope/token，接續完整 ID-token 驗證與應用 required-scope 判定；不記錄 warning/token，不重送已消耗的 code，不全域設定 OAUTHLIB_RELAX_TOKEN_SCOPE。沒有結構化 token 的其他錯誤照失敗；測試涵蓋額外／缺少／別名／無 scope，尚未以真實 Google 驗證。[oauthlib 官方 source](https://github.com/oauthlib/oauthlib/blob/master/oauthlib/oauth2/rfc6749/parameters.py)。

此 source 的遠端 GitHub 頁本次回 503；上述行為由已安裝 4.0.1 的 validate_token_parameters 原始碼直接核對，不冒稱遠端抓取成功。[Requests-OAuthlib 介面](https://requests-oauthlib.readthedocs.io/en/latest/api.html)另確認 code/token endpoint/timeout 介面。

## R3 — 穩定身分與原 grant

**Decision**：驗證 Google 兩種 issuer 後 canonical 化，唯一 `(issuer,sub)` 對應原 teachers.id；email/name 只顯示，active=0 不重建帳號繞過。

**Rationale**：sub 是穩定使用者識別。[Google OIDC](https://developers.google.com/identity/openid-connect/openid-connect)。TeacherContext/grants 可保持。

**Alternatives considered**：email 合併、第二套資源 owner 都會擴大混淆。新教師無本地密碼，空白新 DB schema 允許 username/password_hash NULL。

## R4 — server attempt 與 browser epoch

**Decision**：state hash/browser/300 秒/nonce/PKCE/一次 claim/finalize；同 browser 最後啟動流程有效。token/verifier 不放 signed cookie；server current grant 拒絕登出後晚到 cookie。

**Rationale**：SDK 不替本案處理 logout 競態，兩段短交易避免外網鎖 DB。Google 支援 S256：[discovery](https://accounts.google.com/.well-known/openid-configuration)。

**Alternatives considered**：僅 cookie state 或僅 ID token 不能涵蓋所有情境。loopback 採先完整驗 state，再 `fetch_token(code=...)`，token endpoint 固定 HTTPS，不全域開 insecure transport。

## R5 — Sheets connect 與 Drive 邊界

**Decision**：已登入者明確 connect，openid/email/profile＋spreadsheets，offline、incremental；同 sub、實際 scope、目前 grant 齊才保存。login 附帶其他 scope 不自動連接。

**Rationale**：保留貼本人可存取連結的讀寫；scope 不限單分頁，也不保證特定檔案有權限。[Sheets scopes](https://developers.google.com/workspace/sheets/api/scopes)。

**Alternatives considered**：drive.file 較窄，但貼網址不會自動授權任意檔案，Picker 是下輪。[Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)。不請 Drive 全權，也不用 service account 代替老師。

## R6 — Fernet BLOB 與 instance 綁定

**Decision**：密文存 DB，keyfile repo 外；密文 envelope 與外欄都含 purpose/instance/teacher/issuer/sub/client，解密逐項比較。錯 key 不自動換新。

**Rationale**：多使用者 server token 應加密。[Google best practices](https://developers.google.com/identity/protocols/oauth2/resources/best-practices)。Fernet 提供認證加密但沒有 AAD，owner envelope 是本案設計。[Fernet 50.0](https://cryptography.io/en/50.0.0/fernet/)。

**Alternatives considered**：純 JSON＋ACL 不選；Credential Locker 多平台接線；token 檔＋DB pointer 需跨檔原子性，故選密文 DB。key 和 DB 同時遭取得時不提供主機失陷防護。

## R7 — refresh、取消、登出

**Decision**：只沿用同 owner/client/instance 的舊有效 refresh；無可用值提示重連。refresh 沒新 ID token 時依既有綁定，不能把過期 ID token 當新證明；有新 ID token 時驗時效及同 sub。lease＋revision CAS，取消／錯帳號／缺 scope 保留原有效連接。

**Rationale**：refresh token 不保證每次回傳，stale network 不能改壞新連接；後者是本案競態設計。logout 只撤本系統 grant，不撤 Google project scopes。[Google revocation](https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke)。

**Alternatives considered**：每次登入都問 Sheets、每次登出 revoke、外網期間持 write lock 均不選。已送出的外部寫入無法用登出撤回。

### I1 修正 — SDK 傳輸只用不可刷新快照

**Decision**：新增 transport.py，給 Sheets SDK 的物件僅有 access token／真實 expiry／scope，不帶 refresh token、client secret 或 handler；before_request 只檢查資格／時效及 apply，refresh 明確拒絕。顯式刷新完全留在 service 的 owner/lease/revision 流程。

**Rationale**：本機 build_google_service 雖設定 401 不刷新／不重送，AuthorizedHttp 仍先呼叫 credentials.before_request；一般 Credentials 會在此自行刷新。設定 refresh_status_codes=() 並不足以關閉這條路徑。[AuthorizedHttp 官方說明](https://googleapis.dev/python/google-auth-httplib2/latest/google_auth_httplib2.html)、[Credentials 官方說明](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.credentials.html)。本機安裝 source 已唯讀核對，尚未做新 adapter 測試。

**Alternatives considered**：把完整 Credentials 傳給 SDK 會留下繞過 CAS 的入口；把 expiry 設 None 會假裝永不過期；在 before_request 偷呼叫刷新 handler 則仍可能於寫入中隱性刷新。均不採。僅新增專用本地送出前例外的最小映射，不改原 Gateway 外部介面或回填語意。

### I2 修正 — 30 秒 lease 與 20 秒結果接受期限

**Decision**：refresh 以 monotonic 共用 20 秒預算，最多一次 token POST／一次必要憑證 GET，自動重試 0；每次網路前依剩餘預算限制 3/10 秒 timeout，網路返回與 CAS 前再驗期限。逾時只 CAS 釋放自己 lease，不改連接狀態或密文，回可重試錯誤；晚回一律丟棄。

**Rationale**：單次 connect/read timeout 不是總預算，現有 Google SDK 的 token request 可能自行 retry/backoff；本案需由 provider 明確控制呼叫次數與接受期限。30 秒持久 lease 預留清理餘裕；20 秒不被宣稱為可硬中斷所有阻塞 I/O 的保證。

**Alternatives considered**：只放大 lease 或套 timeout 不足以約束內建重試；把 timeout 當 invalid_grant 會錯誤清掉仍可用授權。服務與 SDK 都不在同次呼叫重試，使用者之後的新操作須重讀狀態再 claim。

## R8 — Cloud 與本機準備

**Decision**：原 project 另建 Web application client，精確 callback `http://127.0.0.1:5000/auth/google/callback`；web JSON repo 外，保留 Desktop client/token。loopback HTTP 僅本機，部署需 HTTPS，不採 request Host 建 redirect。

**Rationale**：client 類型與 callback 要符合規則；Testing app 加 Sheets scope 後的期限不能套用純登入例外。[OAuth expiration](https://developers.google.com/identity/protocols/oauth2#expiration)。

**Alternatives considered**：改 installed JSON 欄名、混用 localhost/127.0.0.1、沿用未驗證 profile 都不採。實際 Google Console 尚未操作。

## R9 — 舊入口／fixture

**Decision**：正式停用 password POST/CLI；test_password 僅 TESTING fixture，Google fixture 用真實 routes＋受控 provider，不能跳過安全驗證。Google gateway/configured 不再讀全域 Desktop 設定。

**Rationale**：保留既有邊界回歸，同時測新正式入口。此為本機 source 核對後的整合決策。

**Alternatives considered**：刪舊測試、全部假登入、正式預設仍 password 都不採。
