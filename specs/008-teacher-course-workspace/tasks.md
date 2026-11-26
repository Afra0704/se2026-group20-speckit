# Tasks: 教師課程工作區與雙入口講義匯入

**Input**: 本功能 spec.md、plan.md、research.md、data-model.md、navigation.md、contracts/ 四份契約與 diagrams/008-* 三圖。
**Prerequisites**: Phase 0/1 已完成，使用者明確要求產生 tasks；之後先執行 speckit-analyze，處理阻擋問題再 implement。圖意已由使用者回報核對完畢，但姓名／獨立紀錄及本次技術修圖互審、分工與 D21 OpenSpec 確認未回報，不代填完成。
**Tests**: FR-020、SC-001–008 與憲章要求測試，先定義並觀察新增行為失敗，再實作；替代端不代表真 Google 或人工通過。
**Organization**: US1(P1)→US2(P1)→US3(P2)，按故事組織；共用檔循序修改。每故事有獨立驗收情境，實際整合依賴列在文末。
**Status**: 2026-11-26：原72項中67項完成受控實作／自動檢查；T066–T070未執行，另有Phase7 T073交付門檻未完成。證據見validation.md，不能宣稱整體完成。沿用005/006/007修改；未操作真實DB／OAuth或commit/push。

## Format: `[ID] [P?] [Story] Description`

路徑相對 repo 根目錄；`[P]` 只表示該組前置完成後不同檔案可並行，不授意另開代理或同改共享檔。資料欄位限制依 data-model.md 原文引用於模型任務，不能留待實作自行改決策。validation.md 為 implement 時才建立的證據檔，未測不得勾完成。

## Phase 1: Setup

**Purpose**: 保留現有007資料與未提交成果，核對本輪起點及證據邊界。

- [X] T001 核對 `.specify/feature.json`、Git分支／commit／工作樹，保留005/006/007修改，實作時建立或沿用 `codex/008-teacher-course-workspace`；在 `specs/008-teacher-course-workspace/validation.md` 記錄起點、日期、目前DB的預定沿用路徑 `D:/os_final/instance/classroom-007.sqlite3` 與私人備份是否已完成，不reset、不清空DB、不將setup腳本回報當實際切分支。
- [X] T002 在 `specs/008-teacher-course-workspace/validation.md` 記錄使用者已確認的分層頁、雙入口、課堂不可刪／講義可移除與plan授權，整理D21、四份契約／技術修圖及001/002/003分工待核對；未知姓名／未回報互審保持未知，不重新詢問既定行為，不把此整理當T070已完成。
- [X] T003 核對 `.gitignore`、`.env.example`、`pyproject.toml`、`uv.lock` 的環境與機敏邊界，在 `specs/008-teacher-course-workspace/validation.md` 記錄沿用鎖定Python／Flask／Google SDK／cryptography；只準備專用Picker client路徑、受限API key與project number的佔位設定，不安裝新框架、不升級無關套件、不讀真實client/key/token、不覆寫main client或持久key。
- [X] T004 在 `tests/workspace_support.py` 與 `tests/conftest.py` 準備明確Google/classroom fixture、合成Picker/main clients及臨時key、固定時鐘／Google替代端與含007教師／課程／授權／immutable講義的populated fixture；舊test_password僅明確測試模式，沒有全域略過CSRF/nonce/PKCE/grant或正式fallback，操作者DB不作fixture。

## Phase 2: Foundational

**Purpose**: 共用初始化、權限與HTML邊界。此階段不提前建故事專屬模型或假稱雲端選檔已接通。

- [X] T005 在 `tests/integration/test_workspace_007_compatibility.py` 先定義007 populated資料啟動兩次／重跑init-db／附加schema故障的預期：教師、課程、auth_instance UUID、credential ciphertext及immutable歷史保留，失敗回滾當段而不清DB；區分notes全模式與workspace Google＋classroom初始化，模型加入後補全對應斷言。
- [X] T006 在 `src/guided_notes/notes/repository.py`、`src/guided_notes/db.py` 建立可重跑的分段附加schema執行邊界；明確BEGIN IMMEDIATE／COMMIT及故障rollback，不在既有transaction內呼叫會implicit commit的executescript，不宣稱整個歷代app init跨段全原子。先沿用原notes schema；故事模型與workspace marker分別於T032/T054接入，不以缺模型跳過正式檢查。
- [X] T007 在 `src/guided_notes/workspace/__init__.py`、`routes.py`、`src/guided_notes/__init__.py` 建立同一app的HTML Blueprint註冊邊界，僅Google＋classroom啟用新workspace；沿用原app factory與CSRF，原JSON Blueprint及CLASSROOM_MODE=false相容，不先redirect到尚未建立的頁面。
- [X] T008 在 `src/guided_notes/workspace/repository.py`、`routes.py` 建立共用教師／課程／room歸屬讀取與固定本地返回組合，復用 `auth.require_teacher`、`activities.course_service`、`classroom_access`；HTML未登入303登入、API保留JSON語意，不信任前端owner/next，不增第二套身分或課程表。
- [X] T009 在 `tests/contract/test_workspace_routes.py` 與 `tests/integration/test_workspace_007_compatibility.py` 定義並驗證新HTML／原JSON互不取代、TeacherContext／CatalogDTO／DisplayContentDTO／ResultSnapshot形狀不變、main OAuth與學生資格維持的共用回歸基準，不將未知DTO欄位改成容許以遷就新功能。
- [X] T010 執行T005–T009已可驗的共用基準與原bootstrap／Google登入／課程權限測試，把命令、退出碼、實際數量及尚待故事模型的schema斷言記入 `specs/008-teacher-course-workspace/validation.md`；未完成的flow／removal模型驗證不能算此階段已通過。

## Phase 3: US1 — 進入自己的課程工作區 (P1，導覽MVP)

**Goal**: 歡迎頁→課程卡片→課程橫幅／側欄／單區內容；指定課堂才顯示活動控制，保留原教學行為。
**Independent Test**: 兩教師只用既有課程／講義即可驗卡片、直接網址、返回與課堂操作；不需要Picker或講義刪除。

### Tests

- [X] T011 [P] [US1] 在 `tests/contract/test_workspace_routes.py` 補歡迎、卡片、課程總覽／lectures／classrooms／指定room頁的200/303與跨教師拒絕，驗rid必屬cid、GET不啟動Google或發token、原GET/POST `/teacher/courses` 等仍是JSON；先觀察新頁尚未滿足。
- [X] T012 [P] [US1] 在 `tests/workspace-navigation.test.cjs` 定義課程卡片、側欄／breadcrumb、空清單、長名稱、按鈕pending/error恢復與固定course/room的預期；舊localStorage課程或晚到另一課堂回應不能覆蓋目前頁，DOM模擬不算真螢幕驗收。
- [X] T013 [P] [US1] 在 `tests/integration/test_workspace_navigation.py` 定義兩教師建課、以原API建room、直接進指定HTML頁及刷新／返回流程，核對建立後全文、準備可結束、同堂單活動及學生proof保持；使用既有合成講義，不依賴US2雲端完成。

### Implementation

- [X] T014 [US1] 在 `src/guided_notes/activities/teacher_routes.py`、`workspace/routes.py` 與 `templates/workspace/welcome.html`、`courses.html` 完成 `/teacher` 簡單歡迎與 `/teacher/workspace` 課程卡片／建立課程入口，server只列本人資料；原Google登入與登出沿用，不顯示全部流程表單。
- [X] T015 [US1] 在 `src/guided_notes/templates/workspace/base.html`、`overview.html` 與 `static/workspace.css` 完成課程橫幅、目前身分、我的課程、三區側欄／breadcrumb與單區內容；設計1366×768／390×844收合及長字換行，鍵盤可到達導覽，不複製截圖校方標誌或新增公告／評分。
- [X] T016 [US1] 在 `src/guided_notes/workspace/routes.py`、`templates/workspace/lectures.html`、`classrooms.html` 完成本課程既有講義版本／OPEN與CLOSED課堂列表、空狀態及進入room；尚未到US2/US3的功能不做假成功入口，課堂／課程不提供刪除。
- [X] T017 [US1] 在 `src/guided_notes/templates/workspace/classroom.html`、`static/workspace.js` 與必要的 `static/classroom.js` 接線，固定data-course-id/data-classroom-id讀原JSON endpoints，呈現加入碼、組別、活動／歷史；沿用原輪詢、錯序回應丟棄、開始／結束及單活動按鈕狀態，學生頁腳本不被混入教師固定room邏輯。
- [X] T018 [US1] 在 `src/guided_notes/notes/routes.py`、`notes/templates/notes/base.html` 及教師導航模板處理舊HTML課程講義入口303與全域notes返回入口，保留原JSON、preview/report/recovery URL；不讓重新整理或上一頁改變course，不接受任意next。US2預覽flow及US3歷史入口分別後續接入。
- [X] T019 [US1] 在 `src/guided_notes/workspace/routes.py`、`static/workspace.js`、`activities/course_service.py`、`classroom_routes.py` 完成新頁路由註冊與建立課程／課堂後固定本地導覽，優先呼叫既有JSON mutation；需抽共享驗證才移至原service，不複製SQL或self-HTTP、不把原JSON改HTML。
- [X] T020 [US1] 執行T011–T019測試與原課程／課堂／學生同步回歸，記錄 `specs/008-teacher-course-workspace/validation.md` 的實際命令、結果與UI模型限制；此checkpoint僅導覽MVP，不宣稱Picker、刪講義或真人驗收已完成。

## Phase 4: US2 — 按加號選擇講義來源並在需要時授權 (P1)

**Goal**: cloud與link只在實際操作引導必要授權，固定原課程／grant，接原分頁／命名／辨識／確認流程，舊007授權保持。
**Independent Test**: 在受控Google邊界下，兩入口各匯入同一來源，驗同課程、題數／小題／全文與固定版本；真實窄scope、Picker與兩教師手動情境另列T066–T068。

### Tests

- [X] T021 [P] [US2] 在 `tests/unit/test_picker_authorization.py` 先定義專用client／same-main拒絕、固定callback、PKCE/nonce/aud/azp/sub、online/false／省略強制prompt、actual四scope／別名／missing／extra broad、局部Warning與不重送code；亦定義Fernet用途／owner/instance/client/generation/expiry錯配、online-only不refresh的預期。
- [X] T022 [P] [US2] 在 `tests/unit/test_import_flow.py` 定義30分鐘flow、原grant固定而非固定browser epoch、source_kind不可變、各status/revision/CAS、120秒claim晚回、ticket期限／一次選擇、cancel/expire標記commit後才回錯誤與retry規則，先觀察模型／服務未滿足。 補I1/U1：119秒busy、120秒可接手、flow先過期、兩個retry只有一個新claim、舊結果先回也拒絕；failed仍保留輸入、相同／不同命名及sheet、choice_revision舊請求、revise與confirm競態、completed拒修改。
- [X] T023 [P] [US2] 在 `tests/contract/test_import_flow_routes.py` 依四契約定義create/get/authorize/token/selection/read/previews/confirm/cancel/retry，HTML303／JSON201/202/200與巢狀errors，驗拒owner/course/name/next覆寫、no token GET、403 missing scope／503 unsafe、409 busy Retry-After:1及原CatalogDTO外層envelope。 補revise(expected_revision)路由、previews必要choice_revision、相同輸入冪等／不同輸入409、reading到期retry與expired拒絕；相同confirm但existing_import_id不同亦拒絕。
- [X] T024 [P] [US2] 在 `tests/integration/test_import_flow_oauth.py` 定義最後開始有效、多flow不混course/source、sidecar丟失／client錯配、claim後logout/switch/disable、外網無write lock、reconnect後selection晚回、24小時舊attempt清理FK、取消／expired preview從舊notes URL確認被拒，避免僅測route開頭的guard。 補讀取中斷後到期接手、雙retry屏障、新舊結果逆序，以及revise先提交後舊preview/原notes確認URL無法出版。
- [X] T025 [P] [US2] 在 `tests/import-menu.test.cjs`、`tests/picker-flow.test.cjs` 定義＋展開／Escape／焦點、link明確read才建flow、cloud才載Google庫、token僅JS記憶體、popupblocked/cancel/expiry、授權返回續接及刷新防重送；攔截Storage/console/DOM/URL寫入，不能將token藏在data attribute。 補未到期提示／到期明確重試、預覽「重新選擇／修改名稱」回填表單、改選後不顯示舊預覽、completed無修改及失敗後按鈕恢復。

### Models, Services & Integration

- [X] T026 [US2] 在 `src/guided_notes/config.py`、`google_login/provider.py` 定義Picker client路徑／API key／App ID配置，驗repo外web JSON、固定callback／origin、Picker client不同main與佔位值拒用；配置缺少只停用cloud，不阻止GET課程或link匯入，不讀Desktop或覆蓋main，完成T021配置案例。
- [X] T027 [US2] 在 `src/guided_notes/workspace/schema.sql` 定義workspace_import_flows的身分、來源欄位，逐項落實data-model §2原文限制：`flow_id`「高熵UUID PK，可放本地URL但不是授權本身。」；`teacher_id / course_id`「NOT NULL FK teachers/courses；建流程與每次操作核對owner。」；`instance_uuid`「NOT NULL，與目前auth_instance一致。」；`browser_hash`「NOT NULL FK auth_browsers.binding_hash。」；`expected_grant_hash`「NOT NULL，原teacher_grant hash快照；不設cascade FK，登出後可保留失效流程並回清楚錯誤。」；`source_kind`「CHECK cloud/link；建後不可切換，改入口需取消舊flow並另建。」；`spreadsheet_url / spreadsheet_id / suggested_sheet_id`「可空；link只存已解析Google Sheets canonical URL與識別，不接受任意URL；cloud ID在後端metadata核對前僅候選。」；`source_verified_at`「可空；cloud後端驗MIME/trashed後才設定，link在本人Sheets成功讀取後設定。」。 只存canonical Google來源與候選，不存OAuth code/state/verifier；目前teacher/browser/grant/course必須在服務層重驗，不能靠flow_id授權。
- [X] T028 [US2] 在 `src/guided_notes/workspace/schema.sql` 接續flow狀態／版本／claim及結果欄位，逐項落實：`status`「source_pending、awaiting_picker_auth、picking、awaiting_sheets_auth、reading、worksheets_ready、preview_ready、completed、cancelled、expired、invalidated、failed。」；`revision`「正整數，每次有效狀態／上下文改變遞增，用於CAS。」；`oauth_attempt_id`「可空 FK google_oauth_attempts.attempt_id ON DELETE SET NULL；每次重新授權更新，舊attempt不能續接。原007的24小時attempt清理不應被此參照阻擋。」；`worksheets_json`「可空，只存安全的sheet_id/title候選；不存題目答案或token。」；`current_preview_id`「可空 FK notes_import_previews.preview_id，僅本人／同課程可關聯。」；`confirmed_import_id / confirmed_version`「completed必有，FK原catalog版本；不自行複製題目。」；`claim_id / claim_action / claim_until`「reading時必有；claim_action=selection/read/preview，最長120秒，外網外的原子claim與finalize用；其他狀態為NULL。」；`error_code`「可空，安全白名單；無provider raw message、URL、nonce或token。」；`created_at / expires_at / updated_at`「UTC epoch；expires_at=建立後1800秒，不因反覆GET延長。」。 以SQL constraints及T022測試驗互斥／期限，保留同teacher重登入仍不得繼承舊flow的規則。 另落實data-model §2的choice_revision、request_state_json、retry_action；failed保留可信輸入，claim欄位仍僅reading有效，新增欄位不混入原DTO。
- [X] T029 [US2] 在 `src/guided_notes/workspace/schema.sql`、`google_login/flow_context.py` 定義google_oauth_attempt_context：`attempt_id`「PK/FK 原google_oauth_attempts ON DELETE CASCADE。」；`flow_id`「NOT NULL FK workspace_import_flows ON DELETE CASCADE。」；`credential_kind`「CHECK sheets/picker，可信server欄位，不能由callback query覆寫。」；`created_at`「UTC。」。 不改原purpose CHECK；sidecar與flow.oauth_attempt_id須同原attempt建立交易，無context的舊007僅main client，Picker或flow缺context不得降級。
- [X] T030 [US2] 在 `src/guided_notes/workspace/schema.sql`、`google_login/picker_service.py` 定義google_picker_credentials：`teacher_id`「PK/FK google_identities.teacher_id；每教師目前一份窄cache。」；`instance_uuid / issuer / subject / client_id`「NOT NULL，與當前DB、教師Google身分、專用Picker Web client一致。」；`credential_id / revision`「新連接UUID generation與正revision；新grant結果替換同教師cache時更新。」；`actual_scopes`「排序JSON；必含openid/email/profile/drive.file且正規化後不得超出這四者。」；`expires_at`「Google真實epoch expiry，不是本機ticket TTL；剩餘<=60秒不交付。」；`secret_blob`「NOT NULL Fernet，payload僅access_token/scopes/expiry；envelope另綁purpose=picker、owner/instance/issuer/sub/client/generation/revision/scopes/expiry。」；`created_at / updated_at`「UTC。」。 原007與Picker密文用途不可互換，不存refresh/ID-token/verifier/client secret，也不借007 refresh。
- [X] T031 [US2] 在 `src/guided_notes/workspace/schema.sql` 定義workspace_picker_tickets：`ticket_id`「高熵UUID PK；只限受權flow，非獨立登入token。」；`flow_id`「NOT NULL FK flow ON DELETE CASCADE。」；`credential_id / credential_revision`「綁本次窄cache generation，不接受被新連接取代的結果。」；`expires_at`「min(now+300, flow expiry, Google expiry-30秒)。」；`used_at`「可空；接受selection時原子claim，不能用同ticket改選另一檔。」；`created_at`「UTC。」。 重送同ticket不能改檔，delivery lease只限制本系統接受結果，不宣稱Google token提早失效。
- [X] T032 [US2] 在 `src/guided_notes/workspace/schema.sql`、`repository.py` 與 `src/guided_notes/__init__.py`、`db.py` 完成preview mapping及workspace初始化：workspace_preview_flows「preview_id PK/FK notes_import_previews、flow_id NOT NULL FK flow ON DELETE CASCADE、created_at UTC；一個flow可有來源變動後的多個歷史preview，current_preview_id只指目前可確認者。create_preview／confirm_preview須在各自最終transaction內驗flow guard並更新對應；不要外層包transaction跨原服務網路。」；schema marker「workspace_schema_versions(version INTEGER PK, applied_at UTC NOT NULL)」。原core/Google/notes後才在Google＋classroom模式原子建立附加表／marker，重跑不覆寫007資料；完成T005 populated相容、故障rollback、CASCADE/SET NULL及無ready orphan mapping的schema案例。
- [X] T033 [US2] 在 `src/guided_notes/workspace/import_flows.py`、`repository.py` 實作flow create/status/claim/finalize，固定teacher/current grant/browser/instance/course/source、30分鐘TTL、revision CAS、120秒外網claim；GET與展開選單不OAuth，不用固定browser epoch阻擋自身授權，外網後同交易再驗原grant與course，處理中回FLOW_BUSY／Retry-After:1。 依import-flow §外網5定義canonical輸入／指紋比對；120秒未到busy，reading到期或安全failed可明確CAS接手，兩重試唯一成功且舊claim始終拒絕，GET不重試。
- [X] T034 [US2] 在 `src/guided_notes/google_login/service.py`、`flow_context.py` 接008授權start，原purpose=sheets加可信kind/flow；attempt＋sidecar＋flow參照同短交易，沿用原state/PKCE/nonce/claim/epoch；只在flow需要該權限時發起，原007無sidecar流程保持main規則，不能由callback query/next派發。
- [X] T035 [US2] 在 `src/guided_notes/google_login/provider.py`、`flow_context.py` 實作可信profile選擇：Picker專用client、openid/email/profile/drive.file、online、include_granted_scopes=false、無強制consent/select_account；以官方verifier驗簽與專用aud/azp/nonce/同sub，actual scopes正規化後精確allowlist。額外broad或無法確認scope回503 PICKER_SCOPE_UNSAFE，缺required回403 PICKER_SCOPE_REQUIRED；不放寬全域OAuth設定或以requested補granted，完成T021。
- [X] T036 [US2] 在 `src/guided_notes/google_login/picker_service.py`、`workspace/repository.py` 沿用007 crypto實作獨立窄cache的加密保存／載入，驗完整envelope與Google真實expiry，剩<=60秒需重取；有有效cache可由本人有效新grant用但交付重驗當前資格，取消／錯帳號／scope失敗不覆寫；忽略不保存意外refresh/ID-token，不使用refresh／revoke。
- [X] T037 [US2] 在 `src/guided_notes/google_login/service.py`、`routes.py`、`flow_context.py` 完成callback finalize：重查原claim/epoch/grant及flow/course/TTL/awaiting步驟，kind=picker送picker_service、kind=sheets送原sheets_service.connect，成功僅303原flow頁；不讓窄token覆寫007 credential，晚到或失敗不改有效教師，callback不直接匯入來源，回歸007登入／登出／切換。
- [X] T038 [US2] 在 `src/guided_notes/workspace/import_flows.py`、`routes.py`、`google_login/picker_service.py` 完成picker/token POST：CSRF與flow/current grant/course/scope/client/cache generation/expiry全檢查後建立ticket，只回窄access_token、真expires_in、ticket/API key/App ID；no-store/no-referrer、同源、無CORS *，不回其他秘密，GET或link flow不得取得token。
- [X] T039 [US2] 在 `src/guided_notes/workspace/import_flows.py`、`routes.py` 與 `google_login/picker_service.py` 完成selection POST：原子claim ticket＋flow，交易外以後端窄cache查Drive固定files.get及最少fields，驗Sheets MIME/未trashed而不信前端metadata；外網後再驗claim、grant、course、ticket與目前cache generation/revision，錯帳號／晚回不存。可讀不可寫不假裝可回填，不新增上傳或任意URL代理。
- [X] T040 [US2] 在 `src/guided_notes/workspace/import_flows.py`、`google_login/flow_context.py`、`notes/routes.py` 完成link parse/read與兩入口的Sheets授權續接：無本人授權回202 needs_authorization=sheets，原007 main授權成功回同flow，連結／已選來源不丟失；有效credential直接讀分頁，refresh busy/timeout保留Retry-After重試而非誤要求重登入，仍以原不可刷新snapshot供Sheets SDK。
- [X] T041 [US2] 在 `src/guided_notes/notes/import_service.py`、`repository.py`、`workspace/import_flows.py` 接分頁／命名／create_preview／confirm_preview及preview→flow關係；原服務各自最終transaction內驗可信flow guard，catalog publication＋flow completed同commit。只接受current_preview，來源變動新preview續接並再確認；原notes API DTO不改，新confirm用catalog外層envelope，非route前驗一次或包外層transaction跨網路。 實作previews的choice_revision／輸入比對及confirm目標比對；revise與publish共用最終交易guard，舊版及已失效notes預覽不能出版，completed不得修改。
- [X] T042 [US2] 在 `src/guided_notes/workspace/import_flows.py`、`repository.py`、`google_login/service.py` 完成cancel/retry/expiry及有界清理：同交易invalidate綁定ready notes previews／ticket，confirmed不改，失效標記commit後才回錯誤；terminal flow至少保留24小時，刪mapping前確保無ready preview。相容007超過一天的attempt清理CASCADE/SET NULL，不把NULL當新flow；無revoke、無教師登出、無未知寫入replay。 retry用保留的retry_action與輸入快照；仍驗原flow期限/grant/course及selection ticket/cache，不用重試延長權限。revise(expected_revision)原子失效舊預覽並遞增選擇版次，返回候選／原命名，換來源另建flow。
- [X] T043 [US2] 在 `src/guided_notes/workspace/routes.py` 實作import-flow契約的create/get/authorize/token/selection/read/previews/confirm/cancel/retry完整路由與欄位白名單，固定本地返回、HTML303／JSON201/202/200、notes巢狀error及安全狀態；不得混CatalogDTO欄位，錯scope／busy／expired／invalidated等HTTP依契約，整合T023。 新增POST revise與expected_revision白名單；previews驗choice_revision；過期claim可retry、未過期busy、不同輸入或舊版衝突均依補充契約。
- [X] T044 [US2] 在 `src/guided_notes/templates/workspace/lectures.html`、`import.html`、`static/import-flow.js` 完成＋兩選項、link先輸入再明確read、原course續接、分頁單選／名稱／預覽確認與安全retry/cancel；GET/refresh不新OAuth，授權後只續接先前明確操作的CSRF POST，無JS有繼續按鈕，多flow不混，完成T025選單案例。 新增明確「重新選擇／修改名稱」與目前choice_revision，先revise成功才顯示編輯；清舊預覽且不自動重建，completed無修改入口。到期重試由使用者按下，保留原選擇。
- [X] T045 [US2] 在 `src/guided_notes/static/picker.js` 接官方Picker單選Google Sheets／無上傳，僅cloud使用時載庫並取已驗窄token；處理popupblocked／cancel／expiry／舊ticket／晚回，關閉／離頁／成功後解除JS引用，不寫Storage、cookie、URL、DOM或console；改link需新flow，不靜默切路徑，完成T025 Picker案例。
- [X] T046 [US2] 在 `src/guided_notes/http.py`、`google_login/log_redaction.py`、`notes/templates/notes/base.html`、`templates/identity/teacher.html` 完成局部header與授權UI：只乾淨workspace.import_page HTML用strict-origin-when-cross-origin，其餘callback/token保持no-referrer/no-store，無query/header任意放寬；常駐Sheets連接表單移入匯入任務，教師姓名／登出保持，原connect API相容。新增header及log sentinel測試至 `tests/unit/test_picker_authorization.py`，不可取消key來源限制解錯。
- [X] T047 [US2] 在 `tests/integration/test_import_flow_oauth.py`、`test_workspace_007_compatibility.py` 完成T024競態／cleanup與本人connect→兩入口→單題/題組/移動版型→預覽確認／活動全文→受控結果／回填恢復整合；驗原007 credential與學生資格保留、無main token外露、無半份講義、超24h新登入成功、舊preview URL不繞過flow，測試結果provider僅替代端，不是真排名。
- [X] T048 [US2] 執行T021–T047對應單元／契約／Node／整合與007原登入／refresh／傳輸回歸，於 `specs/008-teacher-course-workspace/validation.md` 記錄真實命令／數量／修正重驗，清楚標受控Google；實際Picker窄scope smoke未做不宣稱cloud可交付，T066–T069人工項目保持未完成。

## Phase 5: US3 — 刪除講義並保留已發生的教學紀錄 (P2)

**Goal**: 整份講義清單移除與禁止新引用，既有活動／結果／回填照常；課堂只可結束、不可刪。
**Independent Test**: 使用既有保存講義就能驗取消／確認移除、一般與歷史入口、同來源新UUID及競態，不依賴真實Picker。

### Tests

- [X] T049 [P] [US3] 在 `tests/unit/test_lecture_visibility.py` 先定義import_id而非source/version層級removal、absence=active、owner/course、不可變版本與底層owned_import/catalog_row仍可歷史讀取、同來源新UUID及既有confirmed結果不得復活。
- [X] T050 [P] [US3] 在 `tests/contract/test_lecture_removal.py` 定義remove的CSRF／confirm與欄位白名單、本人200／HTML303／重送同結果、其他人404、一般舊URL410；完整覆蓋各一般清單與新引用入口、無include_removed query繞過及課堂／課程無刪除端點。
- [X] T051 [P] [US3] 在 `tests/integration/test_lecture_removal_races.py` 定義remove↔create_activity、remove↔existing_import新版兩方向屏障，交易前已取DTO也必須最終重檢；create先commit保快照、remove先commit無半活動，trigger拒絕映410非500，兩連線不以sleep假證競態。
- [X] T052 [P] [US3] 在 `tests/integration/test_workspace_history.py` 定義removed講義既有全文、結果、教師歷史版本、原export preview／operation、部分成功／未知回填與恢復仍可用，Google零delete/trash/update非目標呼叫；學生原結果與proof規則不變。
- [X] T053 [P] [US3] 在 `tests/import-menu.test.cjs`、`workspace-navigation.test.cjs` 補講義整份刪除二次確認的名稱／所有版本／歷史與雲端保留說明、取消／重送／失敗按鈕恢復、課堂只有結束無刪除；與US2同檔測試必循序修改。

### Models, Services & Integration

- [X] T054 [US3] 在 `src/guided_notes/notes/schema.sql` 定義notes_lecture_removals：`import_id`「PK/FK notes_imports.import_id；整份講義，不是source或單版本。」；`removed_by`「NOT NULL FK teachers.id，必須與source owner及course owner一致。」；`removed_at`「NOT NULL UTC時間，首次移除時固定。」。 納所有模式的notes原子初始化，無列為active、插入為removed，無一般DELETE/復原；原source/import/catalog/問題與bindings不刪，補 `tests/integration/test_workspace_007_compatibility.py` 驗舊資料零rewrite與重跑保留。
- [X] T055 [US3] 在 `src/guided_notes/notes/lecture_lifecycle.py` 實作owned course/import的整份removal及 `require_active_import`／`require_available_for_activity(...,db)` 介面，同BEGIN IMMEDIATE二次驗owner/course、INSERT ON CONFLICT保首次時間；低階repository.owned_import/catalog_row維持owner語意，不全域active filter、不回收憑證或Google來源。
- [X] T056 [US3] 在 `src/guided_notes/notes/routes.py`、`course_catalogs.py`、`import_service.py`、`display_service.py` 的一般講義／新引用意圖上完整過濾：全域/課程清單、未分配、同來源更新候選、assign、一般Catalog/Display與直接版本URL；本人removed410、其他人404。不要將active filter塞入歷史底層，補T050各入口測試。
- [X] T057 [US3] 在 `src/guided_notes/activities/classroom_routes.py`、`classroom_catalog.py`、`teacher_routes.py`、`classroom_access.py` 與 `notes/schema.sql` 為新activity加同db最終availability guard，store_activity/save_display前再驗原course/active；防禦INSERT trigger固定lecture_removed並映410而非500。保留一堂單活動及legacy入口；合成provider fixture需seed真實notes對應或明確測試adapter，不加正式bypass，完成T051活動競態。
- [X] T058 [US3] 在 `src/guided_notes/notes/import_service.py`、`course_catalogs.py` 與 `notes/schema.sql` 為更新版本及confirmed-preview早回分支加active檢查，網路前與save_catalog最終transaction內再驗；removed不可assign、更新或回一般成功頁。同來源明確新增產新UUID/version1，原source lease仍共享，防禦trigger不阻舊活動狀態／回填，完成T049/T051版本競態與US2 flow確認回歸。
- [X] T059 [US3] 在 `src/guided_notes/workspace/routes.py`、`templates/workspace/history_lecture.html` 與 `notes` 原歷史讀取接線實作 `/teacher/workspace/activities/<activity_id>/lecture`：先驗activity/room/teacher再讀原版本，標已移除且無新建活動入口；原export_service／writeback按owner/activity reference繼續，不接受include_removed query或因removed阻擋歷史，完成T052。
- [X] T060 [US3] 在 `src/guided_notes/notes/routes.py`、`templates/workspace/lectures.html`、`static/workspace.js` 實作POST課程lecture remove與確認視窗，完成200/303／欄位／CSRF／取消／重送／錯誤恢復；移除所有版本選項但不刪雲端。課堂／課程只保留原有操作，不建立DELETE或改名的刪除API，完成T050/T053。
- [X] T061 [US3] 完成並執行 `tests/integration/test_lecture_removal_races.py`、`test_workspace_history.py` 的雙向線性化、confirmed重送、同source新import、removed講義已有export preview／unknown恢復、學生歷史與零Google刪檔驗證；用原007有資料fixture，核對所有一般清單／舊URL及trigger錯誤語意，不以刪DB解測試失敗。
- [X] T062 [US3] 執行T049–T061與US1/US2受控端到端回歸，把實際命令、數量、失敗修正及歷史保留證據記到 `specs/008-teacher-course-workspace/validation.md`，確認原DTO/context與Fernet/main授權未改；未實際操作雲端副本或人工者仍不勾T066–T070。

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T063 [P] 更新 `README.md`、`.env.example`、`docs/google-sheets-setup.md`、`specs/008-teacher-course-workspace/quickstart.md` 的已實作路由／專用Picker設定／保留007 DB／故障處理與測試指令；`docs/shared-requirements.md` 只記真實D21狀態，不代填OpenSpec、姓名或既有人工證據，Cloud未實測不寫已可用。
- [X] T064 [P] 對照 `diagrams/008-component.puml`、`008-class.puml`、`008-sequence.puml` 與實作的profile/flow/grant、token交付／header、FKcleanup、tombstone／歷史與最終交易，必要時修圖並CLI產同目錄PNG；於 `specs/008-teacher-course-workspace/diagram-review.md` 記錄命令、差異及AI核對，同學互審分開記。 包含I1/U1的choice_revision、輸入快照、到期claim接手與revise失效舊預覽分支。
- [X] T065 執行完整 `.venv/Scripts/python.exe -m pytest tests -q`、quickstart列出的全部10份Node測試及git diff --check，在 `specs/008-teacher-course-workspace/validation.md` 記真實命令／退出碼／計數／修復重驗；核對新增schema不重寫007密文、舊JSON/DTO不改、無正式demo/假排名、無私人憑證入Git，不預填沿用上一輪通過數字。
- [ ] T066 由操作者依 `specs/008-teacher-course-workspace/quickstart.md` 準備同project的Picker／Drive API、專用Web client、固定callback/JS origin、受website/API限制的key、project number及兩位Google測試教師；原main client/key/DB保留，記去機敏配置是否完成到 `validation.md`，未實際準備保持未勾，不貼JSON/token/key內容。
- [ ] T067 由操作者先執行 `specs/008-teacher-course-workspace/quickstart.md` 的真實scope smoke：main broad grant已存在時Picker仍只四scope、專用aud/同sub、有效cache不重複同意、錯帳號／缺scope／extra broad安全拒絕、來源限制key與局部Referrer可運作；記姓名、日期、版本、結果及安全bool/scopes證據於 `validation.md`。Python Flow false推論未真驗不能宣稱cloud交付，不能放寬allowlist或取消key限制。
- [ ] T068 由兩位教師依 `specs/008-teacher-course-workspace/quickstart.md` 人工驗收課程卡片／側欄／直接URL、兩入口單題／題組／移動版型、授權取消／恢復／錯帳號、同課程保存、講義移除／舊URL／歷史回填與雲端副本保留；於 `validation.md` 記操作者、版本、預期／實際及去機敏證據，真實寫回依001另記，受控結果不當真排名。 另驗同輸入重送、明確改分頁／名稱後新預覽及舊確認拒絕；逾時與雙重試以受控故障證據分開記錄，不把等待畫面當真Google故障證據。
- [ ] T069 由教師及兩組獨立學生瀏覽器依 `specs/008-teacher-course-workspace/quickstart.md` 驗建立即可看全文5秒、開始才填、題組整組、同堂單活動、準備中結束、換活動／復線、教師登出保留學生；另驗1366×768與390×844、長名稱、鍵盤／Escape／焦點、popupblocked/cancel，記姓名、日期、版本、實際計時／畫面到 `validation.md`，不代勾005/006/007原人工任務。
- [ ] T070 由同學實際核對 `specs/008-teacher-course-workspace/contracts/`、`diagram-review.md` 及001/002/003接線：HTML/JSON、兩client與可信sidecar、窄token例外、flow final guard／cleanup、availability／歷史界線；補具名分工、日期、結論與D21 OpenSpec同步到 `validation.md`／`docs/shared-requirements.md`，未回報不代填，不把使用者允許tasks當技術互審完成。
- [X] T071 依最終程式、spec/plan/tasks/契約與三圖執行唯讀speckit-analyze及append-only speckit-converge，於 `specs/008-teacher-course-workspace/analysis.md`、`validation.md` 記錄結果；有缺口僅按流程追加 `tasks.md` 再實作重驗，人工／互審未完成保持原狀，不因自動測試過就宣稱整體converged。
- [X] T072 在 `specs/008-teacher-course-workspace/validation.md` 準備PR標題／描述草稿，列需求、契約／圖、真實測試、所有人工／Cloud／D21限制及保留005/006/007未提交修改的範圍；逐項核對勾選證據，不自行commit、push、建立或合併PR。

## Dependencies & Execution Order

### Phase Dependencies

```text
tasks生成 → speckit-analyze → 處理阻擋
  → Setup T001–T004 → Foundational T005–T010
  → US1 T011–T020 → US2 T021–T048 → US3 T049–T062
  → T063/T064 → T065 → T066 → T067 → T068/T069 → T070 → T071 → T072
```

Cloud／真人／互審未能執行時，仍可整理T071/T072的缺口與草稿；原人工任務不勾，不把新PR草稿當可合併。新增外部配置未完成不是受控Google測試的前提。沒有任何自動部署或外部訊息傳送任務。

### Entity / Service Dependencies

- T005的populated基準先定義；T006僅共用分段runner，T032才接flow相關schema/marker，T054才接notes removal表／trigger，兩處都須回補並完成T005模型斷言，不形成foundation依賴故事模型的循環。
- T011/T012/T013先於T014–T019；US1導覽可沿用已有講義，不為了驗導覽先做雲端或刪除。
- US2模型順序T027→T028→T029→T030→T031→T032。FK循環以flow先建可空oauth/current_preview，後在同交易插原attempt／preview及mapping再回填；不能任意移除FK解循環。
- T033依T027–T032；T034依T033/T029；T035依T026/T034；T036依T030/T035；T037依T034–T036；T038/T039依T031/T033/T036/T037，selection後驗generation不可省。
- T040依T033/T034/T037；T041依T032/T033/T040；T042依T029/T032/T033/T041。T043整合上述服務後才完整接UI T044/T045/T046，T047–T048驗US2整體。既有007清理在T042與T024交錯驗，不等到真Google才發現FK問題。
- US3 T049–T053測試先定義，T054模型→T055核心→T056/T057/T058入口與最終guard→T059/T060歷史/UI→T061/T062回歸。T058與T041同改confirm_preview，嚴格循序；T057與T017/T019同改活動邊界，不跨故事同改檔。
- 原notes低階owner lookup與flow guard不可互相取代：前者保歷史，後者保續接身分；availability只管一般新引用，回填仍須原owner/activity/result/source lease驗證。

### Story Independence & MVP

- **US1 MVP**：完成共用基礎＋US1即可驗教師分層操作，不依賴Picker；只是導覽增量，不是完整008。
- **US2**：以US1課程頁及007身份／Sheets為前提，有獨立雙入口驗收，不依賴US3刪除；完整交付還須T067真scope smoke。
- **US3**：核心可針對既有保存講義獨立驗，不必等真Picker；本輪按US2後整合以避免共用notes/routes/import_service及UI衝突。
- 完整功能需三故事、自動、真Google與人工／協作證據，不能只做歡迎頁就宣稱完成。

### Parallel Opportunities / Examples

- Setup／Foundation的共享fixture、app及db修改循序；不把尚有依賴的初始化標[P]。
- US1：基礎後T011（Python契約）、T012（Node）、T013（整合）可分檔定義；再循序整合共享workspace頁。
- US2：US1後T021（provider單元）、T022（flow單元）、T023（契約）、T024（競態）、T025（Node）可分檔定義；模型／service／同routes修改循序，不在外網持DB鎖。
- US3：T049/T050/T051/T052可分檔定義；T053與前故事Node同檔，須等US2完成才修改。此[P]僅在US3測試組內分檔並行，不是與US2同時動同檔。
- Polish：T063文件與T064圖可並行，兩者完成後T065全回歸；T068與T069須各自真人與獨立瀏覽器證據，不以代理模擬代替。

## Implementation Strategy

先建立導覽MVP，再做完整flow／窄Picker／Sheets續接，最後移除與歷史競態。每段先寫可觀察的安全／失敗預期，通過對應自動驗證才勾工作；不要寫與實作逐行鏡像而無行為證據的測試。

全程沿用007 populated DB與原key，schema分段可重跑，實作前確認私人備份；所有自動case使用臨時資料，錯誤不以刪DB或borrow Desktop token處理。原003未接入仍明報不可用／未結算，受控結果不包裝成正式排名。未授權的commit/push不因範本「每任務提交」而執行。

## Requirement Coverage

| Requirement / Outcome | Tasks |
| --- | --- |
| FR-001/FR-002；US1 AC1–3；SC-001 | T011–T016、T018–T020、T068 |
| FR-003；US1 AC4；SC-008 | T013、T016/T017/T019/T020、T069 |
| FR-004/FR-006；US2 AC1–3；SC-003 | T022/T023/T025、T033/T038/T040/T043–T046 |
| FR-005/FR-007；US2 AC4；SC-003/004 | T004/T009、T021/T024、T026/T034–T040/T048、T067/T068 |
| FR-008/FR-009；US2 AC3/5/6；SC-002 | T021/T023、T035–T041/T044/T045/T047、T067/T068 |
| FR-010；US2 AC8；SC-004 | T022–T024、T027–T034/T037–T043/T047 |
| FR-011/FR-012；US2 AC7；SC-003/004 | T023/T025、T037/T040/T042–T046/T048、T068 |
| FR-013；US3 AC1/2；SC-005 | T049/T050/T053–T056/T060/T062、T068 |
| FR-014；US3 AC3；SC-005 | T052/T054/T055/T059/T061、T068 |
| FR-015；US3 AC2/4/5；SC-005 | T049–T051/T054–T058/T061 |
| FR-016；US3 AC6；SC-006 | T016/T050/T053/T060/T061、T068/T069 |
| FR-017；US1 AC5；SC-004 | T003–T009/T011/T021–T024/T026–T046/T050/T055–T060/T065 |
| FR-018；SC-008 | T009/T013/T017/T020/T037/T040/T047/T052/T057/T059/T061/T065/T069 |
| FR-019；SC-007 | T012/T015/T025/T044/T045/T053/T060/T069 |
| FR-020；SC-001–008 | 測試任務T005/T009/T011–T013/T021–T025/T049–T053；T065–T071 |
| 相容初始化／憲章／追溯 | T001–T010/T027–T032/T042/T054/T063–T072 |

## Notes

任務生成時的歷史紀錄（不代表目前狀態）：共72項：Setup 4、Foundation 6、US1 10、US2 28、US3 14、Polish 10；全部未完成。本次僅產生任務及靜態格式／覆蓋檢查，不建立產品檔或執行上述測試，不修改圖、DB、Google設定或005/006/007人工狀態。下一步為speckit-analyze，不能把任務存在當作已實作或互審完成。

## I1／U1 修正依據（2026-11-25）

使用者已同意逾時可明確重試、不同選擇先失效舊預覽的建議。補強原任務，維持72項與所有未完成狀態，沒有執行測試或實作。依賴補充：T033依T028輸入快照；T041/T042共同定義revise與出版交易邊界，T043接線後T044才能驗UI；T024競態於T047完成驗證。


## Phase 7: Convergence

- [ ] T073 完成並交叉核對T066–T070的真實Picker／Cloud、兩教師及教師加兩組學生真人、窄視窗／鍵盤／計時與具名互審／D21證據，更新 `specs/008-teacher-course-workspace/validation.md` 並重新執行最終analyze／converge後再判定可交付；依 FR-020、SC-002/SC-007/SC-008、Constitution I/V 與收斂F1（partial，HIGH）。此為既有驗收門檻的追蹤，不增加新功能，不以受控Google／DOM測試代替、不自行填姓名或外部結果。

## PR #7 複審修正（2026-11-26）

依itsusername15的review 6070380173補強既有契約，不新增使用者功能；每項自動驗證後分段commit，人工聚合任務維持原狀。

- [X] T074 確認表單固定使用畫面渲染時的preview_id，不在提交前GET最新ID；補前端雙分頁及HTTP舊確認拒絕／無誤存回歸，保留來源變動須再次確認的提示。
- [X] T075 Picker快取授權在寫入交易內重驗flow階段、revision與cache，拒絕晚到請求倒退流程；補階段前進與同階段版本更新的交錯測試。
- [X] T076 基礎／課堂schema與Google身分schema、auth_instance同交易初始化，啟動與init-db共用；補中途故障回滾、重試、重跑UUID／既有資料保留及不相容舊DB拒絕測試。
