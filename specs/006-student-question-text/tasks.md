# Tasks: 學生查看完整題目文字

**Input**: `specs/006-student-question-text/` 的 spec、plan、research、data-model、contracts/display-content、quickstart，以及 `diagrams/006-*` 三圖。
**Prerequisites**: 設計文件已存在；全文是雙方原先定義功能，使用者回報同學已審圖，不重新表決。執行前先完成 speckit-analyze、處理阻擋問題；新介面與 plan 修圖差異由同學核對，不冒稱已核對完成。
**Tests**: 依規格成功條件、計畫及憲章，包含契約／整合／Node 自動驗證與教師加兩組學生人工驗收。先定義新測試，確認新行為尚未滿足後再改程式；既有通過的保護不故意破壞。
**Organization**: 依 US1、US2、US3 的優先序執行，共用契約與儲存先完成。同一檔案的修改循序整合。
**Status**: 2026-11-25 已完成可自動驗證的實作與文件；原 40 項中 37 項完成。T002 介面核對及 T036/T037 人工驗收未完成，證據見 validation.md。不 commit/push，005 人工 checkbox 保持原狀。

## Format: `[ID] [P?] [Story] Description`

`[P]` 表示前置條件已完成後、不同檔案可並行，不是現在執行或另開代理的指示。路徑相對 repo 根目錄。

## Phase 1: Setup

**Purpose**: 核對起點、保留 005 修改，固定可審查的介面與驗證範圍。

- [X] T001 核對 `.specify/feature.json` 指向 006、Git 實際分支及未提交修改，實作前由目前工作樹建立或沿用 `codex/006-student-question-text` 而不丟失 005 成果；在 `specs/006-student-question-text/validation.md` 記錄起點 commit／工作樹、環境版本及 D19 使用者回報，保留 005 人工驗收未完成狀態。
- [ ] T002 在 `specs/006-student-question-text/validation.md` 記錄同學對 `contracts/display-content.md`、Display provider、activity_displays、state metadata 與修圖差異的實作前核對結果；tasks 可先產生，實作前才需完成核對。依使用者指示移除內建示範模式，正式 import_id 一律維持 UUID，不增加 demo 例外；缺姓名或未審項如實留待補，不重新表決全文行為。

## Phase 2: Foundational

**Purpose**: 提供所有故事共用的安全 DTO 驗證及活動文字快照，不改既有核心契約。

- [X] T003 [P] 在 `tests/contract/test_display_content.py` 新增 Display v1 的有效單題／題組、bool 版本、錯 UUID／版號、未知欄位、重複／缺漏／額外／換序 question/item、標號／種類錯配及空白文字測試；保留 `tests/contract/test_catalog_contract.py` 對 v1 item 加 prompt_text 必須拒絕的原測試。
- [X] T004 在 `src/guided_notes/notes/display_models.py` 實作根層與 question 嚴格驗證，逐項落實「整數，必須為 1，bool 不接受。」「與所選 CatalogDTO 相同的 UUID 字串。」「正整數，與所選版本完全相同。」「非空有序陣列；question_id/display_number/kind/items 與 canonical 清單完全一致。」「該版本唯一、與 canonical 相同。」「與 canonical 主題號相同，不重新編號。」「single 或 question_set，與 canonical 相同。」；未知欄位一律拒絕，不改 CatalogDTO v1 validator（依賴 T003 及 T002 實作前介面核對）。
- [X] T005 在 `src/guided_notes/notes/display_models.py` 完成 item／文字及精確配對驗證，落實「該版本唯一、同題且同序，與 canonical 相同。」「單題 null，題組沿用 canonical 標號。」「非空字串（strip 僅用判空），保留字串本體；換行採既有 LF 正規化，不截斷、不自行改字。」；嚴格排除 blank_id、格位、來源 URL、observed_user_value、機敏或他組資料，回應約定錯誤而非猜配對（依賴 T004）。
- [X] T006 [P] 在 `tests/integration/test_student_question_text.py` 先新增 schema／不可變／重跑初始化測試，再於 `src/guided_notes/activities/schema.sql` 定義 activity_displays，逐項落實 activity_id「TEXT PRIMARY KEY，FK activities.id，一活動最多一個快照。」、dto「TEXT NOT NULL，寫入前已驗證的完整 DisplayContentDTO JSON。」、created_at「建立時間，預設 CURRENT_TIMESTAMP。」並加入防 update/delete trigger；只新增結構、不回填舊列、不清空資料。
- [X] T007 在 `src/guided_notes/activities/display_service.py` 實作已驗證安全 DTO 的快照保存／讀取及核心識別核對，保存參與呼叫者現有交易，讀取不寫入、不抓 Sheets；無快照返回 unavailable，快照損壞回 DISPLAY_CONTENT_MISMATCH，不能偽裝 complete；於 `tests/integration/test_student_question_text.py` 驗證快照重複、修改／刪除拒絕及損壞處理（依賴 T005/T006）。

**Checkpoint**: T003–T007 的契約與儲存測試通過後，才接活動及畫面；這不代表全文已對學生可用。

## Phase 3: US1 — 學生在課堂直接閱讀題目 (P1)

**Goal**: 從同版已保存文字建立新活動，兩組建立後可讀全文，開始後才可填答。
**Independent Test**: 在新課堂使用單題講義建立活動；兩組看到同一全文，PREPARING 停用，LIVE 啟用，無須重新加入。可用完整版本 fixture 單獨驗證，不依賴 US3 的改版操作。

### Tests

- [X] T008 [P] [US1] 在 `tests/integration/test_student_question_text.py` 新增完整單題路徑：同版 frozen recognized→Display→課堂活動及 legacy 活動→兩組 state，檢查 prompt 原文、同版 ID、安全白名單、PREPARING/LIVE/CLOSED 及 CSRF／教師／課程／學生 membership 權限，確認 003 context 與 questions.content 不含新增 prompt 欄位。
- [X] T009 [P] [US1] 在 `tests/student-question-text.test.cjs` 新增 classroom／legacy 單題渲染案例，涵蓋 textContent、中文／Unicode／前後空白／換行、長字串、HTML／腳本文字、complete/unavailable 提示、同 ID 階段更新與換場清除舊內容；DOM 模擬不冒稱真實瀏覽器排版驗收。

### Implementation

- [X] T010 [US1] 在 `src/guided_notes/notes/display_service.py` 從指定且已授權的 `notes_catalogs.recognized` 不可變快照取得 prompt，對照同版 canonical catalog 的題號／種類／有序項目生成 DisplayContentDTO v1；已有完整文字的 catalog 可供新活動使用，真正缺字才回 QUESTION_TEXT_UNAVAILABLE，不查 latest、不讀來源答案、不更新既有資料（依賴 T005）。
- [X] T011 [US1] 在 `src/guided_notes/notes/course_catalogs.py` 新增 get_course_display_content 並沿用教師／course／import 綁定檢查，在 `src/guided_notes/activities/classroom_catalog.py` 接 GET_COURSE_DISPLAY_CONTENT；None 使用正式預設，缺服務／非 callable 為 503 DISPLAY_CONTENT_UNAVAILABLE，錯版／額外欄位為 DISPLAY_CONTENT_MISMATCH，不用 AI 或隱性示範資料補字。
- [X] T012 [US1] 在 `src/guided_notes/activities/classroom_routes.py` 建立時取得精確同版 core catalog／display，在既有 activity_transaction 內重檢權限、OPEN 及單活動限制，原子寫活動、questions、activity_displays 與 current_activity_id/state_version；任何一步失敗全回滾，建立 request／201 核心欄位不改（依賴 T007/T011）。
- [X] T013 [US1] 在 `src/guided_notes/activities/teacher_routes.py` 的 legacy `/activities` 建立路徑接 GET_DISPLAY_CONTENT 與同一安全驗證／快照保存，維持原教師歸屬、活動碼及階段語意，不套課堂單活動規則；缺字不得默默建只有題號的活動（依賴 T007/T010）。
- [X] T014 [US1] 在 `src/guided_notes/activities/state_routes.py` 從該活動快照與 core questions 產生明確白名單，新增 display_contract_version=1、question_text_status=complete/unavailable、item.prompt_text 字串或 null，保留原角色／本組／phase 欄位及 005 title；舊活動無快照只提示，不從 notes／Sheets 即時補字，損壞回 409，不輸出 blank_id／來源格位／原答案（依賴 T012/T013）。
- [X] T015 [US1] 在 `src/guided_notes/static/classroom.js` 顯示每項正文與完整／缺字訊息，使用 textContent；新增 `src/guided_notes/static/question-text.css` 僅對 .question-prompt 使用 pre-wrap、overflow-wrap:anywhere，不設 max-height／line-clamp 截斷；於 `src/guided_notes/templates/activities/classroom.html` 載入，保留 005 防亂序／復線／輸入停用與同堂單活動行為。
- [X] T016 [US1] 在 `src/guided_notes/static/activity-sync.js` 加入相同全文、缺字提示及安全文字呈現，在 `src/guided_notes/templates/activities/student.html` 載入共用正文樣式，不套用整份課堂版面或新增課堂加入行為；維持原 legacy 授權與階段限制。
- [X] T017 [US1] 移除 `src/guided_notes/activities/demo_catalog.py`、`src/guided_notes/quiz/demo_submissions.py` 與 `tests/contract/test_demo_entry.py`；在 `src/guided_notes/config.py`、`.env.example`、`src/guided_notes/activities/teacher.py`、`src/guided_notes/activities/classroom_catalog.py`、`src/guided_notes/quiz/submission_gateway.py` 刪除示範旗標、import、分支與受理 fallback。於 `tests/catalog_support.py` 提供僅供測試的有效 UUID catalog/display，更新 `tests/conftest.py` 及 tests/ 下所有依賴刪除模組或示範硬編碼的案例，保留原驗收語意；新增 `tests/contract/test_runtime_providers.py`，驗證殘留舊示範環境旗標也不能啟用假講義／受理，缺正式服務回約定 503，不能放寬 v1、停用測試或刪正常產品／課程 Demo 影片要求。
- [X] T018 [US1] 執行單題契約、T008／T009、legacy 與 `tests/contract/test_runtime_providers.py` 測試，核對移除示範後的正式服務不可用行為及剩餘失效 imports；將實際命令、修復、provider/state 契約及 003 context 不變證據記入 `specs/006-student-question-text/validation.md`，不代勾真人／5 秒驗收。

**Checkpoint**: 完整單題垂直流程可獨立展示；仍須 US2 題組與 US3 版本／教師流程，才可宣稱完整 006。

## Phase 4: US2 — 題組每個小題與作答欄正確對應 (P1)

**Goal**: 一個主題下每個小題的正文、標號、item_id 與欄位正確對應，全部小題仍整組提交。
**Independent Test**: 使用至少兩小題題組與移動欄列版型，核對每格正文，再檢查整組提交及結果／回填身分不變。

### Tests

- [X] T019 [P] [US2] 在 `tests/contract/test_display_content.py` 新增題組錯題、item 換序／重複／缺漏／多出、標號互換及跨版本拒絕案例，驗證同一主題與完整有序 items，不以文字相似或陣列長度猜配對。
- [X] T020 [P] [US2] 在 `tests/student-question-text.test.cjs` 新增兩小題正文、(1)/(2) 標號、input.name 及整組 form 對應的 classroom／legacy 案例，測新舊活動切換不混正文／答案，同一活動開啟仍保留正確對應。

### Implementation

- [X] T021 [US2] 在 `src/guided_notes/notes/display_service.py` 與 `src/guided_notes/activities/display_service.py` 完成題組精確映射，將一個 recognized item 的 prompt 綁同一 canonical item，核對 kind／題號／標號／順序／數量；不更動 question_id、item_id、blank_id、submission_unit_count 或主題計數。
- [X] T022 [US2] 在 `src/guided_notes/static/classroom.js` 與 `src/guided_notes/static/activity-sync.js` 將每個小題正文放在其對應欄位旁，保持一個主題一個表單、全部小題一次送出；補齊 T020 失敗案例，不將小題拆成多次提交或順位。
- [X] T023 [US2] 在 `tests/integration/test_student_question_text.py` 使用題組、移動欄列及不同題號的受控講義，走真正辨識／確認／活動／state 路徑；provider spy 驗證整組答案 item 集合及 003 context 不變，安全 state 無來源答案／座標，全部相同勝組結果仍由原正式模組規則處理，不產生假順位。
- [X] T024 [US2] 執行 T019/T020/T023 與 `tests/contract/test_question_set_exchange.py`、`tests/integration/test_classroom_notes_integration.py` 相關回歸，將題數／小題數／順序／提交及回填契約證據記錄於 `specs/006-student-question-text/validation.md`；只用替代 Sheets／結果，不冒稱真實回填完成。

**Checkpoint**: 題組與單題均可顯示，仍須完成來源變動與舊活動缺字流程的驗收。

## Phase 5: US3 — 老師確認文字與活動版本 (P2)

**Goal**: 教師能核對將顯示的全文；固定活動文字不被來源修改／重新匯入取代，缺字與損壞清楚回報。
**Independent Test**: 活動建立後修改來源並匯入新版，原活動仍讀原快照，新活動讀選定新版；缺字與歧義在確認前拒絕，舊活動不補寫。

### Tests

- [X] T025 [P] [US3] 在 `tests/integration/test_student_question_text.py` 新增來源改字、預覽失效與再次確認、同 import 新版／新 import、舊活動固定文字、舊 catalog 已完整可直接新建、真正缺字拒建及無快照舊活動 unavailable 的案例；檢查 state 期間 Sheets gateway 零呼叫與 DB 無隱性寫入。
- [X] T026 [P] [US3] 在 `tests/contract/test_display_content.py` 新增指定版本不存在、跨教師／課程、provider 缺少／非 callable、QUESTION_TEXT_UNAVAILABLE、DISPLAY_CONTENT_MISMATCH 及損壞快照的錯誤契約，分清 404／409／503，不用最新版本降級。

### Implementation

- [X] T027 [US3] 核對並按新測試必要性修正 `src/guided_notes/notes/import_service.py`、`src/guided_notes/notes/routes.py` 與 `src/guided_notes/notes/templates/notes/import_preview.html`，沿用既有動態辨識與 LF／空白檢查，在發布前標明缺字／歧義並拒絕確認；確認時再讀來源變動維持原流程，不重寫已正確的 recognition 或 base.html 換行樣式。
- [X] T028 [US3] 在 `src/guided_notes/notes/routes.py` 為教師保存頁取得同版授權 display context，於 `src/guided_notes/notes/templates/notes/catalog.html` 顯示每小題全文與缺字提示；Jinja autoescape 不加 safe filter，JSON catalog 回應仍只返回原 v1，不把私有 recognized／答案混進新公開 DTO。
- [X] T029 [US3] 在 `src/guided_notes/activities/display_service.py`、`src/guided_notes/activities/state_routes.py` 核對舊活動無快照、有效快照及損壞錯配三種情況，保證缺快照不 GET 補字、損壞不偽裝 complete；既有 catalog 文字完整時可供新活動使用，不新增 notes manifest、遷移或修改舊活動。
- [X] T030 [US3] 在 `src/guided_notes/static/classroom.js` 與 `src/guided_notes/static/activity-sync.js` 補齊缺字、錯版與服務不可用的中文訊息；依契約區分「選完整版本並建立新活動」與真正缺字「重新匯入」，錯誤時保留既有失敗停用／復線語意，不自動重開或切換活動。
- [X] T031 [US3] 在 `tests/integration/test_student_question_text.py` 注入活動快照寫入故障、對應錯誤及權限／單活動衝突，驗證活動／core questions／display／current/state_version 全成或全敗；驗證重跑 init-db 保留新快照，修改來源及重匯入不改既有活動內容，快照 update/delete 被拒。
- [X] T032 [US3] 執行 T025–T031，自動驗證版本／錯誤／教師預覽與保存頁，於 `specs/006-student-question-text/validation.md` 記錄實際結果、讀狀態無 Sheets 呼叫與無私有資料外洩證據；人工頁面閱讀仍留待後續，不以 HTML 字串測試替代排版驗收。

**Checkpoint**: 三個故事都有自動證據後，再進入完整回歸與真人驗收。

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T033 [P] 在 `README.md`、`specs/006-student-question-text/quickstart.md` 更新實際全文操作、既有完整 catalog 與舊無快照活動的差異、錯誤處理、重新啟動目前工作樹伺服器／避免舊程序佔 5000 的檢查，以及正式 003 限制；不改 005 人工結果、不虛構已提供的新 CLI 或帳號。
- [X] T034 [P] 核對 `diagrams/006-component.puml`、`diagrams/006-class.puml`、`diagrams/006-sequence.puml` 與實作的 provider／快照表／安全投影／版本時序，必要時修圖並 CLI 重新產生同目錄 PNG，將差異、指令、結果及同學核對狀態記入 `specs/006-student-question-text/diagram-review.md`。
- [X] T035 執行 `.venv/Scripts/python.exe -m pytest tests -q`、`node --test tests/student-question-text.test.cjs tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs tests/activity-sync.test.cjs tests/notes-ui.test.cjs` 及 git diff --check，將實際數量、退出碼、失敗修復重驗記錄於 `specs/006-student-question-text/validation.md`；核對原 v1、003 context、005 單活動／準備中結束、排名／回填介面不被放寬。
- [ ] T036 依 `specs/006-student-question-text/quickstart.md` 由教師及兩組獨立瀏覽器人工驗收單題、題組、移動欄列、正文／標號／作答欄、建立後 5 秒同步、開始才可填答、換場與復線；在 `specs/006-student-question-text/validation.md` 記錄姓名、日期、版本、預期、實際、計時與去機敏證據，未執行不勾。
- [ ] T037 由組員實際驗收長中文字、長英文、換行、Unicode、HTML／腳本文字不執行、來源作答格原值不公開、來源改版及舊活動提示，在 `specs/006-student-question-text/validation.md` 記錄瀏覽器視覺／安全結果；此項是人工閱讀與排版驗收，不用 Node 模擬代替。
- [X] T038 在 `specs/006-student-question-text/analysis.md` 與 `specs/006-student-question-text/validation.md` 記錄最終 speckit-analyze 的唯讀結果及 speckit-converge 的收斂結果；若有缺口只依流程追加／修正 `specs/006-student-question-text/tasks.md` 並重驗，人工未做保持未完成，不冒稱完整 converged。
- [X] T039 在 `specs/006-student-question-text/validation.md` 整理給 001／002／003 同學的介面與回歸交接：Display provider、DTO 版本、快照表、state metadata、示範入口／設定／fallback 已移除的證據、固定版本及原核心契約不變；補記實際介面／修圖審查，姓名未知仍待補。
- [X] T040 在 `specs/006-student-question-text/validation.md` 準備可供 PR 審閱的標題／內容、需求／三圖／驗證連結與人工未完成限制，核對 005 原修改及其人工任務沒有被覆寫；不因本任務自動 commit、push、建立或合併 PR，外部動作依使用者授權執行。

## Dependencies & Execution Order

### Phase Dependencies

```text
speckit-analyze：先處理阻擋；T002 為實作前介面核對
  → Setup T001–T002
  → Foundational T003–T007
  → US1 T008–T018
  → US2 T019–T024
  → US3 T025–T032
  → T033/T034 → T035 → T036 → T037 → T038 → T039 → T040
```

### User Story Dependencies

- US1 依賴完整 Display 驗證／快照基礎；可用完整單題 fixture 獨立驗收，不依賴 US3 的重匯入操作。
- US2 沿用 US1 的傳遞／state／畫面管線，獨立增加題組錯位與整組提交檢查；不是另建一套學生介面。
- US3 用 US1/US2 完整管線驗證教師、來源變動與舊活動缺字；測試可用隔離版本 fixture，但不能靠 GET 回填補實作。
- T010、T011、T012、T013、T014 的順序為正式 provider→adapter→兩條建立路徑→安全 state；T017 移除示範並將共用 fixture 改用 tests/ 隔離資料後，才作 T018 的跨模式與缺服務回歸。T008 可使用自己限定的有效 fixture 先定義預期，不必先修改全域 fixture。
- 同檔任務循序：display_models 的 T004→T005，display_service／state／classroom.js 的跨故事修改按 Phase 推進；測試檔跨階段也不平行寫。
- T035 必須在三故事及文件／圖核對完成後執行；T036/T037 只在可執行版本上人工操作。T038 的收斂檢查不得為了清空任務而代勾人工驗收。

### Parallel Opportunities & Examples

以下機會只在所述前置條件滿足後成立，不跨 Phase 同時修改共享檔案：

- Foundational：T003（Display 契約測試）與 T006（schema 測試／表）可並行；T004/T005 跟在 T003 後，T007 依賴兩條路徑完成。
- US1：T008（Python 整合預期）與 T009（Node 渲染預期）可並行；後端管線先完成，再合跑前端與端到端檢查。
- US2：T019（Python 題組契約）與 T020（Node 題組對應）可並行；T021/T022 依各自測試補齊後合跑 T023/T024。
- US3：T025（整合版本情境）與 T026（錯誤契約）可並行；T027–T031 的共享模組依序整合。
- Polish：T033（操作文件）與 T034（圖表一致性）可並行，兩者完成後再 T035；真人驗收不得由代理並行模擬成已通過。

## Implementation Strategy

**MVP first**：共用契約與快照＋US1，先讓完整單題從指定保存版本進入新活動，學生建立後可讀、開始才可填；只有通過單題自動檢查才進題組。

**Incremental delivery**：US2 補齊每個小題與整組提交，US3 補齊教師保存頁、版本不變、缺字／錯誤；最後回歸全部既有契約及人工閱讀。不要以單題可見即宣稱全部題組與版本驗收完成。

**團隊分工**：001 主責安全文字提供端，002 主責活動快照／state／顯示，003 同學核對 context 與答案交換未受影響；共享路由與前端檔案由一個序列整合。技術介面核對不等於重新表決已同意的全文行為。

## Requirement Coverage

| 需求／成果 | 任務 |
| --- | --- |
| FR-001；US3/AC1、AC3 | T010、T025、T027–T028 |
| FR-002；SC-002 | T008–T018、T036 |
| FR-003；US2/AC1、AC2 | T019–T024、T036 |
| FR-004 | T006–T007、T012–T014、T025、T029、T031 |
| FR-005；SC-003 | T005、T009、T015–T016、T020、T028、T037 |
| FR-006 | T003–T005、T008、T010–T014、T023、T026、T035、T037 |
| FR-007 | T025–T030、T037 |
| FR-008 | T012、T017、T021–T024、T031、T035 |
| FR-009、SC-005 | T002、T017–T018、T033、T035、T039 |
| SC-001 | T008、T019–T024、T036 |
| SC-004 | T014、T025–T032、T036–T037 |
| 憲章審查／圖表／AI 與人工驗證 | T001–T002、T033–T040 |

## Notes

共 40 項任務：Setup 2、Foundational 5、US1 11、US2 6、US3 8、Polish 8。實作與自動驗證結果見 validation.md，分析／收斂見 analysis.md。T002/T036/T037 仍未完成，005 人工結果未更改。Convergence 追加項於尾端追蹤原有證據缺口。


## Phase 7: Convergence

2026-11-25 收斂結果為 tasks_appended，尚未 converged。以下只追蹤原有驗證／審查缺口，不增加產品功能，也不代勾原任務。

- [ ] T041 完成 T036/T037 的教師與兩組獨立瀏覽器驗收，補齊單題／題組／移動版型、正文與標號欄位、建立後 5 秒、開始才填答、換場復線、長文字／換行／Unicode／HTML 純文字與來源答案隔離的實際記錄；於 specs/006-student-question-text/validation.md 填姓名、日期、版本、預期／實際及去機敏證據，失敗先修正重驗。依 SC-001–004、憲章 V（partial，HIGH）。
- [ ] T042 由同學核對 DisplayContentDTO v1、GET_DISPLAY_CONTENT／GET_COURSE_DISPLAY_CONTENT、activity_displays、state 新欄位、003 context 不變及 diagrams/006-* 修圖差異，將實際核對者、日期及結果記至 specs/006-student-question-text/validation.md 與 diagram-review.md；補齊 T002/T039 證據，不倒填已完成事前審查。依 plan 介面核對要求、憲章 I/II/VI（partial，MEDIUM）。
