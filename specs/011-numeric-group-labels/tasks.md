# 011 數字組別與一致顯示實作任務

Issue #16。以 `e9a29c7` 為基底。依據 [規格](spec.md)、[計畫](plan.md)、[資料模型](data-model.md)、[契約](contracts/group-number.md)與[驗收指南](quickstart.md)。

## 第一階段｜準備

- [x] T001 核對工作分支、011 功能指向與 PR #14 基底，確認 011 圖表審查紀錄。設定獨立空白測試庫，執行 Python 與 Node 基線並在 `specs/011-numeric-group-labels/validation.md` 記錄版本、命令與結果。

## 第二階段｜共用契約

- [x] T002 在 `specs/011-numeric-group-labels/contracts/group-number.md` 與 `specs/012-tab-classroom-membership/spec.md` 對齊 #17 的 `group_name`、`INVALID_GROUP_NUMBER`、HTTP 400 和拒絕後保留原資格；記錄 #19 的回填顯示採原課堂映射。
- [x] T003 執行 SpecKit Analyze，核對規格、計畫、任務、契約與已審圖表的覆蓋，將結果記入 `specs/011-numeric-group-labels/analysis.md`。

## 第三階段｜US1 學生輸入與修正組號（P1）

獨立驗收以最新加入頁和直接 API 檢查合法值、無效值、修正重送及原資格保留。對應 FR-011-01、SC-011-01。

- [x] T004 [P] [US1] 擴充 `tests/contract/test_classroom_memberships.py`，驗證 1–999 的字串、空白去除、型別檢查與無效輸入無副作用；已有資格者送錯後仍可查閱原本開放中的課堂。
- [x] T005 [P] [US1] 擴充 `tests/student-entry-009.test.cjs`，驗證欄位旁錯誤、原值保留、焦點及 ARIA、修正清除、重新送出，以及欄位錯誤與連線錯誤分開處理。
- [x] T006 [US1] 在 `src/guided_notes/activities/classroom_routes.py` 與 `src/guided_notes/activities/classroom_membership.py` 接入組號驗證。字串先去除前後空白，再完整比對 `[1-9][0-9]{0,2}`，驗證失敗在建立組別、membership 或更新 session 前回傳欄位錯誤。
- [x] T007 [US1] 更新 `src/guided_notes/templates/activities/student_join.html`、`src/guided_notes/static/student-entry.js` 與 `src/guided_notes/static/student-classroom.css`，加入數字鍵盤提示、同一輸入規則、紅字及 ARIA 關聯。有效值仍依伺服器回傳的固定課堂 ID 導航。

## 第四階段｜US2 各畫面一致顯示（P1）

獨立驗收以同一個已建立的組別核對所有畫面均顯示「第 N 組」。對應 FR-011-02、SC-011-02。

- [x] T008 [P] [US2] 在 `tests/contract/test_classroom_results.py` 與 `tests/contract/test_workspace_routes.py` 覆蓋學生狀態、教師組別與在線、作答進度、師生結果及勝組標籤，並核對學生結果投影權限。
- [x] T009 [P] [US2] 在 `tests/integration/test_export_previews.py` 與 `tests/integration/test_export_routes.py` 覆蓋回填預覽與報告以原課堂映射顯示組名，檢查相同組號的其他課堂不影響結果。
- [x] T010 [US2] 提供共用組別標籤格式，接入 `src/guided_notes/activities/classroom_routes.py`、`src/guided_notes/workspace/routes.py` 與 `src/guided_notes/quiz/results_gateway.py` 的授權讀取投影。核對 `src/guided_notes/static/classroom.js` 與 `src/guided_notes/static/student-room.js` 不重複加上前後綴。
- [x] T011 [US2] 更新 `src/guided_notes/notes/routes.py`、`src/guided_notes/notes/templates/notes/export_preview.html` 與 `src/guided_notes/notes/templates/notes/report.html` 的回填顯示，使用已驗權的原課堂映射。保留回填快照及作業識別。

## 第五階段｜US3 保留歷史與隔離（P2）

獨立驗收比對受控資料改動前後的組別識別、勝組與回填，並驗證不同課堂同號隔離。對應 FR-011-03、SC-011-02。

- [x] T012 [P] [US3] 在 `tests/contract/test_classroom_presence.py` 與 `tests/integration/test_classroom_history_009.py` 核對多頁去重、同號跨堂隔離、關課後學生禁讀與教師歷史。
- [x] T013 [US3] 在 `tests/integration/test_quiz_classroom_009.py` 核對現有讀取投影仍指向原組別與原勝組，正式答案、順位、固定版本及回填關聯保持相同。用受控資料驗證，舊測試組名的專屬顯示與恢復排除。

## 第六階段｜整體交付

- [ ] T014 依 `specs/011-numeric-group-labels/quickstart.md` 執行完整 Node 與相關 Python 回歸，再由一位教師與至少兩組學生在空白測試庫實測。將版本、執行者、案例與預期及實際結果寫入 `specs/011-numeric-group-labels/validation.md`。
- [ ] T015 執行 SpecKit Converge，對照程式及 `diagrams/011-component.puml`、`diagrams/011-class.puml`、`diagrams/011-sequence.puml`，將差異、重繪與檢查結果記入 `specs/011-numeric-group-labels/diagram-review.md`。合併前核對驗收證據與組員審查。

## 依賴與交付順序

`T001 → T002 → T003 → US1 → US2 → T014 → T015`。US3 的受控保留測試可與 US2 的顯示測試分開準備，T013 於顯示接線後驗證，T014 同時依賴 US2 與 US3。T004／T005、T008／T009 各操作不同測試檔，可並行。先交付 US1 的加入與欄位提示作為第一個可驗收增量，再加上全部顯示面與歷史回歸。
