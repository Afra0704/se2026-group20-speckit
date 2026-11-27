# 012 學生分頁課堂資格與重新加入

Issue #17。依據 [規格](spec.md)、[計畫](plan.md)、[資料模型](data-model.md)、[介面契約](contracts/tab-membership.md)及[驗收指南](quickstart.md)。

## 第一階段｜準備

- [x] T001 核對 012 專用分支、最新 master、PR #22 合併狀態與新版圖表審查。以獨立測試庫跑 Node 與課堂相關 Python 基線，記入 `specs/012-tab-classroom-membership/validation.md`。

## 第二階段｜共同基礎

- [x] T002 在 `specs/012-tab-classroom-membership/contracts/tab-membership.md` 定義加入、恢復、撤回的請求欄位、回應與錯誤碼，核對 #16 欄位錯誤與 #18 未決送答的交接。接入 #16 程式前核對 PR #22 的實際合併版本。
- [x] T003 在 `specs/012-tab-classroom-membership/research.md` 說明重整與複製的分流證據及無法辨識的處理，涵蓋原頁立即關閉、瀏覽器返回快取與恢復回應遺失，並定義 rollout 期間舊 grant 的處理。
- [x] T004 執行 SpecKit Analyze，核對 FR、SC、角色授權、圖表與任務，結果記入 `specs/012-tab-classroom-membership/analysis.md`。
- [x] T005 在 `src/guided_notes/activities/classroom_tab_schema.sql` 建立附加表，實現「瀏覽器 × 固定課堂 ID 唯一；包含目前組別 ID 與世代」，保存分頁資格、到期及撤回。從 `src/guided_notes/db.py` 以可重跑交易初始化，保留既有資料與 009 遷移；在 `tests/integration/test_classroom_code_schema.py` 驗證升級與重跑。

## 第三階段｜US1 跨堂並存、同堂單組（P1）

獨立驗收：同一瀏覽器兩頁各加入不同課堂，兩頁的狀態、歷史與送答各用自己的資格；同堂異組衝突保留原頁。對應 FR-012-01、03、04 與 SC-012-01、02、03。

- [x] T006 [P] [US1] 擴充 `tests/contract/test_classroom_memberships.py`、`tests/integration/test_classroom_join_races.py`，驗證同瀏覽器跨堂、同堂同組去重、異組競態只允許一組及 4 秒失聯後換組；核對無效組號不改資格。
- [x] T007 [P] [US1] 擴充 `tests/contract/test_classroom_results.py`、`tests/integration/test_classroom_submission_races_009.py`，驗證錯堂、錯組、偽造、CSRF、關課與換組後舊世代被拒，教師的歷史及回填仍有效。
- [x] T008 [US1] 在 `src/guided_notes/activities/classroom_membership.py` 與 `src/guided_notes/activities/classroom_routes.py` 接入瀏覽器專用 HttpOnly 綁定與分頁發行。在單一寫入交易中核對同堂異組、建立首個在線保留，換組加一世代。組別由伺服器解析。
- [x] T009 [US1] 將同一授權解析接入 `src/guided_notes/activities/classroom_routes.py`、`src/guided_notes/activities/submission_context.py`、`src/guided_notes/quiz/results_gateway.py` 與 `src/guided_notes/activities/classroom_presence.py`。狀態、歷史、結果、送答含重送及在線均逐次核對角色、瀏覽器、堂、組、世代與期限。
- [x] T010 [US1] 在 `src/guided_notes/static/student-entry.js` 與 `src/guided_notes/static/student-room.js` 接入分頁資格與加入衝突提示，保留 #16 欄位驗證。確認新協定的學生請求缺少分頁資格時不沿用共用 grant。

## 第四階段｜US2 重整、重連與複製（P1）

獨立驗收：複製有效頁直接進入原堂原組，兩頁各有獨立資格且合計一人；原頁可在有效期限內恢復。對應 FR-012-01、03、05 與 SC-012-01、02、03。

- [x] T011 [P] [US2] 擴充 `tests/contract/test_classroom_recovery_009.py`，驗證瀏覽器與索引須同時匹配、到期及撤回、換組世代失效、關課僅回終態、重試與並行恢復不撤回另一頁。
- [x] T012 [P] [US2] 擴充 `tests/student-room-009.test.cjs` 與 `tests/student-presence-lifecycle.test.cjs`，涵蓋複製後原頁立即關閉、同頁重整、回覆遺失、背景返回與關課清除。
- [x] T013 [US2] 在 `src/guided_notes/activities/classroom_membership.py` 與 `src/guided_notes/activities/classroom_routes.py` 實作恢復。以瀏覽器 cookie、CSRF、原堂原組和世代驗證索引後，發出新索引及短效文件資格；只允許成功的頁面取得受保護資料。
- [x] T014 [US2] 在 `src/guided_notes/static/student-room.js` 接入恢復與複製。索引只在 sessionStorage，文件資格只在記憶體；過期訊息區分可恢復、須重新加入及整堂關閉。確保在線每秒心跳、4 秒逾時及 5 秒驗收目標沿用。

## 第五階段｜US3 本頁重新加入與送答保留（P1）

獨立驗收：取消保留本頁操作；確認只撤回本頁、回空白加入頁；正式答案、順位及其他頁維持。對應 FR-012-02、03、04 與 SC-012-01、02、03。

- [x] T015 [P] [US3] 擴充 `tests/student-room-quiz-009.test.cjs`、`tests/quiz-submission.test.cjs`，覆蓋重整保留、複製不承接未決操作、取消與確認、未知結果警告、原 key／payload 及晚到成功或拒絕回應。
- [x] T016 [US3] 在 `src/guided_notes/activities/classroom_routes.py`、`src/guided_notes/activities/classroom_membership.py` 及 `src/guided_notes/activities/classroom_presence.py` 接入明確撤回，只撤銷本頁並移除本頁在線。已撤回的重試維持同一結果，舊心跳不能復活該頁。
- [x] T017 [US3] 在 `src/guided_notes/templates/activities/student_room.html`、`src/guided_notes/static/student-room.js` 與 `src/guided_notes/static/quiz-submission.js` 接入重新加入入口、草稿與未決警告、撤回確認及本頁作用域清理。重整保留可確認歸本頁的原操作及 key，複製另建作用域。

## 第六階段｜整體交付

- [x] T018 依 `specs/012-tab-classroom-membership/quickstart.md` 執行 Node、Python 與至少一位教師、兩組學生的真人驗收，測量在線更新與斷線恢復。將版本、執行者、場景、預期及實際結果記入 `specs/012-tab-classroom-membership/validation.md`。
- [x] T019 執行 Converge，對照程式及 `diagrams/012-tab-classroom-membership-component.puml`、`diagrams/012-tab-classroom-membership-class.puml`、`diagrams/012-tab-classroom-membership-sequence.puml`，必要時重繪及複核，將差異、證據與組員互審狀態記入 `specs/012-tab-classroom-membership/diagram-review.md`。

## 依賴與交付順序

`T001 → T002／T003 → T004 → T005 → US1 → US2 → US3 → T018 → T019`。T006／T007、T011／T012 分別可並行準備。T015 可在契約確定後獨立準備，接線 T017 須等撤回與恢復完成。多個故事會修改相同的課堂路由與學生頁，依順序整合並逐階段跑回歸。首個開發增量為 US1；公開交付驗收涵蓋三個故事。

2026-11-28：T018自動及真人驗收、T019檢核與三圖實作對照已完成；證據及限制見validation.md與docs/pr24-issue17-integration-review.md。T019完成不代表同學已核准本輪整合／F5修正，互審狀態仍待同學審閱。
