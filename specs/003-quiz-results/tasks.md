---
description: "003 正式搶答與結果的實作、驗證與交付任務"
---

# Tasks: 003 正式搶答與結果

**分支** `codex/003-quiz-results`　**開發基底** `39d6275`　**追蹤** [Issue #8](https://github.com/Afra0704/se2026-group20-speckit/issues/8)

**設計依據** [spec.md](spec.md) · [plan.md](plan.md) · [research.md](research.md) · [data-model.md](data-model.md) · [介面契約](contracts/quiz-interfaces.md) · [quickstart.md](quickstart.md) · [圖表審查](diagram-review.md)

`[P]` 表示同批前置完成後可平行撰寫，所列測試檔各自獨立。新增的回歸測試先證明基底缺少預期行為，再由對應實作使其通過。所有任務依實際完成及驗證結果勾選。

## Phase 1 — 開發準備

- [X] T001 按 `specs/003-quiz-results/plan.md` 核對分支、`.specify/feature.json`、PR #7 基底與工作樹，並在 `specs/003-quiz-results/validation.md` 記錄執行者、日期、版本及圖意審查證據。
- [X] T002 依 `pyproject.toml`、`uv.lock` 與 `specs/003-quiz-results/quickstart.md` 取得 Python 3.13 環境，使用暫存 DB 跑基底 Python／Node 測試，在 `specs/003-quiz-results/validation.md` 記錄命令與既有失敗。

## Phase 2 — 共用基礎

- [X] T003 在 `tests/integration/test_quiz_schema.py` 定義正常啟動及 `init-db` 可重跑、保留 Google instance／授權密文／課程／課堂／講義歷史，以及舊 CLOSED 資料在初始化時不產生結算待辦或發布資料的驗收。
- [X] T004 在 `src/guided_notes/quiz/schema.sql` 定義受理操作、有效指標及結算待辦／發布。受理序列為「單調且唯一的伺服器 `accept_seq`」，「活動、題目、組別、操作識別唯一」；「每個 `(activity_id, question_id, group_id)` 至多一個有效受理識別」，指標只能指向同範圍；結算「每活動一筆，CLOSED 同交易新增待辦」，待辦轉成已發布後不可改回。活動與題目對應既有固定 `(activity_id, question_id)`。
- [X] T005 在 `src/guided_notes/db.py` 將 `src/guided_notes/quiz/schema.sql` 接入啟動與 `init-db`，沿用同一 DB 及可重跑的建表流程，使 `tests/integration/test_quiz_schema.py` 通過。
- [X] T006 在 `src/guided_notes/activities/submission_context.py` 分離固定題目及原組別查閱資格、新送答的 LIVE／目前活動／可提交資格。正式課堂從課堂資格取得組別，非課堂相容入口從原 `activity_groups` 取得，兩種群組來源不可互換。

## Phase 3 — US1 以組別提交完整答案（P1，MVP）

**目標**：正常啟動即可受理單題與完整題組，教師 LIVE 能看各組提交狀況。

**獨立驗證**：教師開一場含單題和兩格題組的活動，兩組使用不同工作階段送答。準備中與跨範圍拒絕；重試保留舊受理；主動重送只留下新有效答案；教師見進度，學生無法取得他組資料。

- [X] T007 [P] [US1] 在 `tests/contract/test_quiz_submission.py` 驗證唯一操作識別、缺漏／空白／重複／未知小題、原字串保留、教師／他組／錯誤 CSRF、準備中／過時活動／關課後的新送答拒絕。
- [X] T008 [P] [US1] 在 `tests/integration/test_quiz_replay.py` 驗證 A 受理回應遺失後用同識別重試、同識別不同內容衝突、主動再送相同文字仍是新操作、已被取代的舊收據重試不復活；新送答失敗保留原有效指標。
- [X] T009 [P] [US1] 在 `tests/quiz-submission.test.cjs` 驗證課堂與相容前端捕捉原 payload、送出期間防連點、斷線重試共用識別、主動再送取得新識別。同分頁重整後模擬還原原活動與組別，驗證不自動送答、手動重試沿用原 key 與 payload、收到明確回覆清除暫存，活動或組別不符時不提供重試。
- [X] T010 [P] [US1] 在 `tests/contract/test_quiz_progress.py` 驗證 LIVE 只有獲授權教師得到 `question_id`、`group_name`、`submitted`，包含已加入未提交組別；學生不取得其他組答案、順位或勝組。
- [X] T011 [US1] 在 `src/guided_notes/quiz/repository.py` 實作查收據、受理序列及有效指標讀寫。相同操作比對以排序後的小題識別及原字串為準。新答案成功才在同一交易取代有效指標，重試不寫入新受理。
- [X] T012 [US1] 在 `src/guided_notes/quiz/activity_routes.py` 與 `src/guided_notes/quiz/submission_gateway.py` 傳入正式請求的 UUID `Idempotency-Key`，先核對原組別查閱資格再判斷重放；新操作重驗 LIVE 並沿用 `ACCEPT_SUBMISSION(db, context, answers)`。答案鍵與固定題目的小題集合完全一致；每個值為去空白檢查後非空的字串，保存與交付仍用原字串。commit 後回 201 accepted；同 key 不同內容回 409 `SUBMISSION_REPLAY_CONFLICT`。
- [X] T013 [US1] 在 `src/guided_notes/quiz/results_gateway.py` 與 `src/guided_notes/quiz/repository.py` 接上正式 `GET_PROGRESS`，查固定題目、組別資格及目前有效提交。投影限定契約允許欄位，保留已加入未提交的組別。
- [X] T014 [US1] 在 `src/guided_notes/__init__.py` 註冊正常啟動的正式受理及進度 provider，保留明確覆寫及 `None`。更新 `tests/contract/test_runtime_providers.py` 驗證正常啟動可送答及明確停用才不可用。
- [X] T015 [US1] 在 `src/guided_notes/static/classroom.js` 與 `src/guided_notes/static/activity-sync.js` 接入送答 UUID、原始 payload、重試與重新提交入口。送出前以 `sessionStorage` 暫存該操作及範圍；同分頁重整且後端確認原活動、原組別與合法資格後提供手動重試，不自動送答。明確受理或拒絕後清除暫存；上下文不符不送出。未受理或未知狀態用可見提示回報。
- [X] T016 [US1] 在 `src/guided_notes/static/classroom.js` 與 `src/guided_notes/static/activity-sync.js` 讓教師選定的 LIVE 活動隨既有同步更新進度，核對活動、角色及切換守衛。
- [X] T017 [US1] 執行 `tests/contract/test_quiz_submission.py`、`tests/contract/test_quiz_progress.py`、`tests/contract/test_runtime_providers.py`、`tests/integration/test_quiz_replay.py`、`tests/quiz-submission.test.cjs`，將單題／題組、保護範圍與回歸結果寫入 `specs/003-quiz-results/validation.md` 作為第一段提交依據。

## Phase 4 — US2 截止、順位、結算及結果檢視（P1）

**目標**：在截止兩種先後順序下，得到唯一且不可變的結果。課堂仍開放時學生也可看已結束活動。

**獨立驗證**：用獨立活動及暫存 DB 控制關閉與提交的順序，操作 A、B、A 的主動重送及同次重試，注入結算故障後重啟，再用教師與兩組學生分別讀取。

- [X] T018 [P] [US2] 在 `tests/integration/test_activity_cutoff.py` 新增正式 provider 與兩連線同步屏障，驗證提交 commit 先與結束 commit 先，涵蓋關課隱含結束，以及較早抵達但未受理的提交不計入。
- [X] T019 [P] [US2] 在 `tests/integration/test_quiz_settlement.py` 驗證同時提交、A／B／A 新操作與重試的兩種排行、部分題目與全部無勝組、待辦故障回滾、重啟恢復、重複發布以及同名活動／講義重用隔離。
- [X] T020 [P] [US2] 在 `tests/contract/test_classroom_results.py` 與 `tests/contract/test_quiz_visibility.py` 驗證四種結果狀態、關課後原瀏覽器及跨組／跨課堂隔離、投影欄位與無勝組。按 D22 驗證兩個歷史查閱入口，課堂 OPEN 時的新瀏覽器合法加入同名組別後可讀已結算結果，課堂 CLOSED 且無原證明時拒絕。
- [X] T021 [P] [US2] 在 `tests/quiz-results.test.cjs` 驗證逐小題標號、原文字安全呈現、舊摘要相容、課堂仍開放時查歷史及切換前的延遲結果不能覆蓋目前畫面。
- [X] T022 [US2] 在 `src/guided_notes/activities/teacher.py` 與 `src/guided_notes/quiz/repository.py` 讓 `transition` 寫入 CLOSED 時在同一交易建立該活動唯一待辦；保留 PREPARING 直接結束及已結束不可重開。
- [X] T023 [US2] 在 `src/guided_notes/quiz/settlement.py` 按 `accept_seq` 遞增對每題有效指標編列名次，首組勝出。以活動固定題目與原字串產生每題 unit、`no_winner` 及整數 `contract_version: 1`。用 `src/guided_notes/notes/repository.py` 的 `catalog_row` 依活動教師、`import_id`、`import_version` 讀完整歷史 DTO，再用 `src/guided_notes/notes/models.py` 的 `validate_snapshot` 驗證；不得以最新清單或 Google 來源替代。失敗保留待辦。
- [X] T024 [US2] 在 `src/guided_notes/quiz/repository.py` 與 `src/guided_notes/quiz/settlement.py` 以單一交易發布全部結果、快照及不可變版本，恢復前重驗 CLOSED、固定題目及待辦。既有發布直接讀取；故障回滾後保留待辦。
- [X] T025 [US2] 在 `src/guided_notes/activities/classroom_routes.py` 與 `src/guided_notes/activities/teacher_routes.py` 串接關閉成功提交後的結算嘗試，包含單活動、關閉課堂及相容入口。結算失敗保留已確認的活動截止及待辦。
- [X] T026 [US2] 在 `src/guided_notes/__init__.py` 與 `src/guided_notes/quiz/settlement.py` 接上正常啟動的有限批次恢復及正式 `GET_SETTLED_RESULTS`，明確提供的替代 provider／None 保留。無待辦的舊活動維持沒有正式結果。
- [X] T027 [US2] 在 `src/guided_notes/quiz/results_gateway.py` 先驗權限、再嘗試恢復待辦並讀取結果。保留 active／pending／settled，新增 unavailable 區分舊資料。逐欄投影教師各組與學生本組，新增逐小題結果並保留舊摘要相容。
- [X] T028 [US2] 在 `src/guided_notes/activities/classroom_routes.py` 與 `src/guided_notes/quiz/results_gateway.py` 對齊課堂歷史清單與單場結果的權限。課堂 OPEN 時按 D22 接線，允許新加入者查閱。關課後沿用 D16，涵蓋原瀏覽器證明、待結算恢復與無正式結果。
- [X] T029 [US2] 在 `src/guided_notes/static/classroom.js` 與 `src/guided_notes/static/activity-sync.js` 顯示不同結算狀態及逐小題結果，保留舊摘要。課堂仍開放時提供已結束活動入口，輪詢可跟進已選活動的結算狀態。
- [X] T030 [US2] 跑 `tests/integration/test_activity_cutoff.py`、`tests/integration/test_quiz_settlement.py`、`tests/contract/test_classroom_results.py`、`tests/contract/test_quiz_visibility.py`、`tests/quiz-results.test.cjs`，將截止、名次、結算失敗／重啟與可見性證據寫入 `specs/003-quiz-results/validation.md`，作為第二段提交依據。

## Phase 5 — US3 將正式結果交給 001 回填（P2）

**目標**：001 從正式 003 取得已結算活動的相容快照，完成預覽、確認、回填、回讀與必要的恢復。

**獨立驗證**：先以正式受理／結算及受控 Sheets 跑現有 001 路徑，再用教師、兩組學生與兩份版型不同的講義副本重驗。檢查無勝組略過、原字串、歷史版本與非目標資料。

- [X] T031 [P] [US3] 在 `tests/integration/test_google_notes_integration.py` 增加正式 003 受理與結算案例，保持 Sheets 層受控。證明含整數 `contract_version: 1` 的快照通過 001 既有驗證，並驗證預覽、確認、實際寫入清單、原字串回讀、多小題及無勝組略過。
- [X] T032 [P] [US3] 在 `tests/integration/test_workspace_history.py` 驗證另存新版或移除講義後，正式 provider 仍用活動原固定題目結算及原歷史清單驗證／回填。在 `tests/integration/test_writeback_restart.py` 驗證回填中斷後仍使用原結算版本。
- [X] T033 [US3] 在 `src/guided_notes/quiz/results_gateway.py` 完成 `get_ended_snapshot` 的教師驗證與待辦恢復接線。未結束回 `ACTIVITY_NOT_ENDED`，無可交付快照回 `RESULT_NOT_READY`，成功回完整 v1。核對 `src/guided_notes/notes/routes.py` 與 `src/guided_notes/notes/models.py` 的既有交接及嚴格驗證。
- [X] T034 [US3] 跑 `tests/integration/test_google_notes_integration.py`、`tests/integration/test_workspace_history.py`、`tests/integration/test_writeback_restart.py`，在 `specs/003-quiz-results/validation.md` 記錄受控證據，作為第三段提交依據。
- [ ] T035 [US3] 依 `specs/003-quiz-results/quickstart.md` 與 `specs/001-guided-notes/quickstart.md` 由教師及兩組學生在真實 Sheets 副本上完成活動到回讀。用來源範本副本及另一份題數或欄列不同的講義，驗證位置變動重檢、無勝組略過、非目標欄位與格式，將真人證據寫入 `specs/003-quiz-results/validation.md`。

## Phase 6 — 全功能驗證與交付

- [X] T036 依 `specs/003-quiz-results/quickstart.md` 跑整套 pytest 與 Node 測試，覆蓋 005–008、既有 Google 資料及原瀏覽器權限。將命令、版本、次數、狀態與失敗重驗寫入 `specs/003-quiz-results/validation.md`。
- [ ] T037 依 `specs/003-quiz-results/quickstart.md` 執行教師與兩組學生的真人權限、更新計時、重連和歷史驗收。記錄環境、兩秒觀察目標及實際結果至 `specs/003-quiz-results/validation.md`。
- [X] T038 在 `specs/003-quiz-results/diagram-review.md` 逐一對照成品與 `diagrams/003-component.puml`、`diagrams/003-class.puml`、`diagrams/003-sequence.puml`。如有依確認規則必要的變更，使用 PlantUML CLI 同步重繪三類對應 PNG，記實際命令與核對。
- [X] T039 依 `README.md` 與 `specs/003-quiz-results/quickstart.md` 核對實際啟動、功能狀態與 Demo 流程，並在 `specs/003-quiz-results/validation.md` 記錄已完成與未測情境及去機敏證據。
- [ ] T040 依 `.specify/memory/constitution.md` 完成合併前的 Analyze／Converge，將結果寫入 `specs/003-quiz-results/analysis.md` 與 `specs/003-quiz-results/validation.md`。修正交付缺口並保留仍待驗證項目。
- [ ] T041 依 `specs/003-quiz-results/plan.md` 與 `specs/003-quiz-results/validation.md` 備妥分段 commit 的證據與 PR 內容，由成員推功能分支與組員互審。PR 關聯 Issue #8，依實際驗收判斷可否關閉。

## 相依關係與可並行工作

- **主線**：T001–T002 → T003–T006 → US1（T007–T017）→ US2（T018–T030）→ US3（T031–T035）→ T036–T041。US2 發布依賴 US1 的正式有效提交；US3 使用 US2 的結算來源，受控與真人流程各自保留驗收證據。
- **US1**：T006 完成後，可並行準備 T007–T010；受理儲存完成後接提交與進度，再接 provider 及瀏覽器。
- **US2**：US1 的受理與進度通過後，可並行準備 T018–T021；待辦、發布、恢復與回應通過後再接前端。
- **US3**：US2 完成後，可並行準備 T031、T032；T033 接線後先做 T034 受控整合，再做 T035 真人驗收。

## 規格追溯

| 規格 | 任務 |
| --- | --- |
| FR-001 至 FR-004、FR-007、SC-001 | T006–T017、T018、T020 |
| FR-005 至 FR-006、FR-008 至 FR-009、FR-011、SC-002 至 SC-003 | T003–T005、T018–T030、T036–T037 |
| FR-010、SC-004 | T023–T024、T031–T035 |
| 憲章人工對圖、互審與收斂 | T035–T041 |

## 交付策略

MVP 是 US1，先驗證教師能看到兩組進度、學生可正式提交與安全重試。接著交付截止與結算，再完成結果投影和 001 回填的整體驗收。依 T017、T030、T034 分段留下測試與 commit 紀錄，真人與全套驗收完成後彙整為一個 PR。
