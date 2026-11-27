# Tasks: 活動結果回填與原課堂組名

**Input**: [spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/http.md)、[quickstart.md](quickstart.md)。
**Branch**: `codex/012-result-writeback`；日期：2026-11-27。
**Status**: 自動實作、技術檢核與本機交付準備完成；T043／T044、T047–T049 人工／真 Sheets／互審保持未完成，證據見 validation.md。
**Tests**: 依規格 SC-001–006、各故事驗收情境及憲章 V，列入錯場／越權／寫入恢復等必要自動驗證與人工驗收；不新增無關測試或整套框架。
**Organization**: 三個故事皆 P1，依 spec 順序交付；共用權限及原堂勝組安全檢查先於所有入口實作。

## Format / Path Conventions

每項 `- [ ] Tnnn [P?] [USn?] 說明與路徑`；路徑相對 repo 根目錄。`[P]` 僅代表指定前置完成後可處理不同檔案，不授權多代理或對外協作。共用檔案依相依順序串行修改。新增測試檔是待建立產物，並非已存在或已執行。

## Phase 1: Setup

**Purpose**: 固定開發基底、相依介面與需求追溯，不操作真 DB／key。

- [X] T001 核對當時最新已合併 master、PR14 基底與 `codex/012-result-writeback`，保留 011 及其他未提交檔；核對 `.specify/feature.json` 後將 SHA／工作區狀態寫入 `specs/012-result-writeback/validation.md`。
- [X] T002 取得並對照 #16 實作版本、組號儲存欄位及 formatter，核對 canonical 1–999 與「第 N 組」；記錄實際模組／函數／責任於 `specs/012-result-writeback/contracts/dependency-boundaries.md`，未取得不得自行猜舊名稱或複製 formatter。
- [X] T003 取得並對照 #20 的時間 helper、來源 tag／fallback 與合流 SHA，核對台北至分鐘（YYYY-MM-DD HH:mm，截取不進位）、naive UTC／offset／缺值／壞值；在 `specs/012-result-writeback/contracts/dependency-boundaries.md` 記錄 `notes/routes.py` 與 `static/classroom.js` 的小範圍接線責任。
- [X] T004 核對 `specs/012-result-writeback/contracts/dependency-boundaries.md` 的 C1-A–C 使用者雙組確認回報及適用範圍（行為確認門檻已滿足），後續若改行為須先取得變更確認，在 `docs/shared-requirements.md` 分開記已確認／待同步；執行唯讀 speckit-analyze，在對話呈現問題，影響實作的重大問題須先解決；只有另獲明確授權的後續編輯步驟才可將報告保存至 `specs/012-result-writeback/analysis.md` 或修改產物，analyze 本身不寫檔。

## Phase 2: Foundational

**Purpose**: 提供所有故事共用的原活動驗權與原堂勝組安全邊界。

- [X] T005 建立 `tests/integration/result_writeback_support.py` 的 temporary DB／受控 gateway fixture，包含兩教師、兩堂同號組、兩場同名活動／不同版本、關課與移除清單、全／部分無勝組，以及可計數讀寫的故障來源；不讀寫操作者 DB。
- [X] T006 在 `tests/unit/test_export_context.py` 建立 context／winner resolver 測試，涵蓋原教師／原堂、非課堂相容分支、canonical ID、缺失／跨堂／不可格式化組號、全 null winner 與批次查詢；記錄新增案例實作前的預期失敗。
- [X] T007 新增 `src/guided_notes/notes/export_context.py` 的原活動投影與授權查詢，沿用 requested_activity／owned_classroom 並驗活動 owner；遵守「原活動永久歸屬；課堂碼不作 join key；教師與課程／活動 owner 一致」，不過濾 CLOSED 課堂或清單移除。
- [X] T008 在 `src/guided_notes/notes/export_context.py` 實作批次原堂勝組 resolver，遵守「所有非空勝組須找到且可合法格式化；組 ID 與組號分開」及「正式課堂 snapshot 的勝組 ID 為 canonical 正整數字串；只做無損轉換查 INTEGER id，輸出保持原字串」；呼叫 T002 formatter，錯誤用 RESULT_INVALID／WINNER_GROUP_SCOPE_MISMATCH，不對舊獨立活動 synthetic ID 強套課堂整數限制。
- [X] T009 在 `src/guided_notes/notes/export_context.py` 區分新操作的嚴格校驗與既有歷史的安全錯誤投影；遵守「context 錯誤是顯示／新操作驗證狀態，不改持久化 operation status、winner 或 snapshot」，缺權限不可被容錯吞掉；跑 T006 並記錄於 `specs/012-result-writeback/validation.md`。

**Checkpoint**: T001–T009 完成且重大 analyze 問題已解決，才能開始故事實作。相依功能缺實際介面時保留該任務未完成，不建立第二套規則充數。

## Phase 3: US1 — 從選定活動進入回填（P1，MVP）

**Goal**: 目前／歷史結果一次操作建立所選活動預覽，刷新／返回不換場，不需手輸 ID。
**Independent Test**: 使用 fixture 兩場同名、共用講義不同版本／答案；逐場點預覽，驗 POST activity_id／CSRF、303／201、原版本固定，刷新 GET 不新增來源讀寫；驗未結束／未結算／全無勝組不同提示。無需先完成 US2 顯示模板或 US3 新恢復接線。

### Tests

- [X] T010 [P] [US1] 新增 `tests/integration/test_result_writeback_entry.py`，測目前／歷史選場、兩版本、額外勝組／座標拒絕、CSRF、來源前驗權、GET 重整無新增 Google 呼叫與三種狀態，記錄實作前失敗。
- [X] T011 [P] [US1] 新增 `tests/result-writeback-entry.test.cjs`，測結果按鈕原生 POST／hidden activity_id／CSRF、切換活動與晚到回應、localStorage 最近活動不同時仍綁已選 ID、返回 URL 的 activity_id 初始化原結果且刷新不換場、無效或跨堂選取不退回最新活動，學生無教師回填入口。

### Implementation

- [X] T012 [US1] 在 `src/guided_notes/notes/export_service.py` 將原 context／勝組驗證接入 create_saved_preview 來源呼叫之前並於保存前重驗；遵守「Preview activity/import/version 與原 reference 一致；snapshot 保持 validate_snapshot 嚴格 v1 形狀與 digest」，網路呼叫不得放入寫交易。
- [X] T013 [US1] 修改 `src/guided_notes/notes/routes.py` 的 export_form／create_export_preview，GET 帶 activity_id 僅驗權並回指定活動重試表單、不讀 Google；POST 保留欄位限制、HTML 303／JSON 201 與原版本綁定。
- [X] T014 [US1] 在 `src/guided_notes/static/classroom.js` 的目前／歷史結果建立「預覽回填講義」POST 表單，以當前 selection ID 與既有 CSRF 資料生成；維持選取序號／晚到回應保護，不讀 localStorage 或 current_activity_id 反查歷史。
- [X] T015 [US1] 移除 `src/guided_notes/notes/static/notes.js` 一般回填的 `[data-current-activity]` 最近活動自動填入；保留其他建立活動／命名／確認按鈕行為，指定活動只取已驗權頁面資料。
- [X] T016 [US1] 修改 `src/guided_notes/notes/templates/notes/export_form.html` 與 `src/guided_notes/notes/templates/notes/export_preview.html`，用 hidden 已選活動取代手輸 ID、無指定活動時導回課堂結果，分別提示未結束／未結算／全無勝組並停用全 skip 的 UI 確認，保留低階全 skip 契約及部分題略過。
- [X] T017 [US1] 依 `specs/012-result-writeback/contracts/http.md` 的返回契約，在 `src/guided_notes/notes/routes.py` 產生原課堂 URL＋activity_id，在 `src/guided_notes/notes/templates/notes/export_preview.html` 與 `src/guided_notes/notes/templates/notes/report.html` 使用；於 `src/guided_notes/workspace/routes.py` 驗教師、course／classroom／activity 歸屬並將原選取交給 `src/guided_notes/templates/workspace/classroom.html`，由 `src/guided_notes/static/classroom.js` 在原堂資料載入後初始化該結果，刷新／關課歷史仍保留原選取；無效／跨堂不退回最新活動，已保存預覽 GET 重驗原活動且不改來源觀察，並於 `tests/integration/test_result_writeback_entry.py` 驗返回頁權限。
- [X] T018 [US1] 執行 `tests/integration/test_result_writeback_entry.py`、`tests/result-writeback-entry.test.cjs` 及既有 `tests/integration/test_export_previews.py`，將 SC-001／Q01／Q02／Q06 的自動實際結果及來源呼叫數記入 `specs/012-result-writeback/validation.md`。

**Checkpoint**: 完成最小入口增量；尚未交付全部 #19。確認仍受基礎原堂校驗與既有回填保護。

## Phase 4: US2 — 辨識原課堂、勝組與歷史版本（P1）

**Goal**: 預覽及報告用一致課程／課堂／活動／講義版本／時間與「第 N 組」，關課或移除講義歷史仍正確。
**Independent Test**: 可直接用伺服器建立的預覽／報告 fixture，不依賴 US1 的結果按鈕；兩堂同號組各顯原答案，壞組別報錯、歷史報告保留，教師 B／學生不能越權。

### Tests

- [X] T019 [P] [US2] 擴充 `tests/unit/test_export_context.py`，驗第 1／42／999 組標籤與跨堂同號不混用、null winner 與壞 mapping 分開、時間欄位語意、無獨立結算時間不補造；記錄新增案例預期失敗。
- [X] T020 [P] [US2] 新增 `tests/contract/test_export_display_context.py`，驗教師 HTML／JSON 外加 activity_context／winner_group_label、原 snapshot exact keys／digest 不變，報告 mapping 錯誤 200 保留 context_error、未授權仍拒絕。
- [X] T021 [P] [US2] 新增 `tests/integration/test_export_context_history.py`，驗關課、加入碼重用、移除講義、同名活動／重用版本、教師 B／學生直接 GET／POST、缺失與跨堂勝組，並檢查來源呼叫及原結果不變。

### Implementation

- [X] T022 [US2] 擴充 `src/guided_notes/notes/export_context.py` 的講義／事件投影，遵守「原版本固定；講義名稱與來源分頁分開；不以最新版本或清單可見狀態替換」、「分別標建立／開始／結束；缺值按事件狀態及 #20 呈現；無獨立結算時間不補造」；`classroom_state` 僅 OPEN／CLOSED，獨立活動 classroom_id/title 為 null。
- [X] T023 [US2] 在 `src/guided_notes/notes/routes.py` 的 export_preview_data／operation_report 外加 activity_context 與 winner_group_label，遵守「快照不加 label/context；教師 DTO 外加投影；created_at 僅預覽時間」及「原活動／版本從 preview 取；updated_at 僅作業更新時間」；保留原 ID 欄位，壞 mapping 用 context_error，缺權限照原規則拒絕。
- [X] T024 [US2] 修改 `src/guided_notes/notes/templates/notes/export_preview.html`，按契約呈現課程→課堂→活動、講義版本／來源分頁、勝組標籤；winner_group_label 為 string|null，僅 no_winner 顯「無勝組／略過」，壞 mapping 明示錯誤且停用確認，內部 ID 放診斷 details。
- [X] T025 [P] [US2] 修改 `src/guided_notes/notes/templates/notes/report.html`，用原 context／標籤顯示明細，遵守「verified_at 是回讀驗證時間」；壞 mapping 保留原操作、狀態與明細並停用恢復，不將 label=null 一律顯為無勝組。
- [X] T026 [US2] 修改 `src/guided_notes/notes/routes.py` 及 `src/guided_notes/notes/templates/notes/export_form.html` 的已保存清單，顯示各自原活動名稱／課堂／必要時間，逐項驗活動與來源權限，不用 activity ID 作主要清單名稱或洩漏他人資料。
- [X] T027 [US2] 在 `src/guided_notes/notes/export_context.py` 接入 T003 的 #20 helper，並於 `src/guided_notes/notes/templates/notes/export_preview.html`、`src/guided_notes/notes/templates/notes/report.html` 接線台北至分鐘／安全缺值；保留原時間精度與排序，不新增時間核心或假的 settled_at。
- [X] T028 [US2] 在 `tests/integration/test_export_context_history.py` 增加惡意課程／課堂／活動／來源名稱及答案 escaping、UTC／offset／跨午夜／空值／壞時間頁面回歸，核對權限錯誤不被 context 容錯轉成成功。
- [X] T029 [US2] 執行 T019–T021／T028 與既有 `tests/contract/test_result_snapshot.py`，將 SC-002–004、Q03–Q05／Q07／Q12 的自動實際結果及 snapshot／rank／winner 不變證據記入 `specs/012-result-writeback/validation.md`。

**Checkpoint**: US2 可由直接預覽／報告獨立驗證；與 US1 整合時不再出現 ID 當組名或歷史選錯場。

## Phase 5: US3 — 確認、重新授權與安全恢復（P1）

**Goal**: 新入口沿用原逐項覆寫、冪等、source lease、回讀與恢復，授權成功／取消／失敗均保留原活動。
**Independent Test**: 使用直接建立的 ready preview／既有 operation fixture，模擬授權與來源故障，驗確認前與每批原堂校驗、先回讀恢復、原勝組／版本不變及已完成題零重送；不依賴 US1 按鈕。

### Tests

- [X] T030 [P] [US3] 在 `tests/integration/test_export_context_history.py` 增加正式課堂 confirm／recovery 的原堂勝組校驗、額外欄位拒絕、冪等重送回原報告及跨教師／學生拒絕案例，記錄新增案例實作前失敗。
- [X] T031 [P] [US3] 在 `tests/integration/test_writeback_restart.py` 增加正式課堂部分成功／未知／重啟恢復、來源移動與新衝突、重複恢復及已完成題不重送，保持既有 origin/root 與租約處理。
- [X] T032 [P] [US3] 在 `tests/contract/test_export_display_context.py` 增加真實活動成功／取消／失敗返回，並在 `tests/integration/test_sheets_reconnect_ui.py` 核對原活動 query／preview／operation 三種安全返回、成功／取消／失敗、不接受外站或寫入 URL、不自動重送，以及重新授權期間切換活動不改原操作的案例。

### Implementation

- [X] T033 [US3] 修改 `src/guided_notes/notes/writeback.py` 的 confirm／_snapshot／recovery_preview，在新 operation／Google 呼叫之前及每批寫入前加嚴格原堂勝組校驗，保留冪等回原報告、preview 消耗、租約、先回讀及原快照；不得把網路包進 DB 寫交易。
- [X] T034 [US3] 修改 `src/guided_notes/notes/routes.py` 的 error_response／確認／恢復接線，將 RESULT_INVALID 安全 reason 映射為明確提示；依原 activity／preview／operation 產生 allowlist 返回，保留未結束／未結算／來源／覆寫等各自錯誤與 HTTP code。
- [X] T035 [US3] 修改 `src/guided_notes/notes/templates/notes/error.html` 與 `src/guided_notes/notes/templates/notes/report.html` 的 PR14 重連元件接線，成功／取消／失敗都保留原活動，教師明確接續才新增操作，不放寬 `src/guided_notes/google_login/return_targets.py` 既有安全 allowlist。
- [X] T036 [US3] 核對並補齊 `src/guided_notes/notes/templates/notes/export_preview.html` 的恢復覆寫呈現：原已同意項目與此次新衝突分開、未同意不覆寫；保留既有提交按鈕恢復能力、no_winner 略過與回讀成功定義。
- [X] T037 [US3] 擴充 `tests/integration/test_export_context_history.py` 並回歸 `tests/unit/test_writeback_recovery.py` 與 `tests/integration/test_export_routes.py`，驗全 skip 低階確認仍零寫入、部分無勝組、原勝組／result_version 不變、來源變動不盲寫、已匹配答案不重送及新舊覆寫同意區別。
- [X] T038 [US3] 執行 T030–T032／T037 及既有回填／授權回歸，將 SC-005、Q08–Q11 的來源呼叫數、先回讀順序、冪等／重啟與結果不變證據記入 `specs/012-result-writeback/validation.md`。

**Checkpoint**: 三故事分別通過自動驗證；真實來源及人工驗收保持後續任務，未執行不可勾選。

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T039 執行 `specs/012-result-writeback/quickstart.md` 的相關回歸、完整 Python tests/unit／contract／integration 及 tests/*.test.cjs 的 Node 回歸；記錄版本、命令、總數、失敗修正／重驗於 `specs/012-result-writeback/validation.md`，保留舊獨立活動模式測試相容。
- [X] T040 在 `tests/unit/test_export_context.py` 與 `tests/integration/test_export_context_history.py` 驗批次勝組解析避免逐格查詢、已保存 preview／report GET 不新增 Sheets 呼叫，並比對原資料／答案／受理序列／順位／勝組／版本保持不變；將結果記入 `specs/012-result-writeback/validation.md`。
- [X] T041 核對程式與 `diagrams/012-component.puml`、`diagrams/012-class.puml`、`diagrams/012-sequence.puml` 的責任／關係／時序，必要修圖後 CLI 重渲染同名 PNG 並檢視；將實際命令、結果及程式對應記入 `specs/012-result-writeback/diagram-review.md`，不代填組員新審查。
- [X] T042 更新 `specs/012-result-writeback/quickstart.md`、`specs/012-result-writeback/contracts/dependency-boundaries.md`、`docs/shared-requirements.md` 與 `README.md` 的實際介面、啟動／驗收、相依版本及限制；檢查連結、格式及機敏內容，未完成驗收保持原狀態。
- [x] T043 依 `specs/012-result-writeback/quickstart.md` Q01–Q12 請教師與至少兩組學生完成人工操作，另核對教師 B 權限；在 `specs/012-result-writeback/validation.md` 記錄執行者、台北日期、SHA、預期／實際及失敗重驗，無回報保持未完成。
- [x] T044 使用來源範本副本及另一份題數／欄列不同的真 Sheets 測試副本執行 Q13，逐題核對勝組答案／無勝組略過及非目標值、合併、格式零變動；於 `specs/012-result-writeback/validation.md` 分開保存真來源與受控來源證據，無實測不得勾選。
- [X] T045 完成實作後先執行唯讀 speckit-analyze，在對話呈現結果；只有另獲明確授權的後續編輯步驟才可保存至 `specs/012-result-writeback/analysis.md` 或修正產物。再依 speckit-converge 的寫入權限處理缺漏並記錄 `specs/012-result-writeback/convergence.md`，將新工作追加到 `specs/012-result-writeback/tasks.md` 並補齊；人工未做仍保留未完成。
- [X] T046 核對差異與必要分段 commit，將 #16／#20 合流、共同確認、具名互審及剩餘限制彙入 `specs/012-result-writeback/validation.md`；依 `.github/pull_request_template.md` 準備 PR 內容，實際模板路徑若不同先核對，未獲授權不代發訊息，未審查不自行合併。

## Dependencies & Execution Order

```text
T001 → T002 → T003 → T004
  → T005 → T006 → T007 → T008 → T009
      ├─ US1: {T010,T011} → T012 → T013 → T014 → T015 → T016 → T017 → T018
      ├─ US2: {T019,T020,T021} → T022 → T023 → {T024,T025} → T026 → T027 → T028 → T029
      └─ US3: {T030,T031,T032} → T033 → T034 → T035 → T036 → T037 → T038
  → T039 → T040 → T041 → T042 → T043 → T044 → T045 → T046
```

圖中故事分支表示共用基礎後各自可驗證；實際建議 US1→US2→US3 串行交付。`routes.py`、context、preview／report 模板在多故事共用，禁止同時修改；跨故事無其他完成相依，但開始下一故事前先落實前一故事已變更的檔案內容。Q13 與完整端到端人工驗收必須在三故事整合後進行。

### Parallel Examples

- **US1**：T009 後，T010 Python 入口測試與 T011 Node 選場測試可並行；兩者都須使用 T005 固定 fixture／既定契約。產品實作串行。
- **US2**：T009 後，T019 unit、T020 contract、T021 history integration 可並行；T023 DTO 完成後，T024 preview 模板與 T025 report 模板可並行，合併後再做 T026／T027。
- **US3**：T009 後，T030 confirm、T031 restart、T032 reconnect 測試可並行（不同檔案）；T033–T037 接線串行，避免相同模板／routes 衝突。

`[P]` 任務沒有隱藏的未完成故事相依；所有並行都以已完成的 Phase 1／2 為共同前提。執行者若尚未取得相依功能或有檔案衝突，先回到前置任務，不將時間經過當作完成。

## Requirements Coverage

| 需求 | 主要任務 | 獨立驗收 |
| --- | --- | --- |
| FR-001–003 | T010–T018、T032、T034–T035 | US1／Q01–Q02／Q08 |
| FR-004–006 | T006–T009、T019–T029、T033 | US2／Q03／Q07／Q12 |
| FR-007 | T010、T016、T018、T037 | US1／Q06；全 skip 相容 |
| FR-008 | T007、T012、T017、T020–T021、T030 | US2／Q04–Q05 |
| FR-009–011 | T030–T038 | US3／Q08–Q11 |
| FR-012 | T003、T022、T027–T029 | US2／Q12 |
| FR-013 | T005、T037、T039–T044 | 三故事整合／Q13 |
| SC-001–006 | T018、T029、T038–T044 | 自動與人工證據分開 |

## Implementation Strategy

先完成 Setup／Foundation，再以 US1 作 MVP：結果直接選場、原權限與版本固定、三種狀態及不手輸 ID。此 MVP 供獨立檢查，不代表完整 #19 或可省略 US2／US3。接著 US2 補原堂標籤與歷史辨識，再 US3 驗確認／授權／恢復；每段完成可測試且審過差異後分段 commit，沿用現有套件與資料庫，不重建憑證或清歷史。最後才進行完整回歸、人工與真 Sheets、對圖／收斂／互審。

## Generation Validation

2026-11-27 Codex 實際檢查：共 46 任務，Setup 4、Foundation 5、US1 9、US2 11、US3 9、Polish 8；9 項標記 [P]。T001–T046 連號、checkbox／標籤／檔案路徑及文件連結檢查通過，所有任務初始未勾選；`git diff --check` 通過。`.specify/extensions.yml` 不存在，before_tasks／after_tasks 無 hook 可執行。原始相依確認、人工驗收與真 Sheets 狀態未因產生 tasks 而改變；未執行產品測試或產品實作。

## Phase 7: Convergence

2026-11-27 程式對照 13 FR、6 SC、11 個故事驗收情境、六項憲章原則與既有 46 任務。未發現新增未建程式範圍；以下為缺少的交付證據，與原 T043／T044 及技術互審保持追溯，不以自動結果代勾。

- [x] T047 完成並記錄教師與至少兩組學生、第二教師的 Q01–Q12 真人驗收於 `specs/012-result-writeback/validation.md`，對照 T043／US1–US3／Constitution V（partial，HIGH）；包含執行者、版本、台北日期、預期／實際及失敗重驗。
- [x] T048 使用兩份不同配置的真 Sheets 測試副本執行 Q13 並將逐格勝組／無勝組略過及非目標內容、合併、格式核對記入 `specs/012-result-writeback/validation.md`，對照 T044／SC-006／Constitution III、V（partial，HIGH）；受控 gateway 不代替真來源證據。
- [ ] T049 請另一位組員檢查本輪程式、三圖與相依接線，將實際具名審查結果及必要修正重驗記入 `specs/012-result-writeback/diagram-review.md`、`specs/012-result-writeback/validation.md`，對照 Constitution II、VI（partial，MEDIUM）；未獲授權不代發訊息，未回報不代勾。

## 2026-11-27 真人與真來源驗收補證據

T043／T047及T044／T048依docs/issues-19-20-manual-acceptance.md的逐段實際使用者回報完成。故障為明列受控工具／合成回歸，不冒認Google自然逾時；實際副本回填／回讀、非目標格與合併格式由使用者核對。T049另一組員本輪程式／三圖技術互審仍未回報，保持未勾；AI自查或使用者功能操作不代替該審查。
