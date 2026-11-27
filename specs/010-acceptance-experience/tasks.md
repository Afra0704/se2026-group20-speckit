# Issue #10 實作任務

依據 [規格](spec.md)、[計畫](plan.md)、[契約](contracts/acceptance-interfaces.md)及[驗收指南](quickstart.md)。A、C 可各自驗收。B 的規則確認與圖表複核已記錄於 T013。

## 第一階段｜環境與基底

- [x] T001 核對分支以含 PR #11 與 ea5efbb 的 master 為基底；確認 009 已合併及 feature 指向，記於 `specs/010-acceptance-experience/validation.md`。

## 第二階段｜共同驗證

- [x] T002 以測試資料庫執行 `specs/010-acceptance-experience/quickstart.md` 內的 Python 與 Node 回歸命令，建立基線並記錄版本、命令及結果於 `specs/010-acceptance-experience/validation.md`。
- [x] T003 在實作前執行 SpecKit Analyze，核對 FR、契約、圖表、任務及驗收對應，記錄於 `specs/010-acceptance-experience/analysis.md`。

## 第三階段｜US1 匯入欄位錯誤（A，P1）

獨立驗收：空白與不支援連結可在欄位旁修正，權限與暫時錯誤可辨識，有效連結仍可匯入。

- [x] T004 [P] [US1] 在 `tests/import-url-validation.test.cjs` 涵蓋原生驗證、後端 INVALID_SHEETS_URL、原值保留、修正重送和清除狀態。FR-A01／A02。
- [x] T005 [P] [US1] 在 `tests/contract/test_import_flow_routes.py` 依介面契約核對無效來源、授權／權限、來源不存在與暫時讀取失敗，包含匯入流程狀態回傳的錯誤。FR-A02。
- [x] T006 [US1] 更新 `src/guided_notes/templates/workspace/lectures.html`、`src/guided_notes/static/import-flow.js`、`src/guided_notes/static/workspace.js` 與 `src/guided_notes/static/workspace.css`，依介面契約將格式錯誤接至欄位提示、其他類別接至操作提示，保留原連結、ARIA 關聯及重送恢復。FR-A01／A02。
- [x] T007 [US1] 執行欄位與匯入回歸測試並用 Sheets 副本走完合法匯入，記錄於 `specs/010-acceptance-experience/validation.md`。SC-001。

## 第四階段｜US2 活動結束結果（C，P1）

前置條件：完成 T002／T003，且新版 C 圖已由組員複核。[圖表審查紀錄](diagram-review.md)已記錄複核完成。

獨立驗收：一位教師及兩組學生可從準備中與搶答中結束活動，看到正確角色結果、歷史紀錄及下一活動。

- [x] T008 [P] [US2] 擴充 `tests/student-room-009.test.cjs`、`tests/student-room-quiz-009.test.cjs`、`tests/quiz-results.test.cjs`，涵蓋自動查詢、結算中轉正式、無資料、重試、純文字／舊格式、手動歷史選取不被本場自動查詢覆蓋、下一活動恢復主畫面、晚到成功／錯誤及卡住結果請求時仍能同步整堂關閉。FR-C01–C03。
- [x] T009 [P] [US2] 在 `tests/contract/test_classroom_results.py` 與 `tests/integration/test_classroom_history_009.py` 核對 D06／003-D22／009-D22：OPEN 同堂晚加入、CLOSED 拒絕學生及原瀏覽器恢復、教師歷史／回填、跨組授權。FR-C02／C03。
- [x] T010 [US2] 在 `src/guided_notes/templates/activities/student_room.html`、`src/guided_notes/templates/workspace/classroom.html`、`src/guided_notes/static/student-classroom.css` 與 `src/guided_notes/static/workspace.css` 提供獨立結果區與狀態。FR-C01／C02。
- [x] T011 [US2] 在學生 `src/guided_notes/static/student-room.js` 接入 OPEN 階段切換及正式投影，讓手動歷史優先並在下一活動撤銷舊目標，在教師 `src/guided_notes/static/classroom.js` 接入結果區。保留關課終止、獨立輪詢、教師作答進度、歷史入口、送答重試及過期回應檢查。FR-C01–C03。
- [x] T012 [US2] 執行結果、課堂、送答及回填相關回歸。以兩組學生實測階段切換與延遲，記錄於 `specs/010-acceptance-experience/validation.md`。SC-003／004。

## 第五階段｜US3 課堂在線統計（B，P2）

獨立驗收：兩組三個瀏覽器環境先顯示 2＋1，再實測多頁、斷線、重連與課堂隔離。

- [x] T013 [US3] 在 `docs/shared-requirements.md` 記錄雙組確認者、日期、理由，以及身分、多頁、心跳、背景頁、逾時和驗收時限定案；同步 `specs/010-acceptance-experience/spec.md`、`specs/010-acceptance-experience/contracts/acceptance-interfaces.md` 及 `diagrams/010-presence-sequence.puml`，若圖意改變則重渲染並複核。
- [x] T014 [P] [US3] 在 `tests/contract/test_classroom_presence.py` 涵蓋合法更新、去重、逾時、零人、跨課堂／教師隔離、關課及保留正式結果。FR-B01–B03。
- [x] T015 [US3] 在 `src/guided_notes/activities/classroom_presence_schema.sql`、`src/guided_notes/activities/classroom_presence.py` 與 `src/guided_notes/db.py` 實作定案後的身分與頁面狀態，驗證會保留既有資料的可重跑升級。FR-B02／B03。
- [x] T016 [US3] 在 `src/guided_notes/activities/classroom_routes.py` 與 `src/guided_notes/workspace/routes.py` 接入授權更新及老師課堂統計。FR-B01／B02。
- [x] T017 [US3] 在 `src/guided_notes/static/classroom.js`、`src/guided_notes/templates/workspace/classroom.html` 顯示在線人數、過期及關課狀態，在學生 `src/guided_notes/static/student-room.js` 接入定案後的頁面更新。FR-B02。
- [x] T018 [US3] 實測加入、重複加入、重整、不同瀏覽器、多頁只關一頁、最後一頁失聯逾時、背景頁、斷線重連、同堂切換、不同課堂及教師查詢失敗後恢復。依定案規則核對計數，記錄實際延遲及在線變動前後的正式結果於 `specs/010-acceptance-experience/validation.md`。SC-002／004。

## 第六階段｜交付檢核

- [x] T019 依實作範圍執行 Converge、比對 PlantUML 與程式、補足回歸及人工驗收紀錄，並核對憲章 III 的兩份講義端到端證據，缺證據時補驗，更新 `specs/010-acceptance-experience/diagram-review.md` 與 `specs/010-acceptance-experience/validation.md`。SC-004。

## 依賴與增量

T001 → T002 → T003 → A。C 另須完成新版圖表複核，才可開始 T008–T012。先交付 A，C 可獨立進行；A 的匯入測試與 C 的結果測試可並行。B 由 T013 解鎖，T014 與 T015 可分開準備。C 與 B 都會修改課堂前端，整合時依序處理並重跑課堂回歸。每次交付按實際範圍執行 T019。
