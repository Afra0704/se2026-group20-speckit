# Tasks: 身分首頁與教師 Google 登入

**Input**: 本功能 spec.md、plan.md、research.md、data-model.md、contracts/authentication.md、contracts/sheets-authorization.md、quickstart.md 與 diagrams/007-* 三圖。
**Prerequisites**: 設計文件已存在，使用者已明確要求產生 tasks。審圖者姓名、新介面核對、分工與 D20 的 OpenSpec 同步尚未回報，不冒稱已完成；T002 整理待補，T060 記錄實際互審。實作前先執行 speckit-analyze，處理阻擋問題。
**Tests**: spec FR-014、plan 與憲章明確要求自動與人工驗證，因此包含測試任務。先定義預期並確認新增行為未滿足，再實作；受控 OAuth／Sheets 替代端不當作真實授權證據。
**Organization**: 三故事依 US1(P1)→US2(P1)→US3(P2) 組織；共用基礎先完成，同檔修改循序。獨立驗收表示各故事有獨立情境，不代表登入後功能沒有前置依賴。
**Status**: 已執行 007 implement，自動工作逐項附證據於 validation.md；T056/T057/T058/T060 真人與互審保持未完成。實際分支 codex/007-google-teacher-login，新空白 DB 已建，未讀個人憑證、未 commit/push；005/006 原人工狀態不變。

## Format: `[ID] [P?] [Story] Description`

路徑均相對 repo 根目錄；`[P]` 僅表示前置條件完成後可在不同檔案並行，不是另開代理或同時改共享檔的指示。所有結果僅於實際完成後記入 validation.md；人工未做不得勾。

## Phase 1: Setup

**Purpose**: 固定起點與範圍，保留既有成果，不在準備階段破壞資料。

- [X] T001 核對 `.specify/feature.json` 指向 007、實際 Git 分支／commit／工作樹，從保留 005/006 修改的工作樹建立或沿用 `codex/007-google-teacher-login`；在 `specs/007-google-teacher-login/validation.md` 記錄環境、起點、專用 DB 的預定絕對路徑及原人工任務未改，不 reset、不提交現有修改。
- [X] T002 在 `specs/007-google-teacher-login/validation.md` 整理使用者已確認範圍、允許進 plan/tasks 的依據，以及 D20、Google provider／原 grants、notes 憑證接線、修圖與分工的待補核對項；未知姓名／未回報審查保留未知，不重新詢問已確認的 Drive 下一輪及無舊資料遷移決策，也不把此整理當作 T060 已審。
- [X] T003 依 plan/research R2 在 `pyproject.toml` 明列 `cryptography>=50.0.2,<51`，更新 `uv.lock` 並同步 `.venv`，核對現有 Python 3.13 與 Google 套件相容性，在 `specs/007-google-teacher-login/validation.md` 記錄實際版本／命令；不順便升級未必要套件或新增登入框架。
- [X] T004 核對 `.gitignore`、`.env.example` 及 `specs/007-google-teacher-login/quickstart.md` 的私有檔邊界，準備僅含佔位值的 Web client／keyfile／固定 origin／callback 設定說明；DB 預定 `instance/classroom-007.sqlite3`，不覆蓋 Desktop JSON/token、不建立真實 key、不刪 005 DB 或雲端講義。

## Phase 2: Foundational

**Purpose**: 共用設定、加密、instance 與 browser/attempt 支援所有故事；不提前宣稱 Google 登入可用。

- [X] T005 在 `tests/unit/test_google_configuration.py`、`tests/unit/test_google_credentials.py` 與 `tests/integration/test_google_schema.py` 先定義 Web/installed 拒絕、固定 origin/URI/endpoints、key 缺少／錯誤、密文用途／owner 錯配、新空白 DB／舊 DB guard／重跑 init 的預期；使用臨時檔與 DB，不讀真實憑證。
- [X] T006 在 `src/guided_notes/config.py` 與 `src/guided_notes/google_login/provider.py` 建立設定驗證：只接受 repo 外 `web` client JSON、固定 Google HTTPS endpoints、精確 `http://127.0.0.1:5000/auth/google/callback` 及同 origin，不從不可信 Host/forwarded header 推導；設定未完成不阻止學生首頁，登入時明確 GOOGLE_NOT_CONFIGURED，正式入口預設切換留 T029。
- [X] T007 在 `src/guided_notes/google_login/schema.sql`、`repository.py`、`src/guided_notes/db.py` 實作 auth_instance，逐項落實 singleton「INTEGER PK，只可為 1。」、instance_uuid「TEXT UNIQUE NOT NULL，隨新空白 DB 產生一次。」、created_at「UTC 時間。」；先 guard 既有業務／教師且無 metadata 的 DB，拒絕偷偷遷移，再初始化新 DB，重跑 init 保留 UUID／資料並完成 T005 schema 測試。
- [X] T008 在 `src/guided_notes/google_login/crypto.py` 完成 Fernet 與 repo 外持久 keyfile，依 T005 測試保證不把 SECRET_KEY 當加密 key、不自動換 key；密文 envelope 的 purpose/instance/owner/client/generation 等與外欄及當前身分逐項核對，錯 key／竄改／搬移 fail closed，不把原文或解密錯誤內容印入日誌。
- [X] T009 在 `src/guided_notes/google_login/schema.sql` 定義 auth_browsers 與 google_oauth_attempts：browser binding_hash「PK，cookie 內高熵 opaque auth_browser 的 SHA256。」、epoch「非負整數，由互動流程開始／完成／登出遞增。」、teacher_grant_hash「可空，FK grants.token，刪 grant 時 SET NULL。」、created_at/expires_at「存活期限；不早於所關聯有效 grant，過期一律拒絕。」；attempt_id「UUID PK。」、state_hash「UNIQUE NOT NULL，raw state 不保存。」、purpose「login 或 sheets，僅 server 儲存值決定 callback 行為。」、expected teacher/grant「login 可空；sheets 必須為發起時教師與 grant。」、status「pending / processing / succeeded / failed / expired / superseded。」、claim_id「processing 時的高熵 claim owner，用於 finalize CAS。」與期限「expires_at=建立後 300 秒；finalize 前仍需未過期。」；browser_hash/browser_epoch「綁發起者與當次世代。」、client_id/redirect_uri/instance_uuid「固定設定與本 DB，finalize 再核對。」、secret_blob「Fernet BLOB，含 nonce、PKCE verifier 與 attempt/purpose/instance/browser/epoch/client 綁定。」，新增結構／constraint 測試至 `tests/integration/test_google_schema.py`，不保存 raw state/code。
- [X] T010 在 `src/guided_notes/google_login/repository.py` 與 `service.py` 實作 browser 建立／延續、epoch 遞增、pending supersede、一次 claim 與終態更新，遵守 pending→processing→succeeded/failed、expired/superseded 不回 pending；交易不跨外網，使用 claim_id/epoch/expected grant/期限 CAS，於 `tests/integration/test_google_auth_races.py` 先測同一 claim、過期及最後開始有效。
- [X] T011 在 `src/guided_notes/google_login/__init__.py` 建立 Blueprint／共用錯誤介面與可注入 provider 邊界，沿用 `src/guided_notes/auth.py` 的 TeacherContext/issue_grant；預留 Google require_teacher 所需 server browser/current grant 核對，具體身分映射接 T023/T026，不能另建第二套教師或學生授權。
- [X] T012 在 `tests/conftest.py` 及各直接 create_app 的回歸案例中，準備明確 `test_password` 舊模式與獨立 Google fixture；Google 使用臨時 instance/key/client、可控時鐘及 OAuth/Sheets 替代端，安全登入測試走真實 routes／state/nonce/PKCE；驗證配置規劃於 `tests/unit/test_google_configuration.py`，不得全域略過安全檢查，執行本階段測試並記錄於 `specs/007-google-teacher-login/validation.md`。

**Checkpoint**: 共用基礎測試通過。Google 登入、登出與 Sheets connect 仍待故事實作；只有 fixture 需要既有教師前提時可明確 seed，不能拿 seed 當登入成功證據。

## Phase 3: US1 — 首頁選擇老師或學生 (P1)

**Goal**: 首頁清楚分流，學生不需 Google，教師頁受保護。
**Independent Test**: 匿名老師／學生各自從首頁到正確入口；學生可加入受控課堂；以已授權 fixture 驗證老師返回自己的管理頁。此階段只驗入口，不宣稱 Google callback 已完成。

### Tests

- [X] T013 [P] [US1] 在 `tests/contract/test_google_auth_routes.py` 先定義 `/`、`/student`、`/teacher`、`/teacher/login` 的 200/303、匿名管理頁保護、已登入返回管理頁、API 401/403 不 redirect Google，以及缺 Google 設定仍可用學生入口的契約。
- [X] T014 [P] [US1] 在 `tests/identity-ui.test.cjs` 先定義身分入口連結、Google 登入表單／CSRF、安全錯誤文字與無本地密碼輸入的 UI 預期；不把 DOM 模擬當真人瀏覽器測試。

### Implementation

- [X] T015 [US1] 在 `src/guided_notes/__init__.py` 與 `src/guided_notes/templates/identity/home.html` 建立 `/` 身分首頁及 `/student` 原學生頁；保留 CLASSROOM_MODE 的課堂／legacy 模板選擇與既有加入端點，不因點老師就 issue grant。
- [X] T016 [US1] 在 `src/guided_notes/google_login/routes.py`、`src/guided_notes/templates/identity/login.html` 與 `src/guided_notes/activities/teacher_routes.py` 建立登入頁、匿名 `/teacher` 303 及已登入管理頁分流，登入表單指向約定 POST/CSRF；Google start 真正功能由 US2 完成，未完成時不做假成功。
- [X] T017 [US1] 更新 `src/guided_notes/templates/activities/classroom.html`、`student.html`、`teacher.html` 及必要的 notes 站內導覽，使學生入口指向 `/student`、首頁可返回身分選擇；保留課堂加入／復線、005/006 全文及題組表單，不混入 Google 規格以外的版面改造。
- [X] T018 [US1] 在 `src/guided_notes/__init__.py` 與 `src/guided_notes/google_login/routes.py` 接妥頁面／API 錯誤分界、固定本地返回路徑及登入頁的可重試提示；禁止前端 teacher_id/email/sub 或任意 next URL 授予身分，確認角色選擇不影響原學生資格。
- [X] T019 [US1] 執行 `tests/contract/test_google_auth_routes.py`、`tests/identity-ui.test.cjs` 與既有學生加入／課堂同步回歸，將命令與實際結果記入 `specs/007-google-teacher-login/validation.md`；明列此 checkpoint 未驗 Google 往返，不代勾兩教師或兩組學生真人驗收。

## Phase 4: US2 — 老師使用 Google 帳號登入 (P1)

**Goal**: 經驗證的 Google 身分首次建帳、再次回同教師，資料隔離與失敗／重放防護完整。
**Independent Test**: 受控 provider 下兩個不同 sub 各自首次／再次登入與建課程，同 sub 並行只有一教師；錯誤結果全部不授權。真實 Google 另於 T057。

### Tests

- [X] T020 [P] [US2] 在 `tests/unit/test_google_identity.py` 先定義 Flow login scope/online、S256/verifier 還原、aud/iss/iat/exp/nonce/sub/azp、顯示 email 變更不認領資料，以及 scope-change Warning 的額外／缺漏／別名／無 scope 處理；用受控 HTTPS response／驗簽測試材料，不繞過待測的 verifier。
- [X] T021 [P] [US2] 在 `tests/contract/test_google_auth_routes.py` 擴充 POST start／callback／安全 session 所需案例：CSRF、重複 query、code/error 混用、state/browser/期限、取消／錯誤代碼／乾淨 303、固定 redirect，以及不公開 token/subject/client；Sheets 狀態完整內容由 US3 接續。
- [X] T022 [P] [US2] 在 `tests/integration/test_google_login.py` 與 `tests/integration/test_google_auth_races.py` 先定義兩教師首次／再次／並行、重放、一 browser last-start-wins、不同 browser 不互斥、停用、自然過期 grant 重新登入及 finalize 故障全回滾；logout 相關競態留 US3，但不能因舊 grant 過期就永遠無法重新登入。

### Implementation

- [X] T023 [US2] 在 `src/guided_notes/activities/schema.sql`、`src/guided_notes/google_login/schema.sql` 與 `repository.py` 落實「新 DB schema 中 username/password_hash 改為可 NULL，Google 教師均為 NULL，不產生可登入的本地密碼。」，以及 identity teacher_id「PK/FK teachers.id，一教師一個 Google 身分，本輪不做換綁。」、issuer「固定 canonical `https://accounts.google.com`。」、subject「經驗證的 sub，非空字串，與 issuer 複合 UNIQUE。」、display_name/email「可空，顯示資料，永不作所有權／自動合併依據。」、email_verified「boolean 顯示中繼資料，不取代 sub。」及 created_at/updated_at「UTC。」；對照 `tests/integration/test_google_schema.py` 補唯一／nullable／active constraint 證據，不遷移舊 DB。
- [X] T024 [US2] 在 `src/guided_notes/google_login/provider.py` 實作 Web authorization_request／exchange_and_verify：login 顯式 online、僅 openid/email/profile，固定 HTTPS endpoint/精確 URI、PKCE S256、原 verifier、Google ID-token 完整驗證與 issuer canonical；應用先驗 state 才 `fetch_token(code=...)`，有界 timeout，不全域開 insecure transport；局部處理已解析 scope-change Warning、不記錄 token、不重送 code、不全域放寬 scope，完成 T020。
- [X] T025 [US2] 在 `src/guided_notes/google_login/service.py` 與 `routes.py` 接 login start／callback 前半：建立該 browser 當次 attempt、保留原教師、驗合法單值 query 與綁定、原子 claim 後才外網；取消／過期／processing／終態／錯 client/URI/instance 明確拒絕，不從 callback query 決定 purpose。
- [X] T026 [US2] 在 `src/guided_notes/google_login/service.py`、`repository.py` 與 `src/guided_notes/auth.py` 完成短交易 finalize 與 require_teacher：重查 claim/epoch/expected grant/active/唯一身分，原子建或取 teacher＋identity＋原 grant，server current pointer 對應 cookie grant，撤該 browser 舊 grant；既有 grant 自然過期可重登入，登出／切換造成的 pointer/epoch 改變則不可繞過，錯誤不留半教師。
- [X] T027 [US2] 在 `src/guided_notes/google_login/routes.py` 完成 POST `/auth/google/start`、GET callback 及 Google session 的服務接線，callback 不 render raw 參數，僅乾淨 allowlist 本地 303／安全訊息；設定／服務失敗、取消、停用分清契約錯誤，原有效教師直到成功切換前保留。
- [X] T028 [US2] 先於 `tests/unit/test_google_logging.py` 放 callback code/state/error_description、token/client_secret sentinel，再在 `src/guided_notes/google_login/log_redaction.py` 與 `__init__.py` 安裝 Werkzeug／OAuth exception 脫敏、no-store/no-referrer 與 Cookie 策略；在輸出 handler 前遮 query，不開 debug、不記完整 provider payload，證明 error path 亦無秘密。
- [X] T029 [US2] 在 `src/guided_notes/config.py`、`__init__.py`、`activities/teacher_routes.py` 與 `activities/init_teacher.py` 將正式預設切為 Google：密碼 POST 回 410 PASSWORD_LOGIN_DISABLED、CLI 拒絕人工密碼教師、移除正式密碼表單；`test_password` 僅 TESTING=True，非 testing 啟用須啟動失敗，無示範／密碼 fallback，補 `tests/contract/test_google_auth_routes.py` 保護。
- [X] T030 [US2] 核對 `tests/conftest.py` 與全部直接 create_app 的既有回歸測試，明確採用舊 test_password 或 Google fixture；原教師權限與課堂／notes 測試仍驗原語意，不刪正常測試、不把 401/403 改成登入成功、不讀個人環境憑證。
- [X] T031 [US2] 完成並執行 `tests/integration/test_google_auth_races.py` 的同 sub 不同 browser 首次建帳、同 callback 平行 claim、同 browser 新舊 attempt、停用後 finalize、自然過期後重登入及 commit fault 注入；核對 teacher/identity/grant/browser pointer 全成或全敗，錯誤不影響其他 browser。
- [X] T032 [US2] 在 `tests/integration/test_google_login.py` 核對取消／無效 nonce／timeout／失敗換帳號時原 A 資格保留、成功換為 B 時 A 舊 grant 失效；以 token/identity 回應白名單與日誌捕捉證明沒有私有欄位，保留後續 US3 的實際 logout 驗證。
- [X] T033 [US2] 在 `tests/integration/test_google_notes_integration.py` 以真實 Google-mode route 加受控 provider 建立 A/B 身分，測直接請求 A 的課程／講義／活動／回填資源被 B 拒絕，email 相同或更新均不合併；檢查原 TeacherContext 與 DTO/context 不增 Google 欄位，Sheets 真正憑證接線由 US3 完成。
- [X] T034 [US2] 執行 T020–T033 對應單元／契約／整合及原權限回歸，把真實命令、數量與失敗修復記到 `specs/007-google-teacher-login/validation.md`；此時只有受控登入證據，尚不能宣稱已真實 Google 登入、可正式交付或已接本人 Sheets。

## Phase 5: US3 — 登出、切換及講義授權界線 (P2)

**Goal**: 老師清楚目前身分並可撤銷本 browser 資格；Sheets 明確另同意且只使用本人 credential，保留學生資格。
**Independent Test**: A 登出重送被拒，B 登入無 A 資料；同 browser 學生仍可恢復；A connect 選 B 被拒、選 A 才可貼連結，失效只要求重連不登出教師。

### Tests

- [X] T035 [P] [US3] 在 `tests/contract/test_google_auth_routes.py` 先定義 GET session 安全狀態、CSRF logout 的 JSON 204/HTML 303、匿名 pending login 可取消、切換／登出只撤本 browser 教師、學生 grants/proof 保留；於 `tests/identity-ui.test.cjs` 接續目前身分／nullable 顯示／登出與重試預期，同檔循序。
- [X] T036 [P] [US3] 在 `tests/contract/test_google_sheets_auth.py` 先定義 connect/status/callback 的教師與 CSRF、同 sub、實際 scope／部分同意、scope-change Warning、無 refresh、取消不覆蓋、固定返回及全部 409/403/503/Retry-After 契約；登入附帶 API scopes 不能自動標 connected。
- [X] T037 [P] [US3] 在 `tests/unit/test_google_credentials.py` 與 `tests/unit/test_google_transport.py` 擴充 owner/instance/client/generation/revision、錯 key／搬移、refresh_token 缺漏保留條件、無新 ID-token／有新 ID-token 驗證、scope不足、invalid_grant 清密文及 lease/revision CAS 預期；使用臨時密文與受控 refresh，不讀 Desktop 憑證。 另先定義真正 AuthorizedHttp 搭受控 HTTP 的不可刷新快照測試：取得後過期 before_request 不發 HTTP/refresh、401 僅一次 HTTP、不帶 refresh_token/client_secret/handler、專用本地送出前失效分類及已送出單元不 replay。
- [X] T038 [P] [US3] 在 `tests/integration/test_google_auth_races.py` 擴充 claim 後 logout／切換／停用、晚到 Set-Cookie、refresh 與 reconnect、lease 過期／busy、舊 invalid_grant 不毒化新 credential 的交錯；明確區分已送往 Google 的寫入不可撤回與登出後新操作必須拒絕。 加入假 monotonic/UTC 時鐘，驗 20 秒結果接受期限與 30 秒 lease 各自有效、token POST 最多一次／必要憑證 GET 最多一次、SDK 額外 retry 被攔截、deadline／timeout 不改 credential 狀態且只 CAS 釋放自己 lease。

### Implementation

- [X] T039 [US3] 在 `src/guided_notes/google_login/schema.sql` 與 `repository.py` 定義 google_sheets_credentials：teacher_id「PK/FK google_identities.teacher_id，每位教師一組目前 credential。」、instance/issuer/subject/client「NOT NULL，與目前 DB、教師映射、Web client 同值。」、credential_id「UUID UNIQUE，每次重新連接使用新 generation。」、revision「正整數，connect／refresh 成功或狀態變更時增加。」、status「connected / reauth_required。」、granted scopes/expiry「實際授予的 scope 與 access-token 期限；非純 requested scopes。」、secret_blob「connected 時必為 Fernet BLOB，含 token／refresh／expiry／scope 及上述 owner/generation/revision；reauth_required 可 NULL。」、lease「可空；30 秒 lease，不持有交易跨網路。」及 created/updated「UTC。」；補 `tests/integration/test_google_schema.py` 約束與 init 保留測試。
- [X] T040 [US3] 在 `src/guided_notes/google_login/service.py`、`routes.py` 與 `src/guided_notes/auth.py` 完成 logout／切換撤銷：CSRF 後 epoch++、撤本 browser current teacher grant、取消 pending/processing 的可 finalize 資格；只清教師 alias，保留 browser binding、csrf、student_grant/classroom_grant/proof，無 `session.clear()`、無 Google revoke；晚到 cookie 必經 server pointer 拒絕。
- [X] T041 [US3] 在 `src/guided_notes/google_login/routes.py`、`src/guided_notes/static/identity.js` 與教師模板完成安全 GET session、目前姓名／email 純文字、登出／切換表單、失效提示；不顯示 subject/client/token/key，學生入口與資格獨立，完成 T035 UI 預期。
- [X] T042 [US3] 在 `src/guided_notes/google_login/sheets_service.py`、`provider.py` 與 `routes.py` 實作已登入者 connect purpose：同 Web client，openid/email/profile＋spreadsheets、offline、include_granted_scopes、必要的 consent，login_hint 只提示；記 expected teacher/grant/sub／返回 allowlist，callback 重驗身分及實際 scope，禁止用 query purpose 或已登入 scope 靜默連接。
- [X] T043 [US3] 在 `src/guided_notes/google_login/sheets_service.py` 與 `repository.py` 完成 connect finalize：外網後短交易重查 browser epoch/claim/有效 grant/active/同 sub/instance/client，再以 T008 加密保存完整列；只保留同 owner/client/instance 的舊有效 refresh，沒有可用 refresh 就要求重連，取消／錯帳號／缺 scope／timeout 不覆蓋原 connected。
- [X] T044 [US3] 在 `src/guided_notes/google_login/sheets_service.py` 與 `provider.py` 實作受控 refresh：30 秒 lease，claim 後 monotonic 20 秒共用結果接受 deadline，最多一次 token POST／一次必要憑證 GET、自動重試 0、固定端點且不跟隨 HTTP redirect；網路步驟前按剩餘預算限制 connect/read 3/10 秒，返回與 CAS 前再驗 deadline／lease。逾時晚回一律不用，僅依 generation/revision/lease CAS 釋放自己的 lease，不改狀態／revision／密文，回 GOOGLE_REFRESH_TIMEOUT／Retry-After:1；不得以私有 SDK API 或全域放寬旗標處理。期限內明確 invalid_grant 才 CAS 清密文／revision++／reauth_required；有新 ID token 驗同 sub，無新者依原綁定，不用過期 token 假驗證。20 秒是接受／提交期限，不假稱能硬中斷所有 I/O。
- [X] T045 [US3] 在 `src/guided_notes/google_login/transport.py` 實作不含 refresh_token/client_secret/handler 的 access-token 快照，valid/expired 依真實 expiry，before_request 僅驗資格／時效與 apply、refresh 明確拒絕且不外呼，不能 expiry=None 偽裝有效；`src/guided_notes/notes/routes.py` 的 gateway 只取此快照，所有刷新走 T044。保留 AuthorizedHttp 的 401 不刷新／重送及 execute(num_retries=0)；於 `src/guided_notes/notes/sheets_gateway.py` 僅新增專用 CredentialSnapshotExpired 的狹窄映射為 GOOGLE_CREDENTIALS_REFRESH_REQUIRED，未送出寫入為 failed，不泛用 Exception 推斷；外部介面、RAW／回讀／恢復不改。Google 模式禁 Desktop／全域 profile fallback，測試 gateway 僅 TESTING 明確注入，完成 T037 的真 SDK 傳輸計數測試。
- [X] T046 [US3] 在 `src/guided_notes/notes/routes.py`、`src/guided_notes/notes/templates/notes/import.html` 與教師管理模板改查本人 Sheets status、顯示連接／重連按鈕及權限提示；未連接仍可管課程，移除 Web 要求跑 Desktop CLI 的提示，不新增 Drive 選檔／API key／檔案瀏覽。
- [X] T047 [US3] 執行並修復 `tests/integration/test_google_auth_races.py` 的 logout/finalize/late-cookie 與 refresh/reconnect 交錯，證明新連接不被舊 refresh 覆蓋、lease busy 不被誤標失效、外網期間不持 DB write lock；已送出外部寫入的限制如實記於 `specs/007-google-teacher-login/validation.md`。 補驗 token API 最大一次、20 秒晚回與 30 秒 lease 交錯、timeout 不誤標 reauth、清理不碰新 owner／revision；記錄阻塞 I/O 不能保證硬中斷的限制，不把 deadline 當成實測性能承諾。
- [X] T048 [US3] 在 `tests/integration/test_google_notes_integration.py` 走受控本人 connect→貼連結→選分頁→預覽／確認→活動全文→受控結果／回填／恢復，覆蓋單題與題組，核對原 DTO/context、RAW／回讀與單活動規則不變；B 無法操作 A，未接正式 003 不產生假排名。 補真實 SDK＋替代 HTTP 的 401／送出前過期／部分已寫入情境，確認原勝組、idempotency、未知狀態恢復與不自動 replay 都保留。
- [X] T049 [US3] 完成 `tests/unit/test_google_credentials.py`、`tests/unit/test_google_logging.py` 的私有資料檢查與部分 scope、scope 別名／額外 scope、無 scope、refresh 缺漏／新 ID-token 差異，確認 log/error/session/cookie 無 token/nonce/verifier/client_secret，錯 key 不自動覆寫，局部 Warning 處理不重送 code。
- [X] T050 [US3] 在 `tests/integration/test_google_notes_integration.py` 以兩個新 DB 重用 teacher_id、舊全域 profile 毒丸、不同 client、密文跨教師／instance 搬移測 fail closed；舊 authorize/私有檔讀取 spy 必為零，登入成功不代表擁有 Sheets 權限，真實檔 403 不誤報登入失敗。
- [X] T051 [US3] 在 `src/guided_notes/google_login/routes.py`、`sheets_service.py` 與 `src/guided_notes/notes/routes.py` 完成契約錯誤／重試 UI 接線：連接與重連分清，busy／GOOGLE_REFRESH_TIMEOUT 回 Retry-After:1，快照失效提示重新進入原操作／恢復流程，notes 保留原巢狀 envelope，callback 用乾淨 303／安全代碼；失效 Sheets 不登出教師，不借其他 token，不把已送出寫入說成已取消。
- [X] T052 [US3] 執行 T035–T051 全部新單元／契約／整合、登入／notes／學生恢復與 005/006 回歸，在 `specs/007-google-teacher-login/validation.md` 記錄實際命令／數量／修復重驗及受控來源限制；不代勾真實 Google 或教師加兩組驗收。

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T053 [P] 更新 `README.md`、`.env.example`、`docs/google-sheets-setup.md`、`specs/007-google-teacher-login/quickstart.md` 的實際 Web client/key/new DB 設定、啟動與錯誤處理，標明新路由已實作後才可用、Desktop CLI 獨立、Drive 下一輪、正式 003 限制；`docs/shared-requirements.md` 僅補真實 D20 狀態，不代填兩組確認或覆寫 005/006 人工紀錄。
- [X] T054 [P] 核對 `diagrams/007-component.puml`、`007-class.puml`、`007-sequence.puml` 與實作的 owner、attempt/epoch/grant、雙 purpose、密文、CAS 及失敗分支，必要時同步修圖並 CLI 產生同目錄 PNG；在 `specs/007-google-teacher-login/diagram-review.md` 記錄實際命令／結果／差異，AI 核對與同學審查分開。
- [X] T055 執行完整 `.venv/Scripts/python.exe -m pytest tests -q`、`node --test tests/identity-ui.test.cjs tests/student-question-text.test.cjs tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs tests/activity-sync.test.cjs tests/notes-ui.test.cjs` 及 git diff --check，在 `specs/007-google-teacher-login/validation.md` 記錄真實計數／退出碼／重驗；額外核對原 DTO/context、005/006 任務與正式無 password／示範 fallback，不把舊數量預填為新結果。
- [ ] T056 依 `specs/007-google-teacher-login/quickstart.md` 由操作者準備 Web application client、固定 127.0.0.1 callback、同意畫面／兩位測試使用者、repo 外 web JSON 與持久 key，在 `specs/007-google-teacher-login/validation.md` 記錄去機敏設定及 instance/new DB 路徑；只記是否準備與結果，不貼憑證，不刪 Desktop token 或來源 Sheets，實際未完成則保持未勾。
- [ ] T057 由兩位真實 Google 測試身分依 `specs/007-google-teacher-login/quickstart.md` 人工驗收首次／再次／取消／失效／切換／登出、跨教師隔離、錯帳號 Sheets connect、本人授權與真實副本唯讀匯入，將姓名、日期、版本、預期／實際與去機敏證據記入 `specs/007-google-teacher-login/validation.md`；替代端不算完成，真實寫回另外追蹤。
- [ ] T058 由教師及兩組學生獨立瀏覽器驗收身分入口、學生無 Google、課堂加入／復線、建立後 5 秒全文、開始才填、準備中結束、同堂單活動、題組／換活動與教師登出不刪學生資格，在 `specs/007-google-teacher-login/validation.md` 記錄操作者／版本／計時／實際結果；不以此自動勾 005/006 未有獨立證據的任務。
- [X] T059 依最終程式與實測執行唯讀 speckit-analyze 及 append-only speckit-converge，在 `specs/007-google-teacher-login/analysis.md`、`validation.md` 記錄結果；若有缺口依流程追加 `specs/007-google-teacher-login/tasks.md` 並重驗，人工／互審缺失保持未完成，不冒稱 converged。
- [ ] T060 整理 `specs/007-google-teacher-login/validation.md` 與 `diagram-review.md` 的 001/002/003 交接與同學實際互審：TeacherContext/grants 保持、雙 purpose、密文 owner、callback 與 notes 邊界、fixture／圖意差異；補實際分工／姓名／日期／結論與 D20 同步狀態，未回報不代填、不將先前 006 審查當本輪核准。
- [X] T061 在 `specs/007-google-teacher-login/validation.md` 準備 PR 標題／描述草稿，連結 spec/plan/三圖/契約/實測與所有未完成限制，確認保留 005/006 修改、未刪真實憑證／講義且任務標記有證據；本任務不自動 commit、push、建立或合併 PR。

## Dependencies & Execution Order

### Phase Dependencies

```text
speckit-analyze → 處理阻擋
  → Setup T001–T004
  → Foundational T005–T012
  → US1 T013–T019
  → US2 T020–T034
  → US3 T035–T052
  → T053/T054 → T055
  → T056 → T057/T058 → T059 → T060 → T061
```

手動步驟未能執行時，仍可整理 T059–T061 的結果／缺口／交接草稿，但未完成的原任務不勾，不把 PR 草稿當可合併。Google Cloud 與真實帳號不是自動替代端測試的前提。

### Entity / Service Dependencies

- T005 測試在 T006–T009 對應設定／加密／schema 前；T007/T008/T009 完成後 T010 attempt repository 才能驗 claim。
- T011/T012 為共用註冊／fixture 邊界；Google identity schema 在 T023、完整 require_teacher 在 T026。US1 已登入頁面的導航可用既有 test_password 授權 fixture，Google-mode 先驗匿名保護；完整 Google 已登入 fixture 等 T023/T026 後建立。登入表單的真實提交留 US2，不假裝 US1 已完成登入。
- US2：T020/T021/T022 → T023/T024 → T025/T026 → T027 → T028/T029/T030 → T031–T034。provider 外網永遠在 claim 與 finalize 交易之外。
- US3：T035–T038 → T039 → T040/T041 → T042/T043 → T044 → T045/T046 → T047–T052。T038 的競態測試要等 logout/connect/refresh 實作後驗綠，不靠提前假服務繞過。
- T043/T044 必須使用 T008 密文服務、T039 credential schema 與原權限；T045 後才可把全線 notes 操作視為本人授權接通。 T045 另外依賴 T037/T038 的快照／deadline 測試；傳輸只能用快照，不接收 provider 內部完整 refresh credential。
- 共享檔序列：routes/service/repository/provider/auth.py、conftest 與跨故事測試按上述順序修改；[P] 不授權同時改同檔。

### Story Independence / MVP

- **US1** 可獨立驗收首頁與學生分流；不需真實 Google，但只是導航增量。
- **US2** 依共用基礎與 US1 路由，受控 OAuth 可獨立驗首次／再次／失敗，不依賴 Sheets 或真實 Cloud 設定。
- **US3** 必須使用 US2 已驗的教師資格；登出與本人 Sheets 是明確的後續垂直流程，不能宣稱零依賴。
- **建議第一增量**：US1 供審閱；**可交付登入 MVP** 還需 US2 與 US3 的登出／撤銷／隔離保護，不能只做登入成功就交付。完整 007 必須含全部 US3、回歸與真人驗收。沒有部署步驟。

### Parallel Opportunities

- US1：T013（Python 契約）與 T014（Node）在基礎後可並行；T015–T018 共享入口／模板，循序整合。
- US2：T020（provider 單元）、T021（路由契約）、T022（整合／競態）可分檔並行定義；T024/T025/T026 有資料與安全依賴，不能跳過。
- US3：T035–T038 在 US2 完成後可分檔定義，但 T035 與 US2 的契約／Node 檔、T038 與 T022 同檔，不能跨故事同時寫。
- Polish：T053 文件與 T054 三圖可並行，兩者完成再跑 T055；真人步驟須真實操作者，不能用代理模擬為通過。

## Implementation Strategy

採增量方式：先共用設定／密文／attempt，再入口、完整 Google 登入，最後登出／本人 Sheets／notes 全線接線。每階段先寫安全與失敗預期，通過對應測試才進下一階段；一份 contract 的成功不代表外部 Google 或真實回填已完成。

資料策略：新建指定的 007 開發 DB，不遷移、不需要刪舊資料。metadata、teacher/identity/grant、credential 以短交易保存；Google 外網不包在 SQLite write lock。讀寫與講義版本規則沿用 005/006/001，不加入 Drive、額外管理員或其他新功能。

記錄策略：自動命令／退出碼、實際 Cloud 設定、兩教師與兩學生組人工分列。未執行就保留未完成。未授權的 commit/push/合併不因模板建議而執行。

## Requirement Coverage

| Requirement / Outcome | Tasks |
| --- | --- |
| FR-001；US1/AC1–2；SC-001 | T013–T019、T058 |
| FR-002；US1/AC3–4 | T016、T018、T021、T025–T029 |
| FR-003/004；US2/AC1–2；SC-002 | T020、T022–T027、T031–T034、T057 |
| FR-005；US2/AC3；SC-003 | T026、T033、T048、T050、T055、T057 |
| FR-006；US2/AC4–5；SC-003/004 | T009–T010、T020–T022、T024–T028、T031–T032、T038/T047 |
| FR-007/008；US3/AC1–3；SC-005 | T035、T038、T040–T041、T047、T057–T058 |
| FR-009；SC-003/006 | T004–T009、T020、T028、T037、T039、T043–T045、T049、T055 |
| FR-010；US3/AC4–5；SC-006 | T036–T039、T042–T051（含 I1 快照／I2 deadline）、T056–T057 |
| FR-011 | T001、T004–T007、T023、T039、T050、T053、T056 |
| FR-012 | T012、T023、T029–T030、T055 |
| FR-013；SC-007 | T017–T019、T033、T045–T048、T052、T055、T058 |
| FR-014；SC-001–007 | T005、T013–T014、T020–T022、T028、T031–T038、T047–T050、T055–T060 |
| 憲章／圖／交接／追溯 | T001–T002、T053–T061 |

## Notes（任務產生時的歷史紀錄；目前狀態以上方 checkbox 為準）

共 61 項：Setup 4、Foundational 8、US1 7、US2 15、US3 18、Polish 9。所有 checkbox 保持未完成。本次未實作、未執行新功能測試、未改 DB／Google 設定或 005/006 人工狀態。下一步是 speckit-analyze，先核對規格、計畫、任務、契約與圖表，再進 implement。

## 2026-11-25 Analyze 修正對應

使用者已授權修正 I1/I2，僅更新設計與任務，仍共 61 項且全部未完成。

| 問題 | 設計落點 | 任務 |
| --- | --- | --- |
| I1 SDK 隱性刷新入口 | plan 傳輸快照、Sheets 契約 I1、data-model 記憶體快照、research R7 | T037/T045（真 AuthorizedHttp／HTTP 計數）、T048/T051 |
| I2 單次 timeout 不等於刷新總期限 | plan 20 秒 deadline／30 秒 lease、Sheets 契約 I2、data-model CAS 清理、research R7 | T038/T044/T047/T051 |

以上只是任務與設計修正，未執行新 adapter、timeout 或真人測試，未改 005/006 checkbox。下一步可重新執行 speckit-analyze 核對。


## Phase 7: Convergence

2026-11-25：依實際程式／測試核對 FR-001–014、SC-001–007、三故事共 14 個驗收情境、8 項資料流決策與憲章六原則。自動可驗範圍未發現新增產品缺口，仍不能宣稱整體 converged；以下聚合原有未完成人工／協作事項，並非重做已完成程式。

- [ ] T062 依 FR-014、SC-001/002/007、憲章 V 與原 T056/T057/T058（partial，HIGH），完成 Web application client／兩位測試教師與持久 key 設定，使用 007 DB 實際跑兩位 Google 教師及教師加兩組學生；記錄真實 OAuth、本人與錯帳號 Sheets、資料隔離、登出保留學生、全文／5 秒／階段與去機敏證據於 validation.md。真實寫回依 001 單獨追蹤；自動替代端不算完成。
- [ ] T063 依 plan 的介面／分工核對、D20 與憲章 I/II/VI、原 T060（partial，MEDIUM），由同學實際互審 google_login 與原 grants/TeacherContext、雙 purpose、notes 授權、fixture 及 diagrams/007-*，補姓名／日期／結論／分工與 OpenSpec 同步狀態於 validation.md、diagram-review.md。未回報不推定已核准；既有 005/006 人工任務不代勾。
