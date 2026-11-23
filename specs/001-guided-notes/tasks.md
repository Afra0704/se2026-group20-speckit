# Tasks: Guided Notes 匯入與回填

**Input**: `specs/001-guided-notes/` 中的 spec、plan、research、data-model、contracts 及 quickstart。
**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[data-model.md](data-model.md)、[介面契約](contracts/interfaces.md)、[格式契約](contracts/format.md)、[research.md](research.md)。
**Tests**: 依憲章 V、spec 的 Independent Test／SC-001–SC-006，以及 quickstart 的自動與人工驗證要求安排測試任務。測試先定義預期並觀察未實作行為的失敗，再完成對應實作；已有邏輯時重用既有有效測試。
**Organization**: 依 US1、US2（P1）、US3、US4（P2）分期。2026-11-23 已完成離線辨識切片，證據見 [validation.md](validation.md)；網頁、資料庫接線及人工驗收未完成。

**離線工作順序調整**：共用骨架由 002 負責，尚未實作。T003／T015／T017 僅依賴標準庫，可先獨立完成並驗證；其餘任務維持既有前置條件。T002 與 Phase 2 不因這三項完成而視為通過。

**本輪使用者授權的續作**：T005、T014、T018、T032 的純資料／Google 邊界部分可在共用骨架前完成，依賴以 mock 取代；T018 不等待 T016 的 Flask 路由測試、T032 不等待 T027 的整個 export service。正常 app 的授權與前置檢查不因此省略。T026／T029／T044 僅完成 DTO／gateway 子部分，仍待 provider、作業與恢復接線，保留未完成。

## Format: `[ID] [P?] [Story] Description`

每項採 `- [ ] Tnnn [P] [USn] 描述與檔案路徑`。只有故事期帶 US 標籤。
[P] 表示共同前置條件完成後，可與同組標記任務同時執行，且各自修改不同檔案。
有依賴的任務在文字及後方依賴表註明，不能只因序號在前就略過它。

## Path Conventions

所有任務路徑相對 repo 根目錄。程式位於 `src/guided_notes/`，測試位於 `tests/`。
程式與測試檔名是 implement 的目標，資料夾尚未建立；現有設計文件可直接讀取。
驗證證據統一記於 `specs/001-guided-notes/validation.md`，建立後記錄版本、執行者、日期、情境、預期與實際結果。
權限、登入及 ended snapshot 由 002／003 提供，001 接 adapter；測試可注入受控 provider，正常應用缺 provider 時拒絕回填。

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 對齊共用骨架、建立可重現環境及離線測試資料。

- [ ] T001 與另一位組員核對 `specs/001-guided-notes/contracts/interfaces.md` 的 app factory、teacher context、provider、識別及欄位；在同檔記錄負責人與介面審查結果，並記錄 `diagrams/001-guided-notes-component.puml`、`diagrams/001-guided-notes-class.puml`、`diagrams/001-guided-notes-sequence.puml` 的組員圖意審查，保留 D01–D04、D06、D08 等未決事項，不代替 002／003 決策。
- [ ] T002 建立或沿用共用 `pyproject.toml`，設定 src layout、Python 3.13 及 research 的依賴範圍，產生並提交 `uv.lock`；以 `uv sync --locked --python 3.13` 及 quickstart 的 import smoke 驗證，將實際結果寫入 `specs/001-guided-notes/validation.md`。
- [X] T003 [P] 在 `tests/fixtures/sheets_layouts.json` 建立單題跨欄答案、跨列題號兩小題題組、混合單題、移動欄列、重複標號、缺表頭及答案交疊的合成 GridData／merges，保留真空白、公式、格式與起始索引；於 `tests/fixtures/README.md` 說明預期題數／作答格數。依本次離線順序調整獨立驗證。
- [ ] T004 [P] 在 `tests/conftest.py` 建立暫存 SQLite、授權／學生 context、可注入 ended snapshot 及可記錄批次／失敗／逾時的 Sheets substitute；測試不需憑證且不連真實來源，依賴 T002。
- [X] T005 依 quickstart 在 `README.md` 連結 `docs/google-sheets-setup.md`，記錄 Desktop OAuth project、Sheets API、測試使用者及 repo 外 client JSON 的準備方式，核對 `.gitignore` 排除憑證與 token；將可用／待設定的狀態記於 `specs/001-guided-notes/validation.md`，保留實際帳號設定給教師操作。

**Checkpoint**: 兩人取得相同介面與可用 Python 環境，離線 fixtures／substitutes 就緒。Google 設定若未完成，保留人工驗收為待執行，離線工作可繼續。

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 完成全部故事共用的設定、資料庫、授權邊界與資料結構。完成本期再進入故事實作。

- [ ] T006 在 `tests/integration/test_notes_foundation.py` 定義 app factory、必要設定、CSRF、teacher／student／未登入／其他擁有者及 init-db 重跑不清空資料的驗證；檢查 Google token 不進 cookie 或錯誤輸出，依賴 Phase 1。
- [ ] T007 建立或重用 `src/guided_notes/__init__.py` 的 create_app(test_config=None)，整合 NOTES_SECRET_KEY、NOTES_DB_PATH、NOTES_GOOGLE_CLIENT_SECRETS、NOTES_GOOGLE_TOKEN，註冊 001 Blueprint／CSRF／providers，設定 HttpOnly、SameSite=Lax 與本機 HTTP cookie；缺少 provider 時 fail closed，依賴 T001、T006。
- [ ] T008 在 `src/guided_notes/db.py` 實作每 request 連線、foreign_keys=ON、有限 busy_timeout 與 `autocommit=True`／顯式 BEGIN IMMEDIATE／SQL COMMIT／ROLLBACK；提供 init-db，既有資料不可清空，網路期間不持有交易，依賴 T007。
- [ ] T009 與 002 共用 `src/guided_notes/auth.py` 的 require_teacher()／TeacherContext，接好來源及活動 ownership；沿用其登入入口，001 不另造教師登入，測試注入身份僅限 testing 設定，依賴 T007。
- [ ] T010 在 `src/guided_notes/notes/models.py` 定義共用 SourceDocument、ImportedCatalog、MainQuestion、AnswerItem、Blank、SourceBinding 及驗證入口；遵守「日期採 UTC ISO 8601，UI 以 Asia/Taipei 顯示」；落實「sheet_id 為 numeric id；title 可變」、「主鍵為 import_id+version，確認後不可變；舊活動引用舊版本」、「kind 為 single 或 question_set；每題是唯一提交單位」、「單題一項且 subitem_label=null；題組至少兩項且標號唯一」、「每個作答項目唯一答案，不和標號格混用」、「範圍為 sheetId+零起算左閉右開 GridRange；label 可空；answer_range 支援跨欄合併」，依賴 T007。
- [ ] T011 在 `src/guided_notes/notes/repository.py` 建立 sources／catalogs／questions／answer_items／blanks／source_bindings 的儲存與唯一／外鍵約束，保存 teacher_id、prompt_text、原 userEnteredValue 與範圍；schema 初始化及升級保留已有資料，依賴 T008、T010。
- [ ] T012 在 `src/guided_notes/notes/routes.py` 建立 Blueprint、契約 error envelope 及權限先行檢查；400／401／403／404／409／422／503 依 interfaces 區分，未授權不得洩漏來源定位，POST 統一 CSRF，日誌「不記 token、完整 Sheet 回應或學生答案」，依賴 T009、T010。
- [ ] T013 執行 `tests/integration/test_notes_foundation.py`，補齊上述共用邊界並將指令、結果及與 002 的實際接線狀態記錄至 `specs/001-guided-notes/validation.md`，依賴 T008–T012。

**Checkpoint**: 基礎測試通過，DTO 與持久化可用，權限為 server-side，測試可以在沒有 Google 憑證時執行。

## Phase 3: User Story 1 - 匯入與確認講義題目 (Priority: P1) MVP

**Goal**: 教師選表、預覽主題號／小題／答案對應，確認不可變版本供活動引用。
**Independent Test**: 不需完成活動搶答，使用兩種合成布局或可編輯副本，驗證正確題數與範圍、錯誤定位、移動欄列及確認前變動。題組結構也須完整辨識，US4 再驗證跨模組整組提交。

### Tests for User Story 1

- [X] T014 [P] [US1] 在 `tests/contract/test_catalog_contract.py` 依 `specs/001-guided-notes/contracts/examples.json` 驗證 CatalogDTO 計數、UUID、版本、single／question_set、item／blank 唯一性、teacher／student 資料邊界；依本輪離線順序調整先完成純 DTO 測試，HTTP 權限仍由 T006／T013 驗證。
- [X] T015 [P] [US1] 在 `tests/unit/test_recognition.py` 使用 T003 fixtures 定義表頭去空白、merge anchor、(1)／（2）標號、題號正規化、位移、空白尾格、分隔列與歧義錯誤案例；至少一個題組第二格須被找到。依本次離線順序調整獨立驗證。
- [ ] T016 [P] [US1] 在 `tests/integration/test_import_routes.py` 定義教師選表、無效 URL／gid、讀取權限、確認前來源改變、重複確認與舊版不可變的 HTTP 行為；以 substitute 觀察預覽不寫來源，依賴 Phase 2。

### Implementation for User Story 1

- [X] T017 [US1] 在 `src/guided_notes/notes/recognition.py` 實作 format 契約的純解析，動態找表頭欄區、主題號跨列範圍、小題標號及右側唯一答案區；保存合併答案左上角錨點，空白格不得遺漏，定位缺表頭／重號／答案交疊，依賴 T015。
- [X] T018 [US1] 在 `src/guided_notes/notes/sheets_gateway.py` 實作標準 Sheets URL 識別、numeric sheetId 選表及官方 client 讀取；fields 明列 GridData 起始索引、userEnteredValue、formattedValue、格式與 merges，保留錯誤分類，不抓任意外部 URL。依本輪調整先由 `tests/unit/test_sheets_gateway.py` mock 驗證，T016 HTTP／真實 SDK smoke 仍待前置環境。
- [ ] T019 [US1] 在 `src/guided_notes/notes/cli.py` 實作 authorize-sheets Desktop loopback CLI，使用 spreadsheets scope，client／token 位於指定 repo 外路徑，處理 invalid_grant 重新授權；將命令註冊至 `src/guided_notes/__init__.py`，並在 `tests/integration/test_google_authorization.py` 用 mocks 驗證路徑及錯誤輸出不含憑證，依賴 T018。
- [ ] T020 [US1] 在 `src/guided_notes/notes/models.py`／`src/guided_notes/notes/repository.py` 落實「import_id 採 UUID4」、「import_version 為同一匯入的正整數版本」、「unit_id 是 question_id 的別名，不另設獨立主鍵」，question／item／blank 身份不得由座標產生；計數遵守「question_count 等於主題號數與提交單位數，answer_item_count 為全部作答項目數」，依賴 T014、T017、T011。
- [ ] T021 [US1] 在 `src/guided_notes/notes/import_service.py` 實作讀表→辨識→預覽→確認重讀→發布版本；建立 semantic_hash／structure_hash／value_hash，語意含主題號、種類、小題序號、題目與順序且排除座標及答案，結構含座標／merge，值含 userEnteredValue 型別與公式；「換行統一為 LF，其餘題目內容不任意忽略」，辨識錯誤不發布，來源變更重建預覽，新版不改舊活動引用，依賴 T017–T020。
- [ ] T022 [US1] 在 `src/guided_notes/notes/routes.py` 實作 GET /teacher/notes、POST worksheets、POST import-previews、POST import-previews/{id}/confirm、GET catalogs/{import_id}/versions/{version}；輸入與錯誤遵守 interfaces 契約，依賴 T021。
- [ ] T023 [US1] 在 `src/guided_notes/notes/templates/notes/import.html`、`src/guided_notes/notes/templates/notes/import_preview.html` 與 `src/guided_notes/notes/static/notes.js` 完成選表、主題號數／作答格數、標號及目標預覽、確認與定位錯誤；保留 escaping／CSRF，依賴 T022。
- [ ] T024 [US1] 執行 T014–T016 與 T019 測試，驗證兩份不同布局、表頭及欄列位移、跨欄答案格、舊版本與 ownership，將結果及涵蓋 FR-001–FR-005、FR-012–FR-014、SC-001 的證據記於 `specs/001-guided-notes/validation.md`，依賴 T023。
- [ ] T025 [US1] 與組員依 quickstart M01／M02 在真實單題與題組副本讀取及預覽，核對全部主題號、小題、實際 merges、答案錨點與操作說明；於 `specs/001-guided-notes/validation.md` 記錄副本、版本與結果，若尚無憑證或未人工操作則如實保持未完成，依賴 T019、T024。

**Checkpoint**: 匯入可獨立展示，題組無需手動重分。離線 MVP 是 T024 通過；真實來源驗收須 T025 完成才可宣稱通過。

## Phase 4: User Story 2 - 預覽並回填勝組答案 (Priority: P1)

**Goal**: 接收可信的已結束快照，驗證完整性後預覽、確認、文字回填與逐項回讀報告。
**Independent Test**: 使用 US1 產生的 catalog 或受控持久化 fixture，以及七組結果範例；替代 002／003 provider 即可獨立測試，實際活動整合於 US4。

### Tests for User Story 2

- [ ] T026 [P] [US2] 在 `tests/contract/test_result_snapshot.py` 測試七組 examples、有勝組／無勝組、未結束、已結束但結算未就緒（RESULT_NOT_READY）、錯 import／result version、缺主題號／小題、混勝組、重複資料；錯誤拒絕回填，依賴 Phase 2 及 T014 的 catalog 契約定案。
- [ ] T027 [P] [US2] 在 `tests/unit/test_export_service.py` 定義原值／預定值／覆寫確認、同題組一次 RAW 請求、文字等號／前導零／中文換行、無勝組略過及精確 stringValue 回讀的預期，依賴 Phase 2。
- [ ] T028 [P] [US2] 在 `tests/integration/test_export_routes.py` 定義 CSRF／ownership、只接受 activity_id、篡改 preview、同 key 同作業、不同 payload 同 key、同來源並行及 read-back 失敗的報告，依賴 Phase 2。

### Implementation for User Story 2

- [ ] T029 [US2] 在 `src/guided_notes/notes/models.py` 定義 ActivityReference、ResultSnapshot、UnitResult、ItemAnswer、ExportPreview、PreviewItem、WriteOperation／WriteItem／WriteReport；落實「結束後不可變；一個主題號一個 UnitResult，必須覆蓋整個 catalog」、「有勝組時所有小題恰好一次且答案非空；無勝組則 winner=null、answers=[]」、「answer_text 為字串；去空白只作有效性檢查，保存原字串不 trim」，action 嚴格為「write、already_matches、skip、requires_overwrite_confirmation」；winner 使用契約欄位 winner_group_id，依賴 T026–T027。
- [ ] T030 [US2] 在 `src/guided_notes/notes/repository.py` 建立 previews／operations／items／source_leases，落實「UNIQUE(teacher_id, idempotency_key)，重複 key 不建立第二份作業，不同 payload 同 key 回 409」、「來源複合主鍵，短交易條件取得／續期／釋放」；owner token、同源互斥、30 秒 timeout 與 300 秒 lease 配合，不在網路期間持交易，依賴 T029、T028。
- [ ] T031 [US2] 在 `src/guided_notes/notes/export_service.py` 接 server-side get_ended_snapshot，核對 ownership、ended 且結算完成、版本與完整成員；以主題號／小題身份比對來源，語意、結構及值指紋分離，純座標移動可重建預覽，題意或成員變更停止，不接受瀏覽器傳入勝組／目標替代資料，依賴 T021、T029–T030。
- [X] T032 [US2] 在 `src/guided_notes/notes/sheets_gateway.py` 實作 numeric sheetId 單格 DataFilter 的 RAW 字串批次寫入，每主題號所有待寫答案單次請求，只改答案 anchor，不修改標號／格式／merge；讀回 userEnteredValue。依本輪調整先由 gateway mock 驗證；T027／T033–T034 的授權、完整題組檢查、lease、寫後回讀報告尚未完成。
- [ ] T033 [US2] 在 `src/guided_notes/notes/export_service.py` 實作 ready→consumed／invalidated 的預覽狀態、確認、精確 overwrite_item_ids、idempotent operation、source lease、結果及來源的寫前重檢，逐提交單位執行；執行期限到則剩餘 not_processed，釋放來源並保留報告，依賴 T030–T032。
- [ ] T034 [US2] 在 `src/guided_notes/notes/export_service.py` 建立回讀判定與報告，遵守「userEnteredValue.stringValue == answer_text」、「成功只能由回讀比對產生」；項目狀態為 not_processed／verified／failed／unknown／skipped／conflict，整體 queued／writing／recovering／completed／needs_attention；「整體只有 verified 與 skipped 時為 completed；全 skipped 亦可完成，報告明列零格寫入」，verified_at 可空，依賴 T033。
- [ ] T035 [US2] 在 `src/guided_notes/notes/routes.py` 接 POST export-previews、POST export-previews/{id}/confirm、GET operations/{id}，重送 writing 作業回 202、終態回 200；驗證錯誤依契約，原始 Google payload 不回傳，依賴 T034。
- [ ] T036 [US2] 在 `src/guided_notes/notes/templates/notes/export_preview.html`、`src/guided_notes/notes/templates/notes/report.html` 及 `src/guided_notes/notes/static/notes.js` 顯示原值／答案／勝組／覆寫確認與逐格狀態，未知不得顯示完成，完成後按需查詢報告，依賴 T035。
- [ ] T037 [US2] 執行 T026–T028，使用 fixture 完成從匯入版本到預覽、確認、回讀的完整流程，逐項核對 FR-006–FR-012、SC-002–SC-004；真實副本依 quickstart M04／M07／M09／M10 另留人工證據，將已執行及未執行部分寫入 `specs/001-guided-notes/validation.md`，依賴 T036。

**Checkpoint**: 可用指定快照獨立展示單題及完整題組回填。只有已回讀一致的項目標成功，失敗與未知留待 US3 恢復。

## Phase 5: User Story 3 - 發現變動與恢復失敗回填 (Priority: P2)

**Goal**: 對移動、衝突、逾時、部分完成與重啟提供可驗證的恢復，保持原勝組。
**Independent Test**: 在 US2 作業中注入來源變動或跨題組中斷，重啟相同暫存資料庫，再驗證先回讀、已完成不重寫及衝突確認。

### Tests for User Story 3

- [ ] T038 [P] [US3] 在 `tests/unit/test_writeback_recovery.py` 定義原值／預定答案／第三種內容、公式同顯示值、題意或結果版變更、無勝組及部分題組的恢復矩陣；明確驗證文字型別、勝組快照及已 verified 不重寫，依賴 US2 離線核心完成。
- [ ] T039 [P] [US3] 在 `tests/integration/test_writeback_restart.py` 定義第一題組成功後第二題組 timeout、寫入成功但回讀失敗、程式重啟、租約到期／失去 owner、兩作業爭用及 provider 版更換，驗證不直接重送，依賴 US2 離線核心完成。

### Implementation for User Story 3

- [ ] T040 [US3] 在 `src/guided_notes/notes/repository.py` 實作未終態作業轉 recovering、租約條件續期／釋放及原 operation／result_version 關聯；遵守「recovering 不能直接重送」與「重新確認的恢復預覽建立新 attempt，連回原 operation 並保留勝組快照」，依賴 T038–T039。
- [ ] T041 [US3] 在 `src/guided_notes/notes/export_service.py` 實作先回讀再重建恢復預覽，原值未變可確認續填、相同答案 verified、第三種內容 conflict、題目／小題／結果變更停止；對純位置變動重建 binding；恢復一律保持原勝組與結果版本，依賴 T040。
- [ ] T042 [US3] 在 `src/guided_notes/notes/routes.py` 實作 POST operations/{id}/recovery-preview，綁 owner 與 origin_operation_id，重用 confirm route 並要求新的 idempotency key，GET 報告不得觸發寫入，依賴 T041。
- [ ] T043 [US3] 在 `src/guided_notes/notes/templates/notes/report.html`、`src/guided_notes/notes/templates/notes/export_preview.html` 及 `src/guided_notes/notes/static/notes.js` 加入恢復與衝突對照操作，提示預覽失效、已完成／待處理範圍、保留原勝組及再次確認，依賴 T042。
- [ ] T044 [US3] 在 `src/guided_notes/notes/sheets_gateway.py` 對讀取 429／暫時 5xx 加有限退避與 jitter；寫入 timeout／不明 5xx 先回讀，不自動重送舊範圍，403／格式錯誤不盲重試；在 `tests/unit/test_google_retries.py` 用假時鐘及受控 transport 驗證，依賴 T041。
- [ ] T045 [US3] 執行 T038、T039、T044，確認跨 request 的部分完成及單 request 已知無效的原子性分類；在 `specs/001-guided-notes/validation.md` 記錄 FR-009、FR-011、FR-015、SC-004 的實際結果，依賴 T043–T044。
- [ ] T046 [US3] 由另一位組員依 quickstart M06／M08 操作副本及恢復畫面，記錄外部編輯可偵測的差異與無法保證的讀寫競態、標明回讀時刻，在 `specs/001-guided-notes/validation.md` 留人工證據；無真實操作保持未完成，依賴 T045。

**Checkpoint**: 恢復先讀後寫、內容衝突需明確確認、重啟後可追蹤原作業。外部競態限制與實際結果一致。

## Phase 6: User Story 4 - 從範本辨識題組並交換整組答案 (Priority: P2)

**Goal**: 將 US1 的題組清單及 US2／US3 的完整快照、回填恢復接到真正的 002／003，完成兩組學生的整組活動。
**Independent Test**: 有一個兩小題題組及一個單題時，顯示兩個主題號、兩個提交單位、三個作答格；未填完整不提交，完整提交一次順位，同勝組逐格回填。001 可用受控 provider 驗證，真實互動需 002／003 接線。

### Tests for User Story 4

- [ ] T047 [P] [US4] 在 `tests/contract/test_question_set_exchange.py` 驗證兩題三格、子題順序、單位層唯一勝組、精確成員集合及舊匯入版本引用；缺項、混勝組、重複／額外小題與未知 blank_id 皆拒收，依賴 US1／US2 的 DTO 定案。
- [ ] T048 [P] [US4] 在 `tests/integration/test_question_set_flow.py` 定義混合講義的 catalog→002／003 adapter→ended snapshot→回填→部分完成恢復流程，以受控 provider 驗證所有小題共用原勝組及完整確認；另保留實際模組整合情境，依賴 US1–US3 離線核心完成。

### Implementation for User Story 4

- [ ] T049 [US4] 在 `src/guided_notes/notes/import_service.py` 提供契約 get_catalog(teacher_context, import_id, import_version)，與同學將已確認 catalog 接入其實際活動入口；在 `specs/001-guided-notes/contracts/interfaces.md` 記錄真實 provider 位置，單題／題組均以主題號作唯一單位，不另開每小題搶答；若前期已完成則沿用，依賴 T047、US1。
- [ ] T050 [US4] 在 `src/guided_notes/notes/export_service.py` 對接同學的真實 get_ended_snapshot，核對 ownership、ended 且結算完成、精確小題集合與不可變結果，禁止以瀏覽器勝組資料代替；與同學確認其學生端全格填完提交、整組一次順位的輸出符合契約，在 `specs/001-guided-notes/contracts/interfaces.md` 留對齊結果，依賴 T048–T049 及 002／003 provider 可用。
- [ ] T051 [US4] 執行 T047–T048，核對題組每次一個批次、標號及 merges 保留、同勝組恢復與 SC-006；將測試替代／真實接線分開記錄於 `specs/001-guided-notes/validation.md`，依賴 T050。
- [ ] T052 [US4] 兩位組員依 quickstart M03／M04，以教師及至少兩組學生操作真正題組提交與回填，核對全部小題同送、整組順位、勝組唯一及三格回填位置；在 `specs/001-guided-notes/validation.md` 記錄執行者、commit、畫面與結果，依賴 T051 及 002／003 完整流程。

**Checkpoint**: 受控契約測試與真實活動分別有證據。002／003 未完成時保留 T050–T052 未完成，001 的離線進展仍可提交。

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 完成跨故事回歸、人工驗收、圖文一致及可審查交付。

- [ ] T053 在 `tests/integration/test_import_capacity.py` 以合成 100 個主題號、每題至多 10 個作答項目檢查掃描完整性及批次請求數，記錄時間與記憶體觀察到 `specs/001-guided-notes/validation.md`；這是設計容量案例，不新增拒收上限，依賴所有故事離線核心完成。
- [ ] T054 由兩位組員交叉完成 quickstart M01–M10 尚未執行的真實來源案例，包含不同題數、移動欄列、變更答案合併寬度、原值與格式比對、可讀不可寫及無勝組，在 `specs/001-guided-notes/validation.md` 逐項標示預期／實際；已驗收項目引用既有證據，依賴 T025、T037、T046、T052。
- [ ] T055 執行 `uv run --locked pytest tests/unit tests/contract tests/integration` 及 quickstart 的實際安裝／CLI smoke，複查所有 teacher routes 的 ownership／CSRF、來源位置與 token 未洩漏、錯誤與日誌分類；在 `specs/001-guided-notes/validation.md` 記錄完整結果及剩餘限制，依賴 T053–T054；只有新增修改或失敗時重跑受影響檢查。
- [ ] T056 逐項核對 `diagrams/001-guided-notes-component.puml`、`diagrams/001-guided-notes-class.puml`、`diagrams/001-guided-notes-sequence.puml` 與實際模組／資料關係／時序；有差異時同步 plan／data-model／contracts、重渲染同目錄 PNG，於 `specs/001-guided-notes/render-report.md` 記錄命令及組員圖意審查，依賴 T055。
- [ ] T057 更新 `README.md` 與 `specs/001-guided-notes/quickstart.md` 為已實測的環境／啟動／授權／測試指令，補真實進度與既有資料升級方式，在 `specs/001-guided-notes/validation.md` 整理經機敏資料檢查的 AI 紀錄索引與分工證據；僅將已執行的命令標為通過，依賴 T056。
- [ ] T058 執行 `$speckit-analyze` 及 `$speckit-converge` 檢查 `specs/001-guided-notes/spec.md`、`plan.md`、`tasks.md` 與實作，將影響交付的剩餘工作列回 `specs/001-guided-notes/tasks.md`，完成修正並重驗後在 `specs/001-guided-notes/validation.md` 記錄結果；本任務與尚待審查的 T059 如實保留狀態，不因檢核循環虛報完成，依賴 T057。
- [ ] T059 依 `.github/pull_request_template.md` 整理指向 master 的 PR 內容，引用功能需求、測試／人工證據、圖表及已確認 Q2／Q3，請另一位組員審查並在 `specs/001-guided-notes/validation.md` 記錄回饋；取得實際審查後才勾選，不自動合併，依賴 T058 及必要補漏完成。

**Checkpoint**: 所有故事具可追溯驗證，文件與程式及圖一致。未完成的人工作業或模組整合保持未完成，不能以離線測試代替。

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 Setup → Phase 2 Foundation → US1 匯入 → US2 回填 → US3 恢復
                                             │             │
                                             └──────┬──────┘
                                                    ↓
                                   US4 真實 002／003 題組整合
                                                    ↓
                                   回歸／人工／圖文／互審
```

階段以完整故事呈現。實際離線開發不必等待較早故事的真人驗收，只要下列核心任務完成即可。

| 工作 | 必要前置 | 可延後的外部驗證 |
| --- | --- | --- |
| Foundation | T001–T005 的共用介面與測試環境；Google 帳號尚未可用須記錄 | Google 授權設定不阻擋離線測試 |
| US1 | T006–T013 | T025 真實範本人工驗收 |
| US2 核心 | T020–T024 的 catalog／binding 及 Foundation | T025，不必等待真實活動 |
| US3 核心 | T029–T037 的可建立作業與回讀核心，T037 的離線部分通過 | US2 真實來源驗收 |
| US4 契約測試 | T014／T026 DTO 定案，完整流程測試另需 US3 核心 | T050／T052 需要同學的 002／003 |
| 收尾 | 全部欲交付的故事與相關人工驗收 | 有外部缺口須明列，任務保持未完成 |

### Within Each User Story

先建立故事測試的預期，再實作模型／儲存、服務、路由與 UI，最後執行整合與人工驗收。
同一服務檔的任務依序完成；T030 的持久化先於寫入，T032 的 gateway 先於 T033 的執行，
T034 的回讀分類先於任何宣稱完成。任務關聯 FR 及 SC 可在下方覆蓋表追蹤。

### Parallel Opportunities

- T002 後，T003 fixtures 與 T004 測試支持可並行，分別寫不同檔案。
- Foundation 後，各故事標記 [P] 的測試可在該故事共同前置完成後並行。
- 001 與同學的 002／003 可依契約各自開發，不同分支／checkout 保持隔離，app factory／auth／DB 由 T001 約定的負責人處理。
- US1–US4 都會修改 notes/models.py、repository.py、export_service.py、routes.py 或 notes.js，這些跨故事實作不能直接並行修改同一工作目錄；依次整合或以 PR 交接。

## Parallel Example: User Story 1

完成 Phase 2 後，T014 寫 `tests/contract/test_catalog_contract.py`，T015 寫 `tests/unit/test_recognition.py`，T016 寫 `tests/integration/test_import_routes.py`，三者可同時進行。T017 起依依賴順序實作。

## Parallel Example: User Story 2

Foundation 及 catalog 契約完成後，T026 的快照契約、T027 的服務情境、T028 的 HTTP／並行情境分別寫不同測試檔，可並行。T029–T036 的共用程式修改依序進行。

## Parallel Example: User Story 3

US2 離線核心可用後，T038 的恢復矩陣與 T039 的重啟／租約測試分別建檔，可並行。服務與儲存的恢復任務依 T040→T041→T042→T043，T044 在 T041 後處理獨立 gateway 檔。

## Parallel Example: User Story 4

T047 可在 catalog／snapshot 契約固定後先建立；US3 核心可用後，T047 與 T048 分別寫契約及完整流程測試，可並行。同學開發 002／003 時可先使用 examples.json，真實 adapter 接線另依 T049–T050 完成。

## Implementation Strategy

### MVP First (User Story 1 Only)

先交付 Phase 1／2 及 US1，展示貼連結、選表、動態辨識單題／題組與確認版本。
這是匯入子功能的 MVP，整個期末系統還需 US2、活動與搶答整合才能滿足回填等核心要求。
離線完成可先交 PR，真實來源與人工驗收繼續保留未完成。

### Incremental Delivery

1. US1 發布可供 002 使用的固定 catalog，立即核對小題身份。
2. US2 用可信受控快照走通回填與報告，再換成真實 provider。
3. US3 補重試、衝突及重啟恢復。
4. US4 完成真正的兩組學生整組提交與勝組回填，題組額外功能才算有完整證據。
5. 收尾回歸、人工驗收、圖文一致及互審。若發現缺漏加入新任務，維持連續新 ID 並更新覆蓋表。

### Parallel Team Strategy

A 主責 001 的匯入／回填，B 主責 002／003 的身份、活動與搶答，沿用先前暫定分工，姓名待團隊補上。
B 可協助 [P] 測試及 T001／T025／T046／T052 人工互驗。
每人使用自己的分支及帳號，變更共用介面先記錄到 contracts，再由對方審查。
任務檔中的 [P] 是可並行性描述，本輪未啟動代理或開發工作。

## Coverage & Validation

| 規格 | 主要任務 |
| --- | --- |
| FR-001 選表 | T016、T018、T022–T025 |
| FR-002 動態辨識 | T003、T015、T017、T024–T025、T054 |
| FR-003 格式歧義 | T015、T017、T022、T024 |
| FR-004 預覽與確認 | T020–T023、T025 |
| FR-005 不可變版本 | T010–T011、T016、T020–T021、T049 |
| FR-006 模組交換 | T014、T026、T029、T047–T051 |
| FR-007 結果驗證 | T026、T029、T031、T050 |
| FR-008 回填預覽 | T027、T031、T035–T037 |
| FR-009 寫前重檢 | T028、T031、T033、T038–T046 |
| FR-010 文字及正確目標 | T027、T032、T034、T037、T054 |
| FR-011 逐項狀態 | T029–T030、T034–T037、T040–T045 |
| FR-012 權限與機敏 | T005–T013、T016、T019、T028、T055 |
| FR-013 合併與標號 | T003、T015、T017–T018、T024–T025、T054 |
| FR-014 題組 | T010、T014–T015、T017、T026、T029、T032、T047–T052 |
| FR-015 恢復 | T030、T038–T046、T048、T054 |
| SC-001 | T024–T025、T054 |
| SC-002 | T037、T052、T054 |
| SC-003 | T013、T024、T026、T055 |
| SC-004 | T037–T046 |
| SC-005 | T025、T046、T052、T054 |
| SC-006 | T047–T052 |

共 59 項，Setup 5、Foundation 8、US1 12、US2 12、US3 9、US4 6、收尾 7。
12 項標記 [P]，每項均有 ID、適用的故事標籤及精確目標檔案。
初次生成時所有 checkbox 未勾選；後續依實際證據更新。2026-11-23 已完成 T003／T015／T017，應用接線與人工驗收尚未執行。

同日續作：使用者明確授權純資料／gateway／授權文件切片，新增完成 T005／T014／T018／T032，累計 7／59；40 項離線測試通過。其他部分完成的任務維持未勾選，實際 SDK／HTTP／DB／provider／人工驗收待前置依賴。

## Notes

2026-11-23：本次先完成 3／59 項離線任務。T021 須實作 data-model 的 ImportPreview 持久化及並行確認只發布一次，並同時提供 get_catalog；T041 恢復須先重新辨識目前位置及核對語意後才回讀，禁止沿用舊座標；T054 要求兩位組員各自完成完整操作並分別記錄。這些設計補正尚未通過完整 analyze，不宣稱已消除所有分析發現。

勾選任務須有實際成果及適用驗證，未執行的人工作業不可代勾。Google 或同學模組依賴未到位時，
照依賴表推進其他離線工作，保留缺口與恢復路徑。下一步執行 `$speckit-analyze`，修正規格／計畫／任務衝突後再進入 `$speckit-implement`。
