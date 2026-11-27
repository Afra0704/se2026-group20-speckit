---
description: "011 時間顯示一致性的依賴順序任務"
---

# Tasks: 時間顯示一致性

**Input**: 本目錄的spec、plan、research、data-model、contracts、quickstart，以及 `diagrams/011-time-display-*`。

**Created**: 2026-11-27（Asia/Taipei）；基底`e9a29c7`，Issue #20。原三圖依使用者回報已由同學審閱；姓名／獨立紀錄未提供，2026-11-27使用者回報OpenSpec已確認時間呈現政策，並指定顯示到分鐘；確認者姓名及獨立紀錄待補，其他未確認事項保持。

**本輪狀態**：只產生任務，全部未完成。沒有實作、產品測試、DB操作、commit或push。共享checkout仍為`codex/012-result-writeback`；setup-tasks以程序限定`SPECIFY_FEATURE_DIRECTORY=D:/os_final/specs/011-time-display`、`SPECIFY_FEATURE=codex/011-time-display`、`SPECIFY_FEATURE_NO_PERSIST=1`解析，不切分支、不改feature.json、不修改012／#16／#17。

**Tests**: 使用者與規格明確要求自動及人工驗證，故列測試任務。實作時先寫相應回歸並記錄修正前失敗，再實作；以下預期不是已執行證據。

## Format: `[ID] [P?] [Story] Description`

- 全部任務用未勾checkbox、連續ID、明確路徑；故事階段必須有US標籤。
- `[P]`僅表示列明前置完成後，可與同組不同檔案任務並行；不允許同時改同檔，也不自動啟動代理。
- 路徑相對於未來011自己的repo根目錄；本輪只寫本tasks.md。

## Phase 1: Setup — 基底、協作與驗證準備

**Goal**：隔離011的實作位置，記錄協作與測試來源。這些是未來實作的前置，現在不執行。

- [X] T001 在 `specs/011-time-display/validation.md` 記錄未來011獨立checkout／worktree、完整基底SHA、dirty狀態及功能目錄，依 `specs/011-time-display/plan.md` 保留共享012及所有未提交文件；不以reset、清DB或覆蓋他人工作切換。
- [X] T002 與#19／012核對 `specs/011-time-display/contracts/teacher-time-metadata.md` 的presenter簽名、欄位、notes/routes.py／模板／classroom.js責任與合併順序，記錄真實確認／未確認來源；未對齊時可先做獨立核心，但T015、T016、T037、T038、T041共用接線須等待。
- [X] T003 在 `specs/011-time-display/validation.md` 依 `specs/011-time-display/source-inventory.md` 建立證據與受控樣本基準，區分原問題未重現、靜態風險、設計選擇、受控與真人觀察，不直接記為已重現八小時錯誤。
- [X] T004 在 `specs/011-time-display/quickstart.md` 核對Python3.13、Node、暫存DB／合成Google fixture、POSIX及受控瀏覽器可用性，記錄平台限制；保留原私有設定，不改系統時區／時鐘，不把Windows單設TZ當真跨環境。

## Phase 2: Foundational — 共用契約與純讀取模型

**Prerequisite**：T001～T004已記錄。T002記錄未確認不等於接線獲准；核心可先行，共用檔案仍等待。

**Goal**：建立共用型別、來源政策及回歸，不另建DB或身分系統。

- [X] T005 [P] 在 `tests/contract/test_time_display_contract.py` 先寫獨立DisplayTime的序列化／狀態形狀回歸，核對label／status／text／instant_utc與known／null約束；只驗基礎模型，不要求尚未接線的history路由或三事件sidecar。教師完整metadata由T011測試，模型未建立時記錄預期失敗。
- [X] T006 [P] 在 `tests/unit/test_time_views.py` 先寫來源政策、生命週期輸入與ReadbackTimeView約束，核對scope只在驗權後組合、query／body不能指定可信來源、非verified沒有回讀時刻；與T005不同檔可並行。
- [X] T007 在 `src/guided_notes/time_display.py` 建立不可變輸入／觀察／顯示型別，逐字遵守data-model約束：「raw_value: str | None」「其他型別轉 invalid，不自動轉字串或 epoch」；event_kind為「created、started、closed、confirmed、preview_created、operation_updated、readback」；occurrence為「occurred、not_started、not_ended、skipped_start、unknown」；scope為「原教師／課堂／活動／回填作業關聯，僅在原驗權後組合；不新建權限系統」；instant為「instant: aware datetime | None」，保留原微秒不寫DB；status為「known、not_started、not_ended、skipped_start、missing、invalid、unknown_timezone」；label為「固定事件標籤，不接受原值提供 HTML」，text的known格式「YYYY-MM-DD HH:mm」、其他為契約中文提示；instant_utc遵守「known 時為明確 UTC ISO datetime，保留原精度；其他為 null。不取代原欄位，非排行依據」。依T005驗證，不新增套件。
- [X] T008 在 `src/guided_notes/time_views.py` 建立server固定SourcePolicy與唯讀輸入：sqlite_utc遵守「只接受原 SQL 秒級格式並明確附 UTC」，offset_required遵守「不推定缺失 offset，顯示 unknown_timezone」，unverified遵守「有明確 offset 可解讀；naive 不猜測」及「政策不由請求 query／body 或瀏覽器提供」；定義ReadbackTimeView的verification_status、`time: DisplayTime | null`、text，遵守「原狀態非verified時time=null且text為『尚未驗證』；原狀態為verified時呼叫presenter，缺時間得到missing」，不改writeback JSON，依T006驗證。
- [X] T009 在 `specs/011-time-display/source-inventory.md` 核對可信SQL UTC欄位、notes offset_required、原phase_version及無settled_at證據；把T005／T006紅綠結果與未做項目記至 `specs/011-time-display/validation.md`，確認模型不讀DB／Google／目前時間，不把任意naive notes值當可信UTC。

**Checkpoint**：契約、型別及來源界線可驗證；核心工作可進US1。

## Phase 3: User Story 1 — 教師看懂正確活動時間 (Priority: P1) — MVP slice

**Goal**：歷史明示建立、開始、結束及台北時區，直接結束的語意正確。

**Independent Test**：以已知UTC、+08:00、可信SQL UTC及不同活動階段，核對同一時刻、三標籤與刷新後原值不變。

### Tests first

- [X] T010 [P] [US1] 在 `tests/unit/test_time_display.py` 寫Z、正負offset、已為+08:00與可信SQL UTC的已知樣本回歸，核對固定台北至分鐘、保留原微秒、不進位、不讀目前時間／主機本地解讀，先記失敗。
- [X] T011 [P] [US1] 在 `tests/integration/test_time_display_routes.py` 用暫存DB寫教師raw欄位保留、三事件sidecar的version=1／timezone=Asia/Taipei／utc_offset=+08:00與直接結束回歸，涵蓋PREPARING/version0、LIVE、CLOSED/version1、有開始值與缺可信版本證據，不動日常DB。
- [X] T012 [P] [US1] 在 `tests/classroom-time-display.test.cjs` 寫建立／開始／結束標籤、台北區塊、textContent與不做Date本地化回歸，保留原selection／generation／按鈕與晚到歷史防護。

### Implementation and integration

- [X] T013 [US1] 在 `src/guided_notes/time_display.py` 實作 `present_time(raw_value, *, event_kind, source_policy='unverified', occurrence='unknown') -> DisplayTime`，先解讀aware瞬間再轉固定UTC+08:00，不對已有offset再加8小時；輸出YYYY-MM-DD HH:mm、年份四位其餘兩位、到分鐘截取，使T010通過，不讀目前時間、不改raw。
- [X] T014 [US1] 在 `src/guided_notes/time_views.py` 建活動adapter，只讀phase／phase_version；逐字遵守「started_at，PREPARING → not_started」「closed_at，PREPARING／LIVE → not_ended」「started_at，LIVE → missing」「started_at，CLOSED，可信初始化及 phase_version=1 → skipped_start」「started_at，CLOSED，但無上述證據／version≥2 → missing」「closed_at，CLOSED → missing」；非空壞值或階段矛盾為invalid，不能只憑null宣稱從未開始。
- [X] T015 [US1] T002實際約定完成後，在 `src/guided_notes/activities/classroom_routes.py` 原history驗權／SELECT後加time_display，內部讀phase_version但不改counter；外層遵守「version=1」「timezone=Asia/Taipei」「utc_offset=+08:00」，三事件各依DisplayTime；raw欄位、ORDER BY、owned_classroom／require_teacher原樣，不額外查DB或擴充學生DTO。
- [X] T016 [US1] T002完成且T015可用後，在 `src/guided_notes/static/classroom.js` 的activityList及 `src/guided_notes/templates/workspace/classroom.html` 呈現三事件和一次時區說明；用server text及textContent，缺少／未知metadata版本顯示「時間資料尚未提供」，不回退raw到本地Date，不改#16／#17邏輯。
- [X] T017 [US1] 執行T010～T012核心、教師HTTP及Node回歸，將修正前失敗、命令、版本、實際結果記至 `specs/011-time-display/validation.md`；驗原值與歷史選取保持，失敗先修本輪修改再重驗。
- [ ] T018 [US1] 依 `specs/011-time-display/quickstart.md` M02／M03由教師與兩組學生人工核對一般活動及準備中直接結束，記操作前後電腦時間區間、台北顯示及直接結束提示；顯示分鐘須落在區間兩端各截取至分鐘的含端點範圍，非任意允許一分鐘誤差至 `specs/011-time-display/validation.md`；時計不同步另記，未做不勾。
- [ ] T019 [US1] 在 `specs/011-time-display/validation.md` 整理US1獨立驗收及第一段提交範圍，核對FR001／002／003與三圖Access→Read→Meaning→Display；標明US2／US4仍待驗，不把MVP畫面可用當整體完成。

## Phase 4: User Story 2 — 新舊歷史的同一時刻一致 (Priority: P1)

**Goal**：可信舊UTC正確呈現；缺值、壞值、不明來源安全提示；跨環境證據分開取得。

**Independent Test**：同瞬間不同表示一致，未知naive不猜測，壞資料不500，跨日與重載不改原值。

- [X] T020 [P] [US2] 在 `tests/unit/test_time_display.py` 加解析邊界回歸，逐字覆蓋「可帶1～6位小數秒」「aware 只接受 Z 或 ±HH:mm」「超過128字元輸入為 invalid」及可信naive僅「YYYY-MM-DD HH:mm:ss」；測date-only、week-date、epoch／布林、非空首尾空白、閏秒、24:00、錯日期／偏移、跨月／年、小年份補零與轉換溢位，不夾邊界或進位。
- [X] T021 [P] [US2] 在 `tests/unit/test_time_views.py` 加未知來源、notes naive、空白／缺值、CLOSED缺開始、LIVE缺開始與階段矛盾回歸，逐字遵守「非空壞值優先回 invalid，不以 null／未發生提示掩蓋」，不能補現在時間。
- [X] T022 [US2] 在 `src/guided_notes/time_display.py` 依T020補齊完整格式、型別／長度檢查及格式／溢位的安全結果；空值按事件缺值規則處理，非可信但格式合法naive為unknown_timezone，known之外instant_utc全為null；保留aware偏移，不依主機預設或寬鬆parser。
- [X] T023 [US2] 在 `src/guided_notes/time_views.py` 依T021補齊不明來源與直接結束證據不足的保守回退，created／notes既有對象缺時為missing，不用其他事件補造；query／body不能切換為sqlite_utc。
- [X] T024 [US2] 在 `tests/integration/test_time_display_routes.py` 的隔離fixture放入損壞、缺值、不明naive及同名活動，驗各格提示、頁面200、原關聯與raw保持；在 `tests/classroom-time-display.test.cjs` 補缺／未知metadata版本回歸，不改日常資料製造錯誤。
- [ ] T025 [P] [US2] 在 `tests/integration/test_time_display_process_tz.py` 建真正POSIX隔離子程序矩陣，分設UTC／Asia/Taipei／另一TZ並呼叫tzset，跑同一樣本，父程序及系統設定不改；Windows不支援明確skip，但真矩陣未做時本任務仍未完成，不能用mock／單設TZ抵作。
- [X] T026 [P] [US2] 以可用受控獨立瀏覽器context或既有不同時區環境，依 `specs/011-time-display/quickstart.md` 核對server text不再本地化，將工具／版本、至少UTC／台北／另一時區結果記至 `specs/011-time-display/validation.md`；不改操作電腦時區，缺環境不勾。
- [X] T027 [US2] 執行T020／T021／T024本機回歸，將T025真POSIX、T026瀏覽器及M01原偏差定位分開記至 `specs/011-time-display/validation.md`，核對SC001～003；找不到原畫面保持未重現，不用受控樣本冒認自然根因。

## Phase 5: User Story 4 — 保留原事件與結果 (Priority: P1)

**Goal**：證明只是顯示修改，不改資料、授權、截止、順位、勝組或版本。

**Independent Test**：以暫存007型DB／合成授權，比較顯示、刷新、重跑初始化與重啟前後的精確原值及結果；不同客戶端時鐘仍依受理序列排名。

- [X] T028 [P] [US4] 在 `tests/integration/test_time_display_preservation.py` 建教師、課程、講義、合成Google密文、學生資格、有效提交與已公布結算的暫存fixture，比較raw timestamps、原答案、accept_seq、順位、勝組、snapshot、result_version於顯示／重新初始化／重啟前後完全相同；顯示不得新增schema、原事件寫入、Sheets或結算。
- [X] T029 [P] [US4] 在 `tests/contract/test_time_display_contract.py` 加匿名、第二教師、跨堂、關課學生拒絕，以及CatalogDTO／snapshot嚴格驗證和原JSON欄位不變回歸；metadata不可含raw_value、來源診斷、憑證或其他組資訊，phase_version／顯示文字不進結果。
- [X] T030 [US4] 執行T028／T029，檢查 `src/guided_notes/activities/classroom_routes.py`、`src/guided_notes/time_views.py`、`src/guided_notes/time_display.py` 的唯讀及驗權；失敗只修本輪呈現／接線，不以改schema、writer、受理／結算provider或放寬權限通過，紅綠結果記至 `specs/011-time-display/validation.md`。
- [X] T031 [US4] 在 `tests/integration/test_time_display_preservation.py` 追加並執行不同客戶端時鐘／時區、重複結束、關課一併結束及刷新回歸，驗deadline、原結束時間、排序、授權expires、lease、presence TTL與網路預算不變，ORDER BY不改按text；記至 `specs/011-time-display/validation.md`。
- [ ] T032 [US4] 依 `specs/011-time-display/quickstart.md` M04／M06由教師與兩組學生核對歷史、重連、同名活動、關課禁讀及原順位／勝組，將實際版本、原／後結果及未做案例記至 `specs/011-time-display/validation.md`，不新增學生時間欄位。
- [ ] T033 [US4] 在 `specs/011-time-display/validation.md` 整理FR009／010／011／014及SC004保護checkpoint，核對data-model的「不新增表、欄位或遷移；不更動既有 writer／order by」；US4未通過不可宣稱可交付，不用重建Google授權解決。

## Phase 6: User Story 3 — 回填相關時間與活動保持一致 (Priority: P2)

**Goal**：notes確認、預覽、更新、回讀使用同一語意及政策；無結算時間不補造。

**Independent Test**：隔離fixture各事件不同時刻，核對HTML、原JSON保持、未驗證與缺時間提示；教師可只讀既有報告驗證。

- [X] T034 [P] [US3] 在 `tests/integration/test_time_display_routes.py` 先補notes確認、預覽清單／內容、更新及逐格回讀HTML回歸，含verified缺時間、非verified、壞值與notes naive，不能把預覽叫來源修改或結算時間，不需真Google。
- [X] T035 [P] [US3] 在 `tests/contract/test_time_display_contract.py` 先補notes JSON preview／report、idempotency payload、snapshot及結果版本精確保持回歸，ReadbackTimeView只供HTML；無settled_at不建立假事件或改結算。
- [X] T036 [US3] 在 `src/guided_notes/time_views.py` 組合notes真實事件的offset_required view，依「verification_status 保留原逐格狀態」「time: DisplayTime | null」及text實作ReadbackTimeView；非verified為time=null／尚未驗證，verified缺時為missing；無settled_at不建立EventTimeInput，不查Google或寫DB。
- [X] T037 [US3] T002共用約定完成後，在 `src/guided_notes/notes/routes.py` 保留notes_time名稱作安全presenter橋接，裸filter預設offset_required，為原驗權HTML組合事件view；不改export_preview_data／writeback.get_report的JSON，不把view放進指紋、覆寫或恢復判斷。
- [X] T038 [US3] T037完成且與012約定區塊後，更新 `src/guided_notes/notes/templates/notes/import.html`、`src/guided_notes/notes/templates/notes/export_form.html`、`src/guided_notes/notes/templates/notes/export_preview.html`、`src/guided_notes/notes/templates/notes/report.html` 的事件、至分鐘與區塊時區；Jinja escaping顯示，不重複加8小時，不覆蓋012名稱／入口工作。
- [X] T039 [US3] 執行T034／T035及 `tests/integration/test_export_routes.py`、`tests/integration/test_writeback_restart.py`、`tests/integration/test_workspace_history.py` 相關回歸，將命令／結果記至 `specs/011-time-display/validation.md`，驗刷新不重寫講義、不改勝組、部分／未知恢復與PR14重連仍正常。
- [ ] T040 [US3] 依 `specs/011-time-display/quickstart.md` M05由教師與兩組學生核對原活動／結果範圍，教師查看確認、預覽、報告及回讀時間，記至 `specs/011-time-display/validation.md`；既有報告不需再寫Sheets，需要新回填時由人用副本走原確認，未做不勾。
- [X] T041 [US3] 在 `specs/011-time-display/contracts/teacher-time-metadata.md` 與 `specs/011-time-display/validation.md` 整理交#19／012的最終簽名、活動／notes view用法、實際共同核對來源與待確認，不冒稱另一對話同意、不修改012文件或另建格式器。

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T042 將已實作範圍、台北政策、可重現操作及證據界線同步至 `README.md`、`docs/shared-requirements.md`、`specs/011-time-display/source-inventory.md`、`specs/011-time-display/quickstart.md`，只更新本功能段落並保留他人歷史；OpenSpec時間政策依使用者回報已確認；具名紀錄待補，其他未確認事項保持。
- [X] T043 在011獨立checkout執行當時全套pytest、Node與git diff --check，命令、完整SHA／dirty狀態、實際次數、失敗與重驗寫至 `specs/011-time-display/validation.md`；不沿用PR14數字、不把平台skip算通過、不刪測試或放寬驗證。
- [X] T044 [P] 對照成品與 `diagrams/011-time-display-component.puml`、`diagrams/011-time-display-class.puml`、`diagrams/011-time-display-sequence.puml`，將mapping與差異寫至 `specs/011-time-display/diagram-review.md`；必要時修圖、CLI重渲染同目錄PNG及檢查，圖意改變保留同學複核，不擴張原審圖範圍。
- [ ] T045 在 `specs/011-time-display/validation.md` 彙總M01～M06、V01～V07及SC001～005，核對操作者／日期／版本、Windows與真POSIX／瀏覽器、時計同步及分鐘截取核對前提；缺環境、人工未做、失敗或未確認保持待辦，原問題未重現如實記錄。
- [X] T046 在 `specs/011-time-display/analysis.md` 做實作後spec／plan／tasks／contracts／三圖與憲章分析，檢查全部FR／SC、#19接線與#16／#17界線，修正本輪缺口並同步文件，不在未核對時標完成。
- [ ] T047 在 `specs/011-time-display/analysis.md` 記錄converge，剩餘本功能缺口以連續新ID追加 `specs/011-time-display/tasks.md`，不抹原紀錄；有缺口時保持未完成直到必要修正重驗，不混入新功能。
- [X] T048 依 `specs/011-time-display/validation.md`、`specs/011-time-display/analysis.md`、`specs/011-time-display/diagram-review.md` 準備分段commit／PR與同學互審材料，只列實際完成／測試，核對011範圍、無012／私有資料／ignored工具；準備不等於已推送或合併。
- [X] T049 對照 `specs/011-time-display/validation.md` 必要驗收、待辦及同學PR審查，記Issue #20是否可結案；必要項未完成不可宣稱完整或提前關Issue，本任務不代替外部審查或另行授權的GitHub操作。

## Dependencies & Execution Order

### Phase dependencies

```text
Setup T001～T004
  → Foundation T005～T009
  → US1 T010～T019
  → US2 T020～T027
  → US4 T028～T033
  → US3 T034～T041
  → T042 → {T043, T044} → T045 → T046 → T047 → T048 → T049
```

**共用檔案gate**：T015／T016／T037／T038／T041需要T002實際約定，不能只因已記錄「待確認」就開始覆蓋同檔。未確認可完成純核心與隔離測試，接線及依賴該接線的驗收保持未完成。

### Within-story dependencies

- Foundation：T005∥T006 → T007 → T008 → T009。
- US1：T010∥T011∥T012 → T013 → T014 → T015 → T016 → T017 → T018 → T019。紅測試可先寫，不需已存在產品metadata。
- US2：T020∥T021 → T022 → T023 → T024；其後T025∥T026，T027收斂本機與可用環境結果。缺環境時不勾T025／T026／SC002，其他獨立案例仍可記錄。
- US4：T028∥T029 → T030 → T031 → T032 → T033。
- US3：T034∥T035 → T036 → T037 → T038 → T039 → T040 → T041。

US2和US1共用presenter、adapter與教師測試，按順序整合。US4的P1保護在P2 notes接線前驗證。各故事都有獨立驗收場景；共用程式的實際整合仍依上述順序，不同人不能同時改同檔。

### External dependencies

- #16／#17不等待本功能，本輪不改其組別、資格、presence或期限。測試fixture若需接已合併的新契約，以實際版本記錄。
- #19／012先約定共用介面與修改區塊，可先合011核心再接012；不重寫另一邊功能。
- 真跨環境及人工案例需要對應環境／操作者。可先完成可自動驗證部分，整體驗收仍保留未完成項。

## Parallel Examples

| 範圍 | 可並行工作 | 前置／限制 |
| --- | --- | --- |
| Foundation | T005 contract、T006 views單元測試 | Setup記錄完成；分開檔案 |
| US1 | T010核心、T011 HTTP、T012 Node測試 | Foundation完成；各用獨立受控資料 |
| US2 | T020 parser與T021 adapter測試；T025 POSIX與T026 browser | 前者在US1後；後者在T022～T024後，skip不算真環境通過 |
| US4 | T028資料保留與T029權限／DTO | 前面功能可用；檔案不同 |
| US3 | T034 notes HTTP與T035 notes JSON契約 | 前面階段完成，不跳過shared-file約定 |
| Final | T043回歸與T044圖對碼 | 所有實作與T042完成，validation與diagram-review分開 |

以上是排程機會，本輪沒有並行實作或啟動新代理。

## Requirement Traceability

| 需求／成果 | 任務 |
| --- | --- |
| FR001／002 固定台北、至分鐘 | T007、T010、T013、T015～T017、T025～T027、T037～T040 |
| FR003 活動事件及直接結束 | T006、T011、T014～T018、T021、T023、T031 |
| FR004 notes用途 | T034、T036～T040 |
| FR005／006／008 同瞬間、來源、跨日精度 | T008～T010、T013、T020～T027 |
| FR007 缺值／壞值／狀態 | T007、T014、T020～T024、T034、T036～T038 |
| FR009／010／014 保留、排序、重試 | T015～T017、T028～T033、T035、T039、T043 |
| FR011 角色範圍 | T011、T015、T029～T032、T034～T040 |
| FR012 證據分類 | T003、T009、T017～T019、T027、T040、T045 |
| FR013 不補造結算時間 | T009、T028、T035～T036、T041 |
| SC001～003 | T010～T027、T034～T040、T045 |
| SC004 | T028～T033、T035、T039、T043、T045 |
| SC005 | T018、T027、T032、T040、T045 |
| 三圖／憲章／交付 | T002～T004、T042～T049 |

## Implementation Strategy

1. **MVP**：Setup／Foundation與US1先完成，提供可獨立展示的已知活動時間、標籤及直接結束。這是第一段，完整交付仍須US2／US4的舊資料、異常、跨時區及保留保護。
2. **P1保護**：US2完成舊值與異常，再US4驗證資料、授權、順位及結果保留，不以畫面可用就宣告全功能完成。
3. **P2接線**：US3用同一presenter接notes並交#19，不另建時區或改回填JSON。
4. **分段歷程**：依「核心與教師歷史」「異常與保留驗證」「notes與接線」「最終驗收文件」整理可測試commit；實際Git操作依後續執行範圍，本輪沒有commit／push。
5. **驗收**：Windows本機、真跨環境及真人結果分開。未做、失敗、缺環境或等待協作保持未完成，文件產生及平台skip不抵作完成。

## Generation Check

共49項：Setup 4、Foundation 5、US1 10、US2 8、US4 6、US3 8、Final 8。格式核對包括ID連續、未勾選、故事標籤、檔案路徑及相依順序；不代表speckit-analyze或產品測試。

DisplayTime.text的欄位限制沿用data-model原文「known 為台北 `YYYY-MM-DD HH:mm`；其他為契約指定中文提示」；NormalizedObservation的event_kind「維持原用途」，由T007與T010／T020回歸共同約束，不在實作時另定格式或改事件種類。T005只驗基礎模型，避免Foundation反過來依賴US1尚未接線的API。

setup-tasks解析正確011絕對目錄、有效tasks-template及research／data-model／contracts／quickstart。extensions.yml前後均不存在時無hook需派送。下一步是明確鎖定011的speckit-analyze；本輪不自動分析或實作。

## 2026-11-27 實作狀態（早期「只產生任務」為歷史）

實作分支為codex/011-time-display-implementation，獨立worktree及80510a6基底見validation.md。產品自動回歸通過，M01～M06、T025 POSIX與相關整體checkpoint未完成。T002已依本對話使用者確認；未將此擴張為012作者具名審查。T049僅完成可否結案評估，結論為不可關閉，不是已關Issue。

## Phase 8: Convergence

以下為既有驗證缺口的收斂追蹤，不新增產品範圍；原T025及人工任務仍未完成，不以重複列出當完成。

- [ ] T050 在可用POSIX Python3.13隔離環境執行 `tests/integration/test_time_display_process_tz.py` 的UTC／Asia/Taipei／America/New_York子程序矩陣，於 `specs/011-time-display/validation.md` 記錄環境、完整SHA、真實TZ回讀與結果，完成後同步T025與SC-002；不能把Windows skip或Chrome證據當伺服器驗證 per SC-002 / T025 (partial)。
- [ ] T051 依 `specs/011-time-display/quickstart.md` 由教師與至少兩組學生完成M01～M06，記錄日期、操作者、版本、頁面、時計前提與預期／實際，更新 `specs/011-time-display/validation.md` 及相關原任務；自然偏差找不到仍誠實未重現，其他人工案例須實際完成才可評估交付 per SC-005 / T018 / T032 / T040 / T045 (partial)。
