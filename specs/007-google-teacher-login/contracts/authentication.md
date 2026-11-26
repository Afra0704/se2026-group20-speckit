# 007 Web 登入與角色入口契約（計畫）

適用 Google 正式模式；瀏覽器用表單與 303 redirect，API 用 JSON。所有寫入有既有 CSRF 驗證；callback 為外部 GET，改用一次性 state＋browser＋nonce/PKCE，不豁免其他路由的 CSRF。

## 路由

| 路由 | 行為 |
| --- | --- |
| GET `/` | 200，僅老師／學生入口；不因選老師建立資格。 |
| GET `/student` | 200，原課堂／legacy 學生模板；加入 endpoints 不變。 |
| GET `/teacher` | 有教師資格才 render 原管理頁；未登入 303 `/teacher/login`。 |
| GET `/teacher/login` | Google 登入按鈕、CSRF、可理解錯誤；已有有效教師 303 `/teacher`。 |
| POST `/auth/google/start` | CSRF，建立 login attempt，303 Google；body 不接受 teacher_id/email/sub/任意 redirect。 |
| GET `/auth/google/callback` | 單一固定 callback，purpose 從已驗 attempt 取，不信 query purpose。成功／失敗都導向乾淨本地 URL，不 render token。 |
| GET `/teacher/session` | 200，安全登入狀態，無須登入即可查 authenticated=false。 |
| POST `/teacher/session/logout` | CSRF，取消該 browser pending 流程、撤本 browser 教師資格；API 204，HTML 303 `/`。未登入亦可取消 pending。 |
| POST `/teacher/session` | 正式 Google 模式 410 PASSWORD_LOGIN_DISABLED，不接受本地密碼 fallback。 |

切換帳號由已登入頁的明確表單 POST `/auth/google/start`，body 可有 `switch=true`；使用 Google select_account 提示，舊教師直到成功 finalize 前仍有效。沒有可讓前端指定「登入成某 teacher_id」的欄位。GET 開頁／切換身分連結不能授權；API 本身維持 401/403，不 redirect Google HTML。

GET session 範例：

```json
{"authenticated":true,"teacher":{"display_name":"測試老師","email":"teacher@example.test"},"sheets":{"status":"not_connected"}}
```

未登入為 `{"authenticated":false,"teacher":null,"sheets":null}`。不輸出 teacher subject、client、grant、token、密文、nonce、verifier 或 key。顯示名稱／email 可 null，前端純文字 fallback。

## Callback 與信任邊界

1. `state` 必須唯一且非空，code 或 error 不得同時存在；重複參數、無 state／browser、過期、終態／processing、purpose/client/URI/instance 錯誤都拒絕。原子 pending→processing，claim owner 及期限固定。
2. reconstruct Flow 時還原原 verifier、state、固定 Web client/redirect_uri；Google HTTPS token endpoint 固定，不信 query 帶入 endpoint。外網不持 DB write transaction，交換／驗證有 timeout。
3. Google ID token 經官方 verifier 驗簽章、audience=此 Web client、iss、iat/exp；應用另驗 nonce、非空 sub，azp 若存在須此 client。接受的 issuer 驗後 canonical 化。email_verified 是顯示資料，永不以 email 認領既有教師。
4. finalize 再驗 browser epoch、claim、expected grant、active 與唯一身分，在短交易原子建／取 teacher＋identity＋原 grant。取消／失敗不撤原有效教師。callback 被 claim 後登出／停用／切換，要在 finalize 拒絕。
5. 期限 300 秒；同 browser 的新互動流程 supersede 舊流程，不同 browser 不互相取消。timeout／invalid code 要重新開始，不把 attempt 改回 pending。
6. 結果僅 303 到固定 `/teacher`、`/teacher/login` 或發起時 allowlisted notes 返回頁；不接受任意 next／外站 URL。callback 不附第三方資源，Cache-Control:no-store、Referrer-Policy:no-referrer。

原 grant 有效性受 server browser pointer 約束；不能只刪 cookie。晚到 Set-Cookie 恢復的舊 grant 在 require_teacher 必須失效。logout 不清空整個 session，不刪學生 grants/proof，不登出 Google 本身，不撤 Google project grant。

## 錯誤與畫面

| 服務層 HTTP／code | 情境／提示 |
| --- | --- |
| 503 GOOGLE_NOT_CONFIGURED | Web client/固定 URI 未設定；提示管理者完成設定，學生入口仍可用。 |
| 400 GOOGLE_FLOW_INVALID | state/browser/code/nonce/token 不合法；提示重新開始，不回 raw provider payload。 |
| 410 GOOGLE_FLOW_EXPIRED | 過期；提示重新登入。 |
| 409 GOOGLE_FLOW_SUPERSEDED | 新流程／登出／切換已使本次失效；不覆蓋目前身分。 |
| 400 GOOGLE_LOGIN_CANCELLED | 使用者拒絕／取消；可重試，原有效教師保留。 |
| 503 GOOGLE_UNAVAILABLE | 外部 timeout／服務問題；稍後再試，無半帳號。 |
| 403 TEACHER_DISABLED | 已停用；不可重建繞過。 |
| 401 AUTH_REQUIRED / 403 FORBIDDEN | 原後端權限語意保持。 |
| 410 PASSWORD_LOGIN_DISABLED | 請使用 Google 登入。 |

表中是 service/API 映射；callback 的瀏覽器回應為乾淨 URL 的 303＋安全訊息代碼，不混用 200 假成功。notes 的既有巢狀 error envelope 保留，錯誤翻譯由其路由處理。

## 設定與可替換服務

- `GUIDED_NOTES_GOOGLE_WEB_CLIENT_SECRETS`：repo 外只接受 `web` JSON，驗必要 endpoint 與 redirect；禁止把 installed 改名混用。
- `GUIDED_NOTES_GOOGLE_REDIRECT_URI`：固定 `http://127.0.0.1:5000/auth/google/callback`。
- `GUIDED_NOTES_PUBLIC_ORIGIN`：固定 `http://127.0.0.1:5000`，不要從未信任 Host／forwarded header 推導。
- `GUIDED_NOTES_GOOGLE_TOKEN_KEY_FILE`：repo 外持久 Fernet key；不等同 SECRET_KEY，不自動換 key。
- Google 模式為正式預設；`TEACHER_AUTH_MODE=test_password` 只可由 TESTING fixture 指定，非 testing 啟用須拒絕啟動。
- Provider 邊界規劃：`authorization_request(attempt)`、`exchange_and_verify(attempt, code)` 回已驗身分及必要的 token bundle，永不直接當作前端傳來的 claims。測試可注入外部替代端，但仍走 attempt/state/nonce/grant 整合流程。

## 日誌／Cookie

Flask cookie 維持 HttpOnly、SameSite=Lax，本機 HTTP Secure=false，正式 HTTPS=true。cookie 簽名不保密，不放 OAuth 秘密。OAuth/callback/教師敏感頁 no-store。新增 Werkzeug logging filter，在送出 handler 前遮 callback query，包含 code/state/error_description；exceptions、HTTP debug、header/body 不直接記錄 token/client_secret。測試捕捉日誌，明確放 sentinel 確認不外洩。不要開 Flask debug。
