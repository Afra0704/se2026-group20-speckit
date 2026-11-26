# Implementation Plan: 身分首頁與教師 Google 登入

**Date**: 2026-11-25（Asia/Taipei） | **Spec**: [spec.md](spec.md)
**Status**: 007 自動驗證範圍已實作；真實 Google、人工及互審保持待完成。實測見 validation.md，未 commit/push。
**Branch**: 已建立 `codex/007-google-teacher-login`，保留 005/006 未提交修改；起點 commit 見 validation.md。
**Input**: 使用者明確確認可進入 plan，審圖姓名及獨立紀錄未提供；不補寫「同學已核准」。本輪身分首頁＋Google 登入；Drive 選檔下一輪。

## Summary

沿用 Flask/Jinja、SQLite、TeacherContext、grants、課堂及 notes 架構。首頁分老師／學生，學生維持課堂碼＋組別；老師經 Web application client 的 Authorization Code＋OIDC 登入，以驗證後 canonical issuer＋sub 唯一對應教師，姓名／信箱只顯示。

登入只請 openid/email/profile，另以明確的「連接 Google Sheets」取得同一 Google 身分的講義授權。此接線是維持既有貼連結匯入所需，不加入 Drive API／Picker。Google 模式不載入舊 Desktop token 或全域 teacher_id profile。

OAuth attempt 秘密與每教師 Sheets token 用 Fernet 加密後存 SQLite，keyfile 在 repo 外；密文內外綁 instance UUID、教師、Google 身分及 Web client。沿用原 grants；加入 server browser epoch/current grant 防止登出後晚到 callback／cookie 恢復身分。

## Technical Context

**Language/Version**: Python 3.13.1、既有原生 JavaScript。
**Primary Dependencies**: Flask 3.1.3、Jinja、google-auth 2.63.1、google-auth-oauthlib 1.5.0、google-api-python-client 2.202.0。cryptography 50.0.2 已在 uv.lock／.venv，實作時列 direct dependency `>=50.0.2,<51`；不新增登入框架，本階段不改套件。
**Storage**: 新 `instance/classroom-007.sqlite3`；沿用核心表，新增 instance metadata、Google identity、browser、OAuth attempt、加密 Sheets credential。keyfile/Web client JSON 在 repo 外。
**Testing**: pytest 契約／單元／整合／競態、Node 登入 UI 與既有六份前端回歸；兩位真實 Google 教師、教師＋兩學生組人工驗收。替代端不冒稱真實 Google。
**Target Platform**: Windows 本機 `http://127.0.0.1:5000`；部署需 HTTPS，本輪不部署。
**Project Type**: 現有 Web app 擴充，不建立第二個 app／教師權限系統。
**Performance Goals**: 不承諾 Google 選帳號時間；外網 timeout 有界，不在外網期間持 SQLite write lock；沿用一秒輪詢，5 秒同步留真人計時。
**Constraints**: 不存 Google 密碼，token/verifier 不放 cookie/localStorage/日誌；不遷移舊資料、不刪憑證或 Sheets、不新增 Drive 選檔／舊帳號認領／校域限制。
**Scale/Scope**: 本機兩教師與兩學生組；沒有未測公開服務／大班效能保證。

## Constitution Check

| 原則 | 設計前 | Phase 1 後 |
| --- | --- | --- |
| I 共同決策 | D20 使用者確認，OpenSpec 同步及本輪分工未回報。 | 維持待補；設計不表示雙組已採用或可合併，正式採用前補紀錄。 |
| II 圖表優先 | specify 三圖已渲染，使用者允許進 plan；未虛構審查者。 | 按圖展開 epoch／attempt／加密／本人 connect，CLI 重渲染並記錄技術修圖待核對。 |
| III 動態匯入 | 保留辨識與原回填。 | 僅換憑證來源，不改 Catalog/Display/Result DTO、題組或回填格位。 |
| IV 機敏／角色 | 舊數字 ID profile 有重用風險。 | Google 模式禁 fallback，密文綁 owner/instance/client；後端、日誌及越權有測試。 |
| V 自動＋人工 | 005/006 未完成證據獨立。 | 本輪矩陣含失敗／競態／真人，未做不勾，不沿用舊數量冒稱 007 通過。 |
| VI 文件一致 | 保留未提交成果。 | Phase 1 文件齊，tasks/analyze/implement 未執行。 |

設計範圍無需技術例外。OpenSpec 同步、審圖姓名、新介面核對及實際分工均是明列待辦，不冒充已確認，也不因此擅自實作。

## Project Structure

```text
specs/007-google-teacher-login/
  spec.md / plan.md / research.md / data-model.md
  contracts/authentication.md / contracts/sheets-authorization.md
  quickstart.md / diagram-review.md / checklists/requirements.md
diagrams/007-{component,class,sequence}.{puml,png}

src/guided_notes/
  __init__.py / auth.py / config.py / db.py
  google_login/                  # 以下皆規劃檔案，尚未建立程式
    __init__.py / routes.py       # 登入、callback、登出、Sheets connect
    service.py                   # attempt claim/finalize、建帳、原 grants
    provider.py                  # Flow／驗證，可注入受控 provider
    repository.py / schema.sql   # 五類新增持久資料
    crypto.py                    # keyfile＋Fernet owner envelope
    sheets_service.py            # 本人 connect、refresh lease/revision
    transport.py                 # 僅 access token 的不可刷新傳輸快照
    log_redaction.py             # callback query／OAuth secrets 過濾
  activities/schema.sql          # 新 DB 的 Google 教師不用本地帳密
  activities/teacher_routes.py / init_teacher.py
  notes/routes.py                # gateway/configured 改用本人 credential
  notes/google_authorization.py  # 保留獨立 Desktop CLI，不作 Web fallback
  templates/identity/{home,login}.html
  templates/activities/{classroom,student,teacher}.html
  static/identity.js
tests/
  conftest.py                    # 舊回歸明確 test_password，新 Google fixture 分開
  unit/test_google_identity.py / test_google_credentials.py
  unit/test_google_transport.py  # before_request／過期／401 不隱性刷新或重送
  contract/test_google_auth_routes.py / test_google_sheets_auth.py
  integration/test_google_login.py / test_google_auth_races.py
  integration/test_google_notes_integration.py
  identity-ui.test.cjs           # 另保留既有六份前端回歸
```

**Structure Decision**: 沿用 TeacherContext/require_teacher/issue_grant，新增 Google 接入與安全持久層；notes 呼叫本人憑證服務，不另建資源 owner 或學生系統。

## Phase 0：研究結論

見 [research.md](research.md) R1–R9。Web code＋OIDC、sub 映射、server attempt/epoch、分開本人 Sheets 同意、密文 DB、refresh CAS、Cloud 設定及舊 fixture 均有決策與理由，沒有未解技術 NEEDS CLARIFICATION。

## Phase 1：主要資料流

1. **入口**：`/` 僅分身分；`/student` 沿用學生模板及加入端點，更新站內連結。`GET /teacher` 未登入 303 到 `/teacher/login`；受限 API 仍 JSON 401/403，不 redirect Google。
2. **發起**：CSRF 保護 POST，短交易建立／取得 server browser，epoch++，supersede 舊 pending attempts。記錄 state hash、300 秒期限、expected grant、加密 nonce/verifier。尚不撤既有教師，取消／失敗仍保留原身分。
3. **往返**：login purpose 顯式 online；PKCE S256、nonce、固定 client/redirect。callback 先驗 state/browser/期限並原子 claim，結束交易後才外網交換與驗簽章、iss/aud/iat/exp/nonce/sub。loopback 使用 `fetch_token(code=...)`，不全域開 insecure transport；應用必先完整驗 state。
4. **提交**：短交易重查 claim、browser epoch、expected grant、active；以唯一 `(issuer,sub)` 建／取教師，同交易 issue_grant、更新 browser current grant、撤本 browser 舊 grant。任何失敗不留半教師，不影響其他 browser。
5. **登出／權限**：Google 模式 require_teacher 除原 grant/active 外，再核對 browser current grant，晚到舊 cookie 亦拒。登出可取消 pending login，epoch++、清 teacher grant／教師 alias，保留 auth_browser、csrf、student_grant、classroom_grant、proof 及學生儲存。一般登出不呼叫 Google revoke。
6. **Sheets**：已登入者發起另一 purpose，同 callback 驗證且 sub 必為當前教師；scope 與可用 refresh token 齊才加密保存。取消／錯帳號／缺 scope 不覆蓋原有效連接，不切換教師。
7. **notes**：gateway 改取該教師 credential，核對 instance/issuer/sub/client/目前授權；無連接與失效分別提示連接／重連，無 Desktop/global fallback。傳給 build_google_service 的是 transport.py 的不可刷新快照，只帶 access token、實際 expiry 與必要 scope，不含 refresh token/client_secret/refresh_handler；valid/expired 隨時間核對，before_request 只能檢查資格／時效及套用 header，refresh 明確拒絕，不能外呼。保留 AuthorizedHttp 的 401 不刷新／不重送及原 execute(num_retries=0)。SheetsGateway 外部介面、RAW／回讀／恢復不變；僅為辨別本地送出前的快照拒絕，允許加入狹窄例外映射，不把未送出誤標成已送出未知。
8. **refresh**：由 sheets_service 唯一負責，30 秒 lease，claim 後建立 monotonic 20 秒結果接受 deadline；每次最多一次 token POST、如新 ID token 確有需要最多一次憑證 GET，包含兩者的共同預算，不做 SDK／HTTP adapter／服務層內建重試。每次呼叫先扣剩餘預算，connect/read 上限 3/10 秒且受剩餘預算限制；回來後及 CAS 前再次驗 deadline/lease。逾時丟棄結果、僅 CAS 釋放自己的 lease，不改 credential 狀態／revision／密文，回可重試錯誤；只有期限內的明確 invalid_grant 才可標 reauth_required。舊失敗不污染新 connect。20 秒是接受／提交結果的期限，不宣稱能硬中斷已阻塞 I/O，任何晚回結果一律不用。

Fernet BLOB 與 owner metadata 在同一 SQLite 交易，避免額外 token 檔的跨檔原子性。Fernet 無 AAD，密文 envelope 重複包含用途與 owner，解密後逐欄核對。錯 key 不自動重建；signed cookie 不作秘密儲存。

傳輸快照在取得後過期時，送出前以專用本地例外拒絕並回 GOOGLE_CREDENTIALS_REFRESH_REQUIRED，該次不得偷偷刷新或重送。真正已送出的 401 沿用重連提示，沒有自動 replay；已寫入或未知的單元仍走原回讀／恢復，不因取得新 token 重做整筆回填。實作需用時間推進、refresh spy 及 HTTP 計數驗證這條邊界；timeout/budget 規則詳見 Sheets 契約。

## 新 DB、舊入口與 fixture

- 建新 classroom-007.sqlite3，不載入或刪除 005 DB。若 Google 模式遇到已有業務／教師但無 007 metadata 的 DB，拒絕並提示指定新 DB，不偷偷遷移。
- 新 schema 的 teachers.username/password_hash 可 NULL；Google 教師均 NULL，身分在 google_identities。舊 fixture 明確填值；不為 Google 教師產生可用假密碼。
- 正式預設 `TEACHER_AUTH_MODE=google`，移除密碼表單；`POST /teacher/session` 為 410 PASSWORD_LOGIN_DISABLED，init-teacher 正式模式拒絕。
- `test_password` 只允許 TESTING=True，由 fixture 明確配置；正式啟用須啟動失敗，不是產品 fallback。Google fixture 用真實 routes＋受控 provider，不停驗 CSRF/state/nonce/PKCE。
- 除 conftest 外，所有直接 create_app 的舊測試都須檢查是否需要明確模式；不能因正式預設更改而偷改測試預期、略過授權或刪案例。
- Web 不再呼叫 Desktop authorize；獨立 authorize-sheets/inspect-sheet CLI 不自動綁到新教師。notes configured 改查本人授權狀態。

## 驗證與可提供的保證

| 層級 | 必驗範圍 |
| --- | --- |
| 契約／單元 | 唯一身分、email 不合併、停用、URI/client/簽章/aud/iss/exp/nonce、錯 key／密文搬移、scope／refresh 缺漏、日誌無 secrets、快照過期／before_request／401 不刷新或重送、20 秒 deadline／最多一次 token POST。 |
| 整合／競態 | 兩教師首次／再次／並行登入、callback 一次性、last-start-wins、claim 後登出／停用／切換、晚到 cookie、原子回滾、refresh/reconnect CAS、逾時／lease 過期釋放、晚到刷新結果丟棄且不污染新連接。 |
| notes／005／006 | 舊 profile 永不讀、instance ID 重用、本人 connect 後受控匯入／全文／回填、DTO/context／題組／單活動不變。 |
| 真人 | 兩 Google 帳號首次／再次／取消／錯帳號／登出；教師＋兩組學生全文與階段；真實 Sheets 先唯讀，寫回另記錄。 |

登出後新請求與提交邊界須拒絕舊 grant；已交給 Google 的寫入不能撤回，保留回讀／恢復限制。Sheets 失效不登出教師，只有講義功能要求重連。Google Testing 的 token 期限需在驗收前核對，不承諾永久授權。

## 進入 tasks 前待辦

1. 同學核對 epoch/attempt、原 grants 接線、密文與 notes provider、fixture 及修圖差異；姓名／結論如實補。
2. D20 OpenSpec 同步及本輪分工未回報，保持待補，不寫成雙方完成確認。
3. 依 quickstart 準備 Web client、精確 callback、兩位測試帳號與 scopes；本次未操作 Console。
4. tasks 須包含所有自動／真人與失敗競態，之後 analyze 再 implement；005/006 人工狀態不改。


## 實作對照（2026-11-25）

模組責任依三圖落於 google_login/provider.py、service.py、sheets_service.py、crypto.py、transport.py、routes.py 與 log_redaction.py；共用 repository.py 管 schema/instance/identity。登入 UI 以 Jinja 與原生 CSRF 表單工作，不依賴 JavaScript 完成 OAuth；identity.js 只提供純文字顯示工具。原 notes 匯入模板實際是 notes/import.html（原計畫的 index.html 指稱更正），本人授權區放 notes/base.html 供所有教師講義頁共用。attempt 終態清除秘密、開始新流程清理過期秘密；未變更登入或 Sheets 契約。

005/006 人工任務保持原狀，D20 與本輪具名互審未回報；不把本次實作授權當作雙組確認。

## PR #7 初始化一致性補強（2026-11-26）

啟動與init-db共用initialize_application_schema：在同一BEGIN IMMEDIATE內辨識DB相容性、建立基礎／課堂表、Google schema及auth_instance。schema逐statement執行，不以獨立executescript切斷邊界；任何中途失敗回滾該段，新的空白DB可直接重試。既有UUID／教師／課程／密文保留，真正不相容舊DB仍拒絕且不改內容。notes與008 workspace的附加初始化仍各自可重跑／各自交易，不宣稱整個app factory全原子。007時序圖補此交易說明，無新增身分系統或資料遷移。
