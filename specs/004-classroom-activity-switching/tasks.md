# 實作任務：004 課堂加入與同堂活動切換

**設計依據** [規格](spec.md) · [計畫](plan.md) · [資料模型](data-model.md) · [介面契約](contracts/classroom-interfaces.md) · [驗證指南](quickstart.md)

**實作範圍** 先以替代 001／003 驗收 004，再用真實介面整合。使用獨立的空白開發資料庫，既有 002 測試資料不遷移。

## Phase 1 — 專案設定

- [X] T001 在 `src/guided_notes/config.py`、`src/guided_notes/__init__.py` 與 `specs/004-classroom-activity-switching/quickstart.md` 以 `GUIDED_NOTES_CLASSROOM_MODE=1` 選用 004 路由與獨立的 `instance/classroom-004.sqlite3`，未啟用時沿用 002 路由及初始化方式。（FR-007）

## Phase 2 — 共用基礎

- [X] T002 [P] 在 `tests/conftest.py` 配置 004 專用的暫存 SQLite、兩位教師、分課程的兩份可重用講義及兩個版本，提供可控制的受理、結算與快照替代服務。
- [X] T003 [P] 在 `src/guided_notes/activities/schema.sql` 與 `src/guided_notes/db.py` 建立 004 的課程、課堂、活動及組別關聯，以外鍵限制活動與組別歸屬。004 初始化可重跑，若資料庫含舊 002 結構則明確報錯且不改動原檔。用 `tests/integration/test_classroom_bootstrap.py` 驗證空白 004 可初始化兩次、誤用舊庫遭拒及 002 仍可建立活動和加入。「目前活動必須屬同一課堂，初始為空。發布階段或切換時遞增版本。已結束不可重開。」活動沿用「開啟只允許本堂沒有其他搶答中的活動。以同一交易檢查，並以資料庫唯一性保護每課堂最多一筆 `LIVE`。」（FR-002、FR-004、FR-007）
- [X] T004 在 `src/guided_notes/activities/classroom_access.py` 建立共用授權查詢，由課程取得課堂及活動的教師歸屬，供教師及 001 驗證。沿用共用登入及 CSRF，對無權資源回應 403。「教師管理自己的課程。名稱供顯示。」（FR-001、FR-006；依 T003）

## Phase 3 — US1 教師重用課程講義並管理課堂（P1）

**獨立驗收** 以教師與替代 001 建立一門課程內的兩個班次，確認兩份講義可選、指定版本可重用、加入碼不同且其他教師遭拒。

- [X] T005 [P] [US1] 在 `tests/contract/test_classroom_management.py` 定義課程與課堂新增、列表、歷史及擁有者拒絕案例，核對唯一加入碼、課堂初始狀態及同名活動的不同識別。（FR-001、FR-002、SC-001）
- [X] T006 [P] [US1] 在 `tests/integration/test_classroom_catalog.py` 定義講義重用、固定版本與順序，以及 001 未就緒案例。驗證同一教師用 B 課程的講義及版本在 A 課程建活動會遭拒且不留活動紀錄，改用 A 課程的適用版本才能建立。（FR-001、FR-004、D15）
- [X] T007 [US1] 在 `src/guided_notes/activities/classroom_catalog.py` 接上課程講義與精確版本查詢的替代提供者。先確認教師管理該課程，再驗證 `course_id`、`import_id`、`import_version` 關聯，通過才固定版本。「002 只使用屬同課程的指定版本。001 管理 Sheets 位置與存取授權。」缺少提供者回 `503 CATALOG_UNAVAILABLE`。正式函式簽名依 T023 複核。（FR-001、FR-004、D15；依 T006）
- [X] T008 [US1] 在 `src/guided_notes/activities/classroom_routes.py` 與 `src/guided_notes/__init__.py` 接上課程、課堂及歷史路由，發出唯一加入碼供教師操作，並建立固定講義及有序題目的活動。預設活動名沿用講義名稱，允許自訂而保留獨立活動識別。（FR-001、FR-002、FR-004；依 T004、T005、T007）
- [X] T009 [US1] 在 `src/guided_notes/templates/activities/classroom.html` 加入選課程、講義版本、建立課堂、加入碼及歷史入口，並提供「在目前課程匯入講義」的 001 接點。實際預覽確認依 T023 驗收；替代模式執行 T005、T006。（FR-001、FR-002、SC-001；依 T008）

## Phase 4 — US2 課堂加入一次並跟隨活動（P1）

**獨立驗收** 預建一個含兩場活動的課堂，以兩組學生各加入一次。驗證切換、刷新與重連保留組別，兩個開啟請求最多一個成功，舊活動提交遭拒。

- [X] T010 [P] [US2] 在 `tests/contract/test_classroom_memberships.py` 定義課堂碼加入、跨堂同名組隔離、拒絕空組名及課堂狀態契約，涵蓋當前活動空指標與後續切換。驗證課堂狀態只對管理教師或同堂學生提供。（FR-002、FR-003、SC-002）
- [X] T011 [P] [US2] 在 `tests/integration/test_classroom_switch.py` 用兩條 SQLite 連線驗證同堂同時開啟兩個活動，最多一個成功；切換後舊活動提交遭拒且未寫入新活動。（FR-004、SC-003）
- [X] T012 [US2] 在 `src/guided_notes/activities/classroom_membership.py` 與 `src/guided_notes/activities/classroom_routes.py` 實作課堂碼及自填組名加入。遵循「空白拒絕。同堂整理後的相同名稱唯一，不同課堂分離。」以及「只有進行中的課堂可建立加入。」共用原瀏覽器證明及短期授權，不因切換活動而重建組別。（FR-002、FR-003；依 T010）
- [X] T013 [US2] 在 `src/guided_notes/activities/teacher.py` 與 `src/guided_notes/activities/classroom_routes.py` 使用既有寫入交易開啟或結束指定活動、更新課堂目前活動及版本。以擁有者、課堂開放、目標階段和單一 LIVE 條件保護轉換。（FR-003、FR-004；依 T008、T011）
- [X] T014 [US2] 在 `src/guided_notes/activities/submission_context.py` 與 `src/guided_notes/quiz/submission_gateway.py` 於收件交易驗證原活動仍是當前活動且搶答中、課堂開放、組別屬於該堂，保留原答案文字並延用既有題組驗證。（FR-004、FR-005；依 T012、T013）
- [X] T015 [US2] 在 `src/guided_notes/activities/classroom_routes.py` 以同一讀取快照提供課堂及目前活動，回傳課堂狀態、版本、可空活動識別與階段。讀取逐次驗證活動範圍，不在同步資料預載歷史結果。（FR-003、FR-006；依 T012、T013）
- [X] T016 [US2] 在 `src/guided_notes/static/classroom.js` 與 `src/guided_notes/templates/activities/classroom.html` 接上加入一次、等候、進行、已結束與課堂已結束狀態。以課堂識別及版本拒絕舊回應，活動切換時清除舊題草稿，提交仍綁原活動識別。以 `tests/activity-sync.test.cjs` 驗證反序回應，並執行 T010、T011。（FR-003、FR-004、SC-002；依 T014、T015）

## Phase 5 — US3 關課並保留歷史與回填（P1）

**獨立驗收** 預建同一課堂的兩場已結算活動及另一場搶答中活動。確認關課一併結束搶答中活動，拒絕後續加入及提交。原瀏覽器可看同堂已結算活動的 D06 結果，並可用指定活動取得回填快照。

- [X] T017 [P] [US3] 在 `tests/integration/test_classroom_close.py` 定義取消／確認、關課原子結束目前活動、關課與加入及提交競爭、拒絕重開，以及歷史資料保留的案例。（FR-005、FR-007、SC-003）
- [X] T018 [P] [US3] 在 `tests/contract/test_classroom_results.py` 定義原瀏覽器恢復、跨瀏覽器拒絕、清單只列已結算活動、指定活動快照及錯誤區分。以學生直接請求跨堂、同堂未結算及同堂已結算的活動，驗證 403、僅結算狀態、僅 D06 欄位。（FR-006、SC-004、D16）
- [X] T019 [US3] 在 `src/guided_notes/activities/classroom_routes.py` 與 `src/guided_notes/templates/activities/classroom.html` 加入明確關課確認。於同一交易關閉課堂、更新版本並結束仍 LIVE 的活動。拒絕新加入、提交、開啟和重開，提交成功後才回報關課，保留活動資料且不觸發 Sheets 寫入。（FR-005、FR-007；依 T017）
- [X] T020 [US3] 在 `src/guided_notes/activities/classroom_membership.py` 與 `src/guided_notes/activities/classroom_routes.py` 實作課堂結果授權。遵守「結束後原瀏覽器可恢復唯讀結果授權；不得切換組別。」驗證課堂加入證明取得原組別及唯讀授權，拒絕他堂或新瀏覽器。（FR-006、D16；依 T018、T019）
- [X] T021 [US3] 在 `src/guided_notes/quiz/results_gateway.py` 與 `src/guided_notes/quiz/activity_routes.py` 限制學生歷史清單只含同堂已結算活動。直接查活動時，由授權取得課堂與組別，跨堂回 403，同堂結算中只回狀態，已結算依 D06 篩選。指定活動快照核對教師、`CLOSED` 與結算狀態，維持兩種快照錯誤碼。遵守「同一份講義建立的活動各自保存。只有已結束且已結算的活動可提供回填快照。」（FR-006、SC-004；依 T018、T020）
- [X] T022 [US3] 在 `src/guided_notes/templates/activities/classroom.html` 與 `src/guided_notes/static/classroom.js` 加入關課後原瀏覽器結果恢復及同堂歷史選擇。測試選取結果不會更改課堂當前指標或重新開放提交。執行 T017、T018。（FR-005、FR-006、D16；依 T021）

## Phase 6 — 整合與交付驗證

- [ ] T023 [P] 在 `specs/004-classroom-activity-switching/contracts/classroom-interfaces.md` 與 `specs/001-guided-notes/contracts/interfaces.md` 記錄 001／002 介面複核，對齊課程授權、講義清單、精確版本查詢及錯誤。001 到位後，在 `tests/integration/test_live_classroom_catalog.py` 驗收課程內匯入預覽與確認綁定原課程，講義只出現在原課程，竄改課程或使用他人的預覽遭拒且不留紀錄。另驗證兩份真實講義及活動版本固定。
- [ ] T024 [P] 在 `tests/integration/test_live_classroom_quiz.py` 於 003 就緒後驗證同堂切換、舊活動拒收、已結算結果隔離與指定活動快照，再與 001 核對回填。未就緒時保留實際串接待辦。
- [ ] T025 在 `specs/004-classroom-activity-switching/quickstart.md` 記錄空白資料庫初始化重跑、教師和兩組操作、自動驗證、日期、執行者、預期與結果。未執行及受阻項目如實記錄；保留舊 002 測試檔與 Sheets。
- [ ] T026 在 `specs/004-classroom-activity-switching/plan.md` 記錄程式與三張圖對照及差異修正。若需改圖，更新 `diagrams/004-component.puml`、`diagrams/004-class.puml` 或 `diagrams/004-sequence.puml` 並重新渲染、複核。合併前依憲章保留 Analyze、Converge 與驗收紀錄。

## 相依順序與並行工作

`T001 → T002/T003 → T004 → US1 → US2 → US3 → 獨立驗收與串接`

- US1 的 T005、T006 可同時編寫，服務實作完成後才接教師頁。
- US2 的 T010、T011 可同時編寫。課堂加入與活動轉換完成後，再驗證交易內收件與同步畫面。
- US3 的 T017、T018 可同時編寫。關課完成後，再接唯讀恢復與歷史結果。
- T023、T024 分別在 001 和 003 契約就緒後進行。先使用替代服務完成自動驗證和三端操作，T025、T026 可先記錄獨立驗收，再補實際串接結果。

## 實作策略

1. 首個 MVP 完成 US1。教師可在自己的課程選擇兩份替代講義、建立不同課堂並固定活動版本。
2. US2 加入課堂身份與活動切換。US3 加入關課、歷史結果與快照界線。
3. 以真實 001／003 完成跨功能驗收，保留先前 002 的獨立任務與證據。

## Phase 7: Convergence

2026-11-25 合併前以 spec／plan／tasks 與現有程式收斂，outcome=tasks_appended。以下不表示原 T023–T026 或人工驗收完成。

- [X] T027 修正 classroom.js 在狀態或歷史清單讀取失敗後不重試、按鈕持續停用的情形；清單成功前保持刷新需求並防止舊清單回應覆蓋新選擇，補 JavaScript 重現測試。（FR-003、SC-002，partial）
- [X] T028 整合共用 db.py／conftest，保留 001 顯式 COMMIT／ROLLBACK 與 004 隔離建表；課堂讀取交易以 SQL ROLLBACK 結束，移除重複 activity reference 定義，驗證同 context 後續可寫及 init-db 冪等。（plan: shared SQLite、Constitution VI，contradicts）
- [X] T029 用真實 course provider 及 001 course-scoped catalog 實作整合測試，驗證匯入、跨課程拒絕、固定版本、一次加入後切換與既有回填 adapter；Sheets 與正式 003 仍明確使用替代來源。（T023、FR-001/004/006，partial）
- [X] T030 修正合流後 D12 重複與任務路徑差異，將顯示名稱獨立編為 D17，更新圖文、啟動說明與分析／收斂證據；同步執行 001／004 回歸。（Constitution II/VI，contradicts）
- [ ] T031 正式 003 完成後，兩位組員依 T024–T026 完成真實 Sheets、教師及兩組學生、關課後歷史與同勝組回填的人工驗收，保留日期／執行者／結果及圖意審查，不用 substitute 代勾。（Constitution V、SC-002/004，partial）

合流修補 T027–T030 已實作及自動驗證；T023–T026 的真實副本／003／人工及 T031 仍未完成。圖意對照、分析／收斂與測試證據見 docs/pr6-integration-validation.md，不宣稱完整專題驗收。
