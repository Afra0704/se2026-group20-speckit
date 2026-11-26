# Tasks: 建立活動後顯示學生預覽

**Input**: `specs/005-preview-before-start/` 的 spec、plan、research、data-model、contracts/classroom-preview、quickstart，以及 `diagrams/005-*` 三類圖。
**Prerequisites**: 設計文件已存在；使用者回報 D18 與圖意確認完成，姓名待補。執行以下任務前須完成 speckit-analyze，處理阻擋問題；本文件僅產生任務，不授權跳過分析。
**Tests**: 使用者明確要求自動測試與教師／兩組學生人工驗收。先新增或調整能區分新舊行為的測試，確認因預期差異失敗後再實作；既有已通過的安全測試不需故意弄壞。
**Organization**: 依三個 user story 分組，共用規則先完成；共享同一檔案的任務循序執行。
**Status**: 可自動驗證任務已執行，人工驗收保持未完成；詳見 validation.md。

## Format: `[ID] [P?] [Story] Description`

每個 checkbox 為未完成；`[P]` 僅指滿足前置條件後可以在不同檔案並行，不代表現在啟動代理或允許跳過依賴。路徑皆相對 repo 根目錄。

## Phase 1: Setup

**Purpose**: 確認工作版本及可追溯驗收範圍，不重建專案或套件環境。

- [x] T001 核對實際分支及 `.specify/feature.json` 指向 005，實作前建立或沿用 `codex/005-preview-before-start`，保留既有修改；在 `specs/005-preview-before-start/validation.md` 記錄起點 commit、負責人待補、D18 與分析結果，說明本次補齊已確認行為，不重新表決。
- [x] T002 在 `specs/005-preview-before-start/validation.md` 建立 FR/SC 驗證表，記錄 Python/Node 與測試起點；依 `specs/005-preview-before-start/quickstart.md` 選用專用空白開發 DB，不遷移舊測試資料。若實際刪除使用者已允許丟棄的舊開發 DB，先停止服務、列出並核對精確路徑，僅處理該 DB 及其已核對附屬檔，不刪憑證、程式、整個 instance 或雲端 Sheets。

## Phase 2: Foundational

**Purpose**: 先完成所有故事共用的「一次一個未結束活動」及交易保護，防止部分交付放寬限制。

- [x] T003 在 `tests/integration/test_classroom_preview.py` 新增共用 fixture 與交易測試：使用臨時空白 SQLite DB、單題／兩小題 catalog、兩組學生及兩個獨立已授權教師客戶端，驗證 PREPARING/LIVE 拒建、其他課堂不受影響、失敗全回滾；不加入舊多準備活動遷移 fixture。
- [x] T004 在 `src/guided_notes/activities/classroom_access.py` 與 `src/guided_notes/activities/classroom_routes.py` 建立共用未結束活動檢查，落實「PREPARING 及 LIVE 都算未結束」；create 在既有 BEGIN IMMEDIATE 交易內重檢教師歸屬、OPEN 及所有關聯活動，衝突回 409 ACTIVITY_IN_PROGRESS，建立失敗不留活動／題目／關聯，不新增 app factory 或 DB。
- [x] T005 在 `src/guided_notes/activities/classroom_schema.sql` 加入課堂關聯 INSERT 與 phase UPDATE 防護，阻止第二個未結束活動及 CLOSED 重開；在 `src/guided_notes/activities/classroom_routes.py` 將特定衝突轉約定 409，保留其他錯誤；於 `tests/integration/test_classroom_preview.py` 驗證 trigger、初始化冪等、legacy 不受影響及原子回滾，重跑初始化不刪新資料。

**Checkpoint**: T003–T005 測試通過後才開始故事實作；這裡的共用限制不代表 US3 的完整 UI 與依序活動流程完成。

## Phase 3: US1 — 建立後即可看見活動 (P1)

**Goal**: 建立成功即發布固定版本的名稱、題號、小題及作答欄。
**Independent Test**: 新 OPEN 課堂、兩組已加入，建立單題／題組後兩組均取得 PREPARING 清單，欄位數及順序正確，無須再加入。

### Tests

- [x] T006 [P] [US1] 在 `tests/contract/test_classroom_management.py` 與 `tests/integration/test_classroom_preview.py` 驗證建立後 state 契約：201 PREPARING、current_activity_id、state_version、activity.title、完整有序 questions/items；驗證無 blank_id、來源座標、他組資料，名稱為一般字串。
- [x] T007 [P] [US1] 在 `tests/classroom-preview.test.cjs` 新增 Node VM 渲染測試，涵蓋單題、兩小題、名稱含 HTML 特殊字元的純文字顯示及 PREPARING 輸入／提交停用；沿用既有 DOM 模擬方式，不新增前端框架。

### Implementation

- [x] T008 [US1] 在 `src/guided_notes/activities/classroom_routes.py` 的成功建立交易內，與活動／題目／關聯一併設定 current_activity_id 及增加 state_version；維持「新建活動、題目、關聯及指標全成或全敗」，catalog 查詢不佔用寫鎖。
- [x] T009 [US1] 在 `src/guided_notes/activities/classroom_routes.py` 的 state 回應同一讀取快照中加入本課堂 activity.title，沿用 `src/guided_notes/activities/state_routes.py` 的安全清單，不改 CatalogDTO 或 legacy 回應；不得在 GET 隱性修改 DB。
- [x] T010 [US1] 在 `src/guided_notes/static/classroom.js` 建立成功後刷新 state，以 textContent 顯示活動名稱及「尚未開放搶答」；PREPARING 顯示全部題目但停用 input/button，新 activity id 重建表單且不攜帶上一活動答案。
- [x] T011 [US1] 在 `tests/integration/test_classroom_preview.py` 驗證建立後兩組讀取相同固定版本、單題及題組數量、重新加入前後組別保持、刷新恢復，以及 catalog 失敗不改原 current_activity_id/state_version；檢查新活動未設定 started_at、未呼叫受理 provider 或產生順位。
- [x] T012 [US1] 執行 T006／T007／T011 的測試，在 `specs/005-preview-before-start/validation.md` 記錄命令、版本、預期／實際及失敗修復，不將自動模擬當成兩組真人驗收。

**Checkpoint**: 可在尚未開放搶答的新課堂獨立展示預覽；尚非完整 005 發布門檻。

## Phase 4: US2 — 老師開放後才接受提交 (P1)

**Goal**: 同一活動由預覽轉 LIVE 才能輸入及提交，結束或失聯後停用。
**Independent Test**: 同一活動開始前、開始後、結束後及關課後測試 UI 與直接提交請求；拒絕不產生有效答案／順位。

### Tests

- [x] T013 [P] [US2] 在 `tests/integration/test_classroom_preview.py` 新增 PREPARING/CLOSED/關課的直接提交拒絕，以及學生、其他教師、其他課堂及錯誤 CSRF 的 start/finish/close 拒絕測試；以受理 spy 核對未經授權／未開放請求不進 provider，LIVE 使用受控替代驗證契約而非宣稱正式順位完成。
- [x] T014 [P] [US2] 在 `tests/classroom-preview.test.cjs` 新增同 id PREPARING→LIVE→CLOSED、關課、state 失敗／復線、舊版本及舊課堂晚到回應測試，驗證全部 input/button 狀態與活動識別，不要求重新加入。

### Implementation

- [x] T015 [US2] 核對並在必要時修正 `src/guided_notes/activities/submission_context.py` 與 `src/guided_notes/activities/classroom_routes.py`，保持後端獨立檢查教師權限、OPEN、目前活動及 LIVE；重送／舊活動不得寫入新活動，不改提交 payload、排名或正式 003 provider。
- [x] T016 [US2] 在 `src/guided_notes/static/classroom.js` 每次同步皆依目前課堂與階段更新 input/button，即使 activeId 相同也能開放作答；保留 selection/request/version 防亂序，斷線及驗證失效停用作答，復線成功才恢復。
- [x] T017 [US2] 在 `tests/integration/test_classroom_close.py` 新增關課與延遲提交／start 邊界測試，確認 CLOSED 不重開、不新增有效答案、原活動歷史保留；正式 003 缺少時明確維持既有不可用／待結算限制。
- [x] T018 [US2] 執行 `tests/classroom-sync.test.cjs`、`tests/classroom-recovery.test.cjs`、`tests/classroom-preview.test.cjs` 與相關 Python 階段測試，僅在證據要求時修正回歸，將結果記錄於 `specs/005-preview-before-start/validation.md`。
- [x] T019 [US2] 核對 `specs/005-preview-before-start/contracts/classroom-preview.md` 與實作錯誤／階段回應一致，在 `specs/005-preview-before-start/validation.md` 留下提前提交與他組資料排除證據，不以畫面按鈕停用取代後端驗證。

**Checkpoint**: 可獨立驗收開始／結束安全邊界；正式 003 的完整排名與結算仍不屬本次交付。

## Phase 5: US3 — 下一活動不打斷既有搶答 (P2)

**Goal**: 補齊已確認的單活動限制；準備與搶答時都拒絕新建，結束後才可下一場。
**Independent Test**: 準備、搶答、結束三階段建立，兩視窗同時建立及準備中直接結束；檢查保留歷史與無跨活動誤送。

### Tests

- [x] T020 [P] [US3] 在 `tests/integration/test_classroom_switch.py` 將「預建兩場」舊預期改為準備／搶答拒建、結束再建；新增兩獨立連線與已授權客戶端的同步建立測試，穩定協調競態且不靠任意 sleep，斷言一個 201、一個 409，恰一個未結束活動且無殘筆。
- [x] T021 [P] [US3] 在 `tests/integration/test_classroom_close.py` 與 `tests/integration/test_classroom_preview.py` 驗證目前 PREPARING→CLOSED、started_at 仍空值、closed_at/phase_version 更新、重送及非目前目標回 409 的測試；關課分別涵蓋準備與搶答階段，不產生假答案／順位。
- [x] T022 [P] [US3] 在 `tests/classroom-preview.test.cjs` 新增教師建立按鈕、準備中結束按鈕、409 中文提示、建立失敗、form finally 不誤啟用、歷史讀取失敗／復線及切換課堂晚到回應測試。

### Implementation

- [x] T023 [US3] 在 `src/guided_notes/activities/classroom_routes.py` 擴充目前 PREPARING→CLOSED，保留 started_at 空值、更新 closed_at/phase_version/state_version；PREPARING 與 LIVE 均僅可結束目前活動，非目前或已 CLOSED 回 409 INVALID_PHASE，不加舊資料特例。
- [x] T024 [US3] 在 `src/guided_notes/activities/classroom_routes.py` 開始前確認目標為目前 PREPARING 且無其他未結束活動；關課在同一交易結束關聯未結束活動並更新課堂版本，保留本版歷史；不實作舊指標恢復、非目前 finish 或 GET 隱性遷移。
- [x] T025 [US3] 在 `src/guided_notes/static/classroom.js` 與 `src/guided_notes/templates/activities/classroom.html` 整合建立按鈕業務停用、先結束提示、PREPARING 的明確結束操作與 ACTIVITY_IN_PROGRESS 中文訊息；任何未結束歷史項都阻擋建立，歷史未知／失敗時保守停用並可復線恢復，form finally 不得覆寫業務狀態。
- [x] T026 [US3] 在 `tests/integration/test_classroom_preview.py` 驗證專用空白 DB 從零建立課程／課堂／活動，準備拒建→結束→新建→搶答拒建→結束的全流程，始終最多一個未結束活動，歷史與固定講義版本保留，不實作舊資料相容。
- [x] T027 [US3] 在 `tests/integration/test_classroom_preview.py` 驗證目前指標、活動及課堂歸屬一致：非目前或跨課堂 start/finish 被拒、CLOSED 不重開；重啟與 init-db 保留新流程課程／活動／歷史，state_version 與 phase_version 隨有效操作增加，不受失敗操作影響。
- [x] T028 [US3] 在 `tests/integration/test_classroom_notes_integration.py` 調整受本次規則影響的既有「預建多活動」流程為依序建立／結束，核對 001 固定版本、同堂分組及指定舊活動回填契約保持有效，僅使用替代 Sheets／結果，不執行雲端寫入。
- [x] T029 [US3] 執行 T020–T028 自動驗證，在 `specs/005-preview-before-start/validation.md` 記錄 SC-006、目前指標一致性、失敗回滾與新歷史保留；開發資料重置與正常結束活動分開記錄，失敗須追蹤修復重驗。

**Checkpoint**: 三個故事均可驗收，仍須最終回歸、人工驗收及圖表一致性檢查。

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T030 [P] 在 `README.md` 與 `specs/005-preview-before-start/quickstart.md` 同步實際預覽／開始／結束流程、空白開發 DB 設定、首次教師及 Google profile 綁定、CMD 啟動與正式 003 限制；不新增跨組待確認狀態，其他既有待確認項維持原狀。
- [x] T031 [P] 在 `diagrams/005-component.puml`、`diagrams/005-class.puml`、`diagrams/005-sequence.puml` 核對程式責任、單活動不變量、準備中直接結束及競態分支；必要時更新並用 PlantUML CLI 產生同目錄 PNG，在 `specs/005-preview-before-start/diagram-review.md` 記錄結果與修圖差異。
- [x] T032 執行完整 `.venv/Scripts/python.exe -m pytest tests -q`、`node --test tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs tests/activity-sync.test.cjs tests/notes-ui.test.cjs` 及 `git diff --check`，在 `specs/005-preview-before-start/validation.md` 記錄實際數量、退出碼與失敗重驗；確認未改正式 DB／憑證、未對真實 Sheets 寫入。
- [ ] T033 依 `specs/005-preview-before-start/quickstart.md` 由組員實際操作教師及兩組獨立瀏覽器，驗收單題／題組、名稱與數量、建立與開始各 5 秒內同步、不可預先填答、換活動／刷新／斷線與結束關課，在 `specs/005-preview-before-start/validation.md` 記錄姓名、日期、commit、預期、實際及不含機敏資料的證據；未做或受阻保持未完成。
- [ ] T034 依 `specs/005-preview-before-start/quickstart.md` 由組員人工驗證空白開發 DB 的首次設定、同堂單活動及重啟後本版歷史保留，在 `specs/005-preview-before-start/validation.md` 記錄實際操作；沒有刪除舊 DB 就記為未刪除，不捏造遷移或正式排名驗收。
- [x] T035 執行最終 speckit-analyze 與 speckit-converge，將結果記錄在 `specs/005-preview-before-start/analysis.md`、`specs/005-preview-before-start/validation.md`；有缺漏則依流程追加／修正 `specs/005-preview-before-start/tasks.md` 並完成重驗，人工未驗收不勾完成，不以剩餘任務多寡宣稱全專題完成。
- [x] T036 在 `specs/005-preview-before-start/validation.md` 整理 002/004 同學接線重點與交付狀態，核對契約、圖、README 及測試證據後準備功能分支 PR 的具體標題／內容與同學審查清單；實際 push／建立或合併 PR 依使用者授權執行，不因本任務自動合併，正式 003 未完成項明列交接。

## Dependencies & Execution Order

### Phase Dependencies

```text
speckit-analyze（阻擋項先處理）
  → T001 → T002 → T003 → T004 → T005
  → US1 T006–T012 → US2 T013–T019 → US3 T020–T029
  → T030/T031 → T032 → T033 → T034 → T035 → T036
```

### User Story Dependencies

- US1 依賴前置規則，不依賴 US2/US3 的完整流程；以新課堂及固定 catalog 獨立驗收預覽。
- US2 依賴 US1 的預覽發布與渲染；可用已建立 fixture 活動獨立檢查階段與權限，不要求先完成教師操作 UI。
- US3 依賴前置 guard／trigger 及 US1/US2 的活動流程；其競態、PREPARING finish 及階段 API 測試可用 fixture 個別執行，但共享路由及 JS 的修改循序整合。
- T003–T005 是最低限度共用不變量，US3 的任務補足 UI、準備中結束、指標一致性與端到端證據，非重做基礎。
- 各故事先寫測試，確認新行為差異，再依順序改程式；同檔後一任務依賴前一任務完成。T032 依賴三故事及文件／圖一致；人工驗收依賴可執行版本與自動檢查。

### Parallel Opportunities & Examples

僅在同一階段前置任務完成後使用下列並行機會，不跨故事同時修改共享檔案：

- US1：T006（Python 契約測試）與 T007（Node 渲染測試）可並行；T008–T010 在測試已定義後依路由→畫面順序整合。
- US2：T013（Python 權限／提交）與 T014（Node 同 id／復線）可並行；T015、T016 可按後端／前端分工，但需先固定測試預期，完成後合跑 T017–T019。
- US3：T020（switch）、T021（close）、T022（Node 教師操作）各改不同檔，可並行；T023–T025 修改共享程式需循序，T026–T028 按順序補整合證據。
- 最終：T030 文件與 T031 圖表核對可並行；T032 後才進行 T033／T034 人工驗收。

## Implementation Strategy

**MVP first**：先完成共用不變量及 US1，能展示建立後預覽、看得到但不能提交；只作階段展示，不把缺少 US3 準備中結束操作的版本當作本迭代正式發布。

**Incremental delivery**：US2 驗證統一開始與拒絕邊界，再由 US3 完成依序活動、準備中結束及空白開發 DB 驗收，最後合跑回歸與人工驗收。

**團隊分工**：可讓另一位組員核對測試預期、圖與介面；共享 classroom_routes.py／classroom.js 由同一工作序列整合，避免雙方同時重寫。commit 以可驗證階段分組，PR 由同學互審。

## Requirement Coverage

| 需求／成果 | 任務 |
| --- | --- |
| FR-001、FR-002；SC-001、SC-002 | T006–T012、T033 |
| FR-003、FR-004；SC-003、SC-004 | T007、T011、T013–T019、T033 |
| FR-005、FR-009；SC-005 | T008、T010–T011、T014、T016、T022、T025、T033 |
| FR-006 | T013、T015、T017、T021、T023–T024、T028 |
| FR-007 | T006、T009、T013、T019、T032 |
| FR-008；SC-006 | T003–T005、T020–T029、T034 |
| 憲章圖表／文件／驗收及交接 | T001–T002、T030–T036 |

## Notes

原始任務 36 項：Setup 2、Foundational 3、US1 7、US2 7、US3 10、Polish 7。自動驗證證據見 validation.md；T033/T034 人工驗收未完成。Convergence 追加項另列，未驗證事項不代勾。

## Phase 7: Convergence

- [ ] T037 依 SC-001/SC-004、US1/US2 驗收、憲章 V 及 T033/T034（partial），由組員完成教師及兩組學生的實際瀏覽器、5 秒同步計時、專用空白開發 DB 首次設定與重啟驗收，將姓名、日期、版本、預期／實際及去機敏證據補至 `specs/005-preview-before-start/validation.md`；問題修復後重驗，人工未做不勾選。此項追蹤既有人工缺口，不新增產品範圍。
