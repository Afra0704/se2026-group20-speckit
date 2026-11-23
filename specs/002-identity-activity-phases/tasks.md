# 實作任務：002 身分與活動階段

**設計依據** [規格](spec.md) · [計畫](plan.md) · [研究](research.md) · [資料模型](data-model.md) · [介面契約](contracts/activity-interfaces.md) · [驗證指南](quickstart.md)

**範圍** 先用替代清單及作答服務驗收 002，再串接 001／003。所有勾選均須有實作及適用的驗證證據。`[P]` 表示該項的前置條件達成後，可與同批其他標記項目並行。

## Phase 1 — 專案初始化

- [ ] T001 在 `pyproject.toml` 與 `uv.lock` 建立 Python 3.11 以上的 Flask／Jinja／pytest 環境，若已有專案設定則沿用。
- [ ] T002 [P] 在 `app/__init__.py` 與 `app/config.py` 建立本機 Flask 應用入口，使用 loopback 與環境設定載入憑證，開發 HTTP 與 HTTPS 的 Cookie 設定分開。
- [ ] T003 [P] 在 `.gitignore` 與 `.env.example` 排除本機祕密設定、SQLite 資料與日誌，範例僅提供佔位值。

## Phase 2 — 共用基礎

- [ ] T004 [P] 在 `app/db.py` 建立共用 SQLite 連線與短寫入交易，啟用外鍵，支援 `BEGIN IMMEDIATE`、回滾與有限忙碌重試。提交完成後才回報成功，重試耗盡映射至 503。
- [ ] T005 [P] 在 `app/activities/security.py` 建立共用工作階段驗證、有效範圍檢查、CSRF 與代碼嘗試限制。定義「教師、學生權限分開。由原加入紀錄恢復的已結束授權只可讀取該活動的允許資料和結果。」（FR-003、FR-005、FR-006）
- [ ] T006 [P] 在 `app/http.py` 建立介面契約所列錯誤與禁止快取回應，未授權的回應不得揭露活動內容、代碼有效細節或祕密值。
- [ ] T007 [P] 在 `tests/conftest.py` 配置隔離的測試應用與資料庫，準備三題兩版清單、兩組測試身分，以及可控制的替代 003 受理與結算狀態。

## Phase 3 — US1 教師建立及控制活動（P1，首個 MVP）

**獨立驗收** 使用兩版三題清單及教師測試帳號，確認無效清單遭拒、建立時固定版本、合法開啟與結束、重開遭拒。

- [ ] T008 [P] [US1] 在 `tests/contract/test_teacher_activities.py` 定義登入、建立、開啟及結束的 HTTP 案例，驗證無管理權限遭拒且階段不變。（FR-001、FR-004、SC-003）
- [ ] T009 [P] [US1] 在 `tests/integration/test_activity_catalog.py` 驗證三題順序與識別、無效及無權清單不建活動、重新匯入後原活動維持原版本。（FR-001、FR-002、SC-001、D11）
- [ ] T010 [US1] 在 `app/activities/schema.sql` 建立教師、活動、活動題目、活動組別與授權資料。套用「登入名稱唯一。」「活動識別、活動碼各自唯一。清單參考建立後固定。階段版本隨成功轉換遞增。」「每活動題目及位置各自唯一。顯示題號不當關聯鍵。」「組別識別在活動內唯一。同一活動內相同的整理後名稱對應同一組別，空白名稱拒絕。」
- [ ] T011 [P] [US1] 在 `app/guided_notes/catalog.py` 建立 001 版本查詢介面及替代資料接點。依模型驗證「清單與版本組合唯一。已交付的版本不可變，每版題目 ID 和位置各自唯一，至少一題。來源格位與憑證留在 001。」（FR-001、FR-002）
- [ ] T012 [US1] 在 `app/activities/teacher.py` 與 `app/activities/teacher_routes.py` 實作教師登入與活動管理。建立時原子保存活動及有序題目。套用「管理操作要求帳號有效且是該活動的管理教師。」轉換只允許 `PREPARING → LIVE → CLOSED`，其他開啟或結束請求保留原階段與版本。提供教師查看活動碼的介面，並在 `app/activities/init_teacher.py` 提供以受控本機憑證初始化教師的指令，供空資料庫驗收。（FR-001 至 FR-004、D11）
- [ ] T013 [US1] 在 `app/templates/activities/teacher.html` 接上教師登入、清單選擇、建立、開啟及結束流程，顯示已確認的階段和操作錯誤，並通過 T008、T009 的驗證。

## Phase 4 — US2 學生按組加入並同步狀態（P1）

**獨立驗收** 使用已建立的活動測試資料，甲組在準備中加入、乙組在搶答中加入。檢查題目可見、三端重整與重連、結束後拒絕新加入，以及原瀏覽器恢復與跨瀏覽器拒絕。

- [ ] T014 [P] [US2] 在 `tests/contract/test_memberships.py` 定義按組加入、狀態及結果存取介面的案例，覆蓋錯誤活動碼、空白組名、同活動同組名、錯誤活動或組別範圍、結束後新加入、原瀏覽器恢復及換裝置／清除證明後遭拒。（FR-003、FR-005、D09）
- [ ] T015 [P] [US2] 在 `tests/integration/test_activity_sync.py` 以管理教師及兩組驗證共用狀態入口、六次重整、狀態版本遞增及授權過期的伺服器資料契約，並驗證無該活動管理權限的教師遭拒。（FR-005、FR-006、SC-002、A08）
- [ ] T016 [US2] 在 `app/activities/schema.sql` 與 `app/activities/membership.py` 實作原加入紀錄與授權。套用「僅在結束前成功加入時產生。結果恢復要求仍有效且綁定原活動與組別的原加入證明，恢復不建立新的加入紀錄。」加入與關閉共用寫入交易，短期授權與同瀏覽器恢復證明分開。（FR-003、FR-005）
- [ ] T017 [US2] 在 `app/activities/student_routes.py` 實作加入與結果恢復，在 `app/activities/state_routes.py` 實作管理教師和已授權學生共用的權威狀態入口，逐次檢查角色與活動範圍。學生以活動碼與自填組別加入，伺服器綁定該組別。準備中加入即顯示題目，結束後的新加入遭拒，既有學生須持原瀏覽器證明取得原活動及原組別的唯讀結果授權。（FR-003、FR-005、FR-006、D09）
- [ ] T018 [US2] 在 `app/templates/activities/student.html` 與 `app/static/activity-sync.js` 接上學生流程及教師端的共用同步腳本。約一秒輪詢、同時僅一個輪詢請求，載入與重連立即重取，在瀏覽器驗證先收到「已結束」再收到舊「搶答中」時，畫面維持「已結束」且無法提交。依階段顯示重新加入或恢復結果。執行 T014、T015 及三端操作。（FR-003、FR-005、SC-002）

## Phase 5 — US3 角色與階段限制資料（P1）

**獨立驗收** 使用由測試資料建立的教師、兩組授權與 003 替代服務。確認兩種截止競爭順序、結算中僅有狀態，以及結算後教師、勝組及非勝組各自的欄位。

- [ ] T019 [P] [US3] 在 `tests/contract/test_quiz_visibility.py` 定義直接請求及預載 HTML 案例，涵蓋教師與兩組的結束前資訊隔離、結算中無結果欄位、結算後遵循 D06，以及唯讀恢復授權不可提交。（FR-006、SC-003、SC-004、A04）
- [ ] T020 [P] [US3] 在 `tests/integration/test_activity_cutoff.py` 用兩條 SQLite 連線與受控同步點驗證受理先提交和關閉先提交，另驗證關閉與加入競爭、回滾無部分受理，以及準備中和結束後拒收。（FR-007、D02、A06）
- [ ] T021 [US3] 在 `app/activities/submission_context.py` 與 `app/quiz/submission_gateway.py` 建立 002→003 受理邊界，遵守「同一寫入交易內核對，以活動題目及活動組別關聯。無法由瀏覽器指定權威欄位。」在測試替代受理服務驗證有效角色、組別、題目與搶答中，成功持久化並提交後才視為受理。完整排名、空白及重送留給 003。（FR-007、D02）
- [ ] T022 [US3] 在 `app/quiz/results_gateway.py` 與 `app/quiz/activity_routes.py` 接上提交與結果契約。伺服器按授權視角組裝結果，教師可看進行中的作答狀況，結算中只回狀態，結算後教師取得各組結果，學生只取得勝組名稱與答案及本組答案、順位。（FR-006、FR-007、D06）
- [ ] T023 [US3] 在 `app/templates/activities/results.html`、`app/templates/activities/student.html` 與 `app/templates/activities/teacher.html` 接上作答入口及結果畫面。開始前不開放提交，已結束保留其階段並區分結算中與已結算，頁面及預載資料使用 T022 的限制。執行 T019、T020。（FR-006、FR-007、SC-004）

## Phase 6 — 串接與交付驗證

- [ ] T024 [P] 在 `tests/integration/test_live_catalog_contract.py` 使用 001 實際接口與兩份講義核對固定版本、有序題目及回填時可追溯至原版本。待 001 契約可用再執行，題組與多空依 D05／D10。（T023、A01、A02）
- [ ] T025 [P] 在 `tests/integration/test_live_quiz_contract.py` 使用 003 實際受理及結算重跑截止、資訊隔離與三端結果契約。待 003 契約可用再執行，D01／D02 未定細節維持相依。（T023、A03、A04、A06）
- [ ] T026 在 `specs/002-identity-activity-phases/quickstart.md` 記錄實測啟動與測試指令、替代服務驗收，以及教師與兩組的人工結果、同步量測、執行者和版本。實際串接受阻時如實記錄。
- [ ] T027 在 `specs/002-identity-activity-phases/plan.md` 記錄程式與三圖的責任、關係及時序對照，核對憲章與測試證據。發現差異時依已確認規格修正並重驗，更新圖表時重渲染並記錄。

## 相依順序與並行工作

- **整體順序**：T001–T003 → T004–T007 → US1 → US2 → US3 → Phase 6。US2、US3 可用測試資料各自驗收，正式串接依前一階段的活動及授權界面。
- **US1 並行例**：T008 與 T009 可同時編寫。共同測試環境就緒後，T011 的清單讀取契約可與 T010 的 SQLite 結構並行，T012 等兩者及其測試就緒。
- **US2 並行例**：US1 就緒後，T014 和 T015 可同時編寫。T016 → T017 → T018。
- **US3 並行例**：US2 就緒後，T019 和 T020 可同時編寫。T021 → T022 → T023。
- **串接**：T024 與 T025 依各自外部契約可並行。三端替代資料驗收不必等待外部模組。T026 依實際執行情況記錄，T027 核對完成證據。

## 實作策略

1. 先完成基礎與 US1，展示教師用替代清單建立活動、開啟及結束。這是首個可獨立驗收的開發增量。
2. 加入 US2 及 US3，先以替代服務跑通教師與兩組學生、截止和資料隔離。
3. 確認 001／003 介面可用後完成整合驗收。雙組尚未定案的講義與排名規則依 [共同需求](../../docs/shared-requirements.md) 追蹤。合併前依憲章保留 Analyze、Converge 與人工驗收紀錄。
