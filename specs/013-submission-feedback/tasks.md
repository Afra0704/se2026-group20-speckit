# 013 學生送答提示一致化任務

依據 [規格](spec.md)、[計畫](plan.md)、[資料模型](data-model.md)、[送答契約](contracts/submission-feedback.md)與[驗收指南](quickstart.md)。[P] 表示先完成相依任務後可並行，執行時仍須避免同檔同時修改。

## 第一階段｜準備

- [x] T001 核對 Issue #18 專用分支含已合併的 #17 及已審三圖。依 `specs/013-submission-feedback/quickstart.md` 執行既有 Node、Python 送答與分頁基線，建立 `specs/013-submission-feedback/validation.md` 記錄版本、命令、結果與測試環境。

## 第二階段｜共同基礎

- [x] T002 核對 `src/guided_notes/quiz/activity_routes.py`、`src/guided_notes/quiz/submission_gateway.py`、`src/guided_notes/quiz/repository.py` 及 `src/guided_notes/activities/submission_context.py` 的驗權、驗空、查重與受理順序，將先於查重的拒絕和原操作確定結果對照補入 `specs/013-submission-feedback/contracts/submission-feedback.md`，供 US2／US3 共用。
- [x] T003 核對 `src/guided_notes/static/student-room.js` 與 `src/guided_notes/static/quiz-submission.js` 的表單生命週期及 #17 儲存相容性。在 `specs/013-submission-feedback/data-model.md` 標明雜湊或序列化相容性界線、錯誤回覆與畫面失效點。保留「固定課堂 ID、活動 ID、組別 ID、題目 ID、#17 文件作用域。每個作用域最多一個未決操作。」

## 第三階段｜US1 學生找到漏填位置（P1，MVP）

對應 FR-001／FR-003、SC-001。獨立驗收以一題單題和一題多小題操作，錯誤只出現在空白欄位，保留其餘輸入，無正式受理。

- [x] T004 [P] [US1] 在 `tests/contract/test_quiz_submission.py` 補空字串、純空白、漏填、格式錯誤與非空原文案例，驗證已授權的本題欄位才可出現在 invalid_item_ids，空白拒絕不新增受理。覆蓋 U+0085、U+001C 與 U+FEFF，並驗證非空原文。
- [x] T005 [P] [US1] 在 `tests/student-room-quiz-009.test.cjs` 補有效與無效欄位並存、空白判定、第一錯誤欄位焦點、aria-invalid／提示關聯、逐欄修正及無效時無送出請求，含 U+0085、U+001C 與 U+FEFF 的共同判定案例。
- [x] T006 [P] [US1] 在 `src/guided_notes/quiz/submission_gateway.py` 與 `src/guided_notes/http.py` 為已授權且可定位的空白或漏填附加 invalid_item_ids，維持 400 INVALID_ITEMS 和既有 error 欄位。重複、外來或結構錯誤維持拒絕，回應不揭露答案。
- [x] T007 [P] [US1] 在 `src/guided_notes/static/student-room.js`、`src/guided_notes/static/quiz-submission.js`、`src/guided_notes/static/student-classroom.css` 按契約碼位集合接入逐欄驗空、欄位紅字、鍵盤焦點及後端欄位提示。維持「原始文字、已知小題 ID、局部錯誤。驗空使用暫時判斷值，新的有效操作保存原文。」

## 第四階段｜US2 學生辨認本題送答結果（P1）

對應 FR-002／FR-003／FR-004、SC-002。獨立驗收逐題操作提交、送出中、受理、格式或階段明確拒絕、限流與無法確認的回應。確認其他題目與連線狀態獨立。

- [x] T008 [P] [US2] 在 `tests/quiz-submission.test.cjs` 補首次提交、避免重複點擊、201 accepted、400 INVALID_ITEMS、409 INVALID_PHASE／SUBMISSION_REPLAY_CONFLICT、429、5xx 和不可判定的回應。確認未受理過不能顯示「重新提交」。
- [x] T009 [P] [US2] 在 `tests/student-room-quiz-009.test.cjs` 補雙題狀態獨立、同活動輪詢保留當前回饋、切換活動清除舊回饋與連線提示分離。
- [x] T010 [US2] 在 `src/guided_notes/static/quiz-submission.js` 實作未提交、送出中、已受理、明確拒絕及結果未知的處理。維持「目前狀態、是否已有可確認的受理、欄位提示及目前嘗試。畫面重建時只讀取目前作用域，上一活動的提示不延伸。」
- [x] T011 [US2] 在 `src/guided_notes/static/student-room.js` 傳遞 HTTP 狀態、錯誤資訊及可用的 Retry-After，於題目旁更新可讀的狀態與提交按鈕。保留 #17 的全頁資格及連線訊息，首次 429 與結果未知採契約所定分類。

## 第五階段｜US3 結果未知時安全重試（P1）

對應 FR-005／FR-006／FR-007／FR-008、SC-003。獨立驗收分別模擬未達和受理後遺失回覆，再編輯輸入並按重試，核對原操作、原文、目前輸入及順位。

- [x] T012 [P] [US3] 在 `tests/quiz-submission.test.cjs` 補結果未知時允許編輯、禁止提交新內容，手動重試原 UUID／原內容，保留編輯值。涵蓋重試先遇 429 或驗權拒絕、後續確認受理、失效畫面的晚到成功或拒絕與新操作並存，另測重送衝突後停用提交／重試、保留編輯值與同頁恢復。
- [x] T013 [P] [US3] 在 `tests/student-room-quiz-009.test.cjs` 與 `tests/student-presence-lifecycle.test.cjs` 補有效同頁交接恢復、複製頁不承接、取消重新加入保留、確認只清本頁、教師關課與切換活動。核對恢復不自動重試。
- [x] T014 [P] [US3] 在 `tests/integration/test_classroom_submission_races_009.py` 驗證已受理後原樣重送不增加受理或重新取順位，新操作若已受理，晚到的舊操作也不覆蓋有效答案。核對角色可見範圍與原文。
- [x] T015 [US3] 在 `src/guided_notes/static/quiz-submission.js` 接入「既有 UUID 與原始提交內容。本頁短暫的嘗試識別用於拒絕晚回；持久格式相容 #17 的既有記錄。」重試期間保留編輯值，先於原操作查重的拒絕不得錯誤結清。重送衝突記錄相容的選填標記，新提交與同內容重試停用，提示核對或依 #17 重新加入。同時檢查作用域及最新嘗試才可更新畫面或清理未決記錄。
- [x] T016 [US3] 在 `src/guided_notes/static/student-room.js` 接通 #17 文件交接、複製、關課、重新加入和畫面世代。只清被撤回頁的本地操作，切換活動阻擋晚回，保留教師在線及結果流程。確認正式受理紀錄為「003 的受理序列及同組重送記錄，原樣重試查回既有結果。無額外寫入。」

## 第六階段｜整體回歸與交付

- [x] T017 [P] 依 `specs/013-submission-feedback/quickstart.md` 執行完整 Python／Node 回歸與教師、一位學生和另一組學生的真人驗收，將鍵盤、窄視窗、受控回覆遺失及原順位的證據寫入 `specs/013-submission-feedback/validation.md`。記錄執行者、日期、版本、場景、預期及實際。
- [x] T018 [P] 以 `diagrams/013-submission-feedback-component.puml`、`diagrams/013-submission-feedback-class.puml`、`diagrams/013-submission-feedback-sequence.puml` 對照實作並記入 `specs/013-submission-feedback/diagram-review.md`。有行為差異時更新原圖、重繪 PNG 並取得複核。
- [x] T019 匯整 Analyze 與實作後 Converge 結果至 `specs/013-submission-feedback/validation.md`，追溯 FR-001～FR-008 與 SC-001～SC-004，確認自動結果、真人驗收與組員互審的證據齊備後交付。

## 依賴與執行順序

`T001 → T002 → T003 → US1 → US2 → US3 → T017／T018 → T019`。任務生成後先執行 Analyze，再開工修改產品程式。US2 與 US3 依序接線，因為共用表單與狀態模組，每一階段仍可依該階段的獨立驗收直接驗證。

### 並行例子

- US1 的 Python 契約 T004 與前端案例 T005 可並行。兩組測試備妥後，後端 T006 和前端 T007 可依同一契約分工，再一起回歸。
- US2 的 T008、T009 寫不同測試檔，可並行。先完成 T010，再讓 T011 接線。
- US3 的 T012、T013、T014 可並行。T015 固定核心操作，T016 再整合 #17。

## 實作策略

先交付 US1 作為可單獨驗收的 MVP，完成逐欄提示與服務端契約。再加入 US2 的本題狀態及 US3 的原樣重試。三段都完成並通過交付驗收後，才完成 Issue #18。

## Phase 7: Convergence

2026-11-28：已讀目前規格／計畫／19任務與實作；不因舊勾選推定完成。功能程式未發現新增缺漏，剩餘交付證據如下。沿用T017–T019，不改舊勾選；本節只追加可執行的補正工作。

- [x] T020 補齊US3/AC2、SC-003、T017及quickstart真人情境4：在原頁有未決送答時，驗證F5後不自動送答但可手動原樣重試；原生複製頁不承接原頁重試；取消重新加入保留pending而確認只清本頁。記錄原正式答案與順位、兩組不互相影響，更新validation.md與manual-acceptance.md。現有Node及後端測試已通過，這是人工交付證據partial，不是已知程式失敗。
- [x] T021 依Constitution II／VI、plan圖對碼及T018–T019，請另一位組員複核A1更新後時序圖與目前實作，記錄實際回報及可提供的確認者／連結；核對delivery-check.md的程式責任與狀態分支，完成後重跑converge並更新交付狀態。原三圖舊審查不能替代此次差異確認（partial）。
