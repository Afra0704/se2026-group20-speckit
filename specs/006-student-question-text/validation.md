# 006 實作與驗證紀錄

日期：2026-11-25（Asia/Taipei）。執行者：Codex。分支 `codex/006-student-question-text`；起點 commit `812037a46c244aa057769c1969a64c512092403e`，保留 005 及 006 設計文件未提交修改續作。沒有 commit、push、建立／合併 PR，也沒有刪除使用者 DB 或操作真實 Sheets 回填。

## 起點與審查

- prerequisite 指向 006，requirements checklist 16/16，唯讀檢查，沒有代勾。Python 3.13.1、Node v22.12.0，沿用既有 .venv、套件與 Google 授權。
- 依 D19／使用者回報：全文為雙組原先定義的功能，同學已審圖；不重問行為。確認者姓名及獨立紀錄連結未提供。
- **T002 未完成**：尚未收到同學對 Display provider、DTO、activity_displays、state metadata 及 plan 修圖細節逐項核對的結果。本次依使用者明確 implement 指示進行，不能倒填「實作前介面審查已完成」；後續 PR 仍需核對。
- 005 的 T033/T034/T037 人工任務維持未勾，未以自動測試替代。

## 實作與需求對應

| 需求 | 程式與證據 |
| --- | --- |
| FR-001/007 | notes/display_service.py 只投影指定版 notes_catalogs.recognized；核對題號、種類、標號、數量與順序。既有 recognition 的 LF、空白／合併歧義及確認前來源重檢保留。 |
| FR-002/003/005 | classroom.js、activity-sync.js 每小題 textContent，一主題一個 form；共用 question-text.css 保留換行、長字換行、不截斷。教師保存頁 Jinja autoescape。 |
| FR-004 | activity_displays 與活動同交易保存，主鍵／FK／防 update-delete triggers；state 只讀本活動快照。來源改字、重匯入或修改 notes_answer_items 不取代活動文字。 |
| FR-006 | Display 每層嚴格白名單，state 不含 blank_id、原答案、格位或來源 URL。沒有學生直接查 Sheets 的新入口。 |
| FR-008 | CatalogDTO v1、ResultSnapshot v1、Submission、questions.content 及 003 context 不增 prompt。005 單活動／準備中結束／競態及復線保護保留。 |
| FR-009/SC-005 | 刪除 demo_catalog.py、demo_submissions.py、test_demo_entry.py，移除 config/.env 開關與清單／受理 fallback。替代資料僅供 tests/ 注入。 |

既有 catalog 已有完整文字時可建立新活動；真正缺字回 409 QUESTION_TEXT_UNAVAILABLE。舊活動無快照回 unavailable/null，不抓來源／補寫；損壞／錯配回 409 DISPLAY_CONTENT_MISMATCH。缺顯示服務回 503 DISPLAY_CONTENT_UNAVAILABLE，缺清單／受理維持各自 503。

## 自動驗證過程

Display 測試先定義，初跑因模組不存在失敗，實作後最初 21 項通過。Node 全文測試先跑，確認兩畫面及樣式尚缺後失敗，再實作至通過。schema／整合測試在儲存骨架建立後補齊，**並非每項都先紅後綠**，不冒稱全程嚴格 TDD。

初次完整回歸中斷並定位到 fixture 改 UUID、reference 預期仍是 course_id；修正對應。其後完整回歸 250 passed、98 subtests passed、1 failed（005 state 白名單未加入約定 metadata），98 秒；已加入新欄位，保留安全白名單斷言。下一次完整結果為 258 passed、98 subtests passed，105.29 秒；後續補測結果見最終紀錄。

測試檔：tests/contract/test_display_content.py、test_runtime_providers.py、tests/integration/test_student_question_text.py、tests/student-question-text.test.cjs，加上原 catalog、題組交換、匯入／回填及 005 回歸。全部 Sheets 使用受控替代端，Node 是 DOM 模擬；不代表真實雲端讀寫、視覺排版或 5 秒真人同步已驗收。

## 001／002／003 交接

- 001：`get_display_content(teacher_context, import_id, import_version)`，從同版 frozen recognized 提供安全全文，必查教師／import 所有權。
- 002：`get_course_display_content(teacher_context, course_id, import_id, import_version)` 加查 course/import 綁定。`GET_DISPLAY_CONTENT`／`GET_COURSE_DISPLAY_CONTENT` 的 None 使用正式預設，非 callable／缺服務為 503。
- Display v1：根為 display_contract_version/import_id/import_version/questions；question 同 canonical 識別與順序；item 僅 item_id/subitem_label/prompt_text。
- 新表 activity_displays 與活動、questions、目前活動／版本同交易保存；state 增加 display_contract_version、question_text_status、items.prompt_text。讀取不呼叫 Google。
- 003 context／答案、排名及回填契約維持原樣。正式受理未接入仍 QUIZ_UNAVAILABLE，不再有示範受理或假順位。
- 請同學核對新增介面及修圖差異，姓名與實際 review 紀錄待補；此段是交接，不是已核准紀錄。

## 人工待辦

T036/T037 未執行：教師加兩組獨立瀏覽器、單題／題組／移動版型、正文對應、建立後 5 秒同步、開始才填答、準備中結束、換場復線、長中文／英文／Unicode／換行、HTML 純文字及來源答案隔離。依 quickstart 記錄操作者、日期、版本、預期／實際及去機敏截圖；未完成前不宣稱完整交付或 converged。

## PR 草稿（尚未送出）

標題：`feat: show immutable full question text and remove built-in demo mode`

補齊保存講義全文到活動及學生畫面的傳遞，建立後可讀、開始後才填，題組整組提交；新增嚴格 Display v1 與不可變活動快照，不改原 catalog／排名／回填契約。移除內建示範清單、受理及設定。包含沿用 005 的單活動與準備中結束修改。

審閱依據：[spec](spec.md)、[plan](plan.md)、[contract](contracts/display-content.md)、[tasks](tasks.md)、[圖意核對](diagram-review.md)、本紀錄。人工／5 秒／排版及新增介面審查待完成，正式 003 尚未整合；不自動 commit/push/送 PR。


## 最終自動結果

- `.venv/Scripts/python.exe -m pytest tests -q --tb=short`：退出碼 0，**265 passed、98 subtests passed，99.12 秒**。包含原 v1 嚴格拒絕 prompt、003 context、005 競態／準備中結束、回填與恢復的回歸。
- `node --test tests/student-question-text.test.cjs tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs tests/activity-sync.test.cjs tests/notes-ui.test.cjs`：退出碼 0，**12 tests passed，0 failed**。
- 新契約／provider／全文整合集中測試：最後一次 **44 passed**；完整回歸另包含所有案例。安全 sentinel 測試最初遇到 fixture 空答案格省略尾欄的 IndexError，已補齊測試格位並重驗通過；不是產品讀寫故障。
- `git diff --check`：退出碼 0；新檔另檢查行尾空白。PlantUML CLI 退出碼 0，三圖 PNG 成功重新產生。
- prerequisite script、checklist、ignore 設定及 hooks 均已核對；extensions.yml 不存在。
- 未進行本版真人瀏覽器操作、5 秒計時、真實 Google 回填，未變更既有教師或憑證。伺服器須從目前工作樹重新啟動才能人工測試；只重整不會載入新 Python。

最終 analyze／converge 輸出由 implement 記錄至 analysis.md。剩餘兩類 partial（真人證據、同學介面審查）追加 T041/T042；尚未 converged。不以自動通過代勾 T002/T036/T037 或 005 人工項。


## 使用者回報與顯示微調（2026-11-25）

使用者回報測試成功，附圖可見題組正文／標號與輸入欄，另指出單題正文前多出「答案」預設標籤。依此修正兩種學生畫面：沒有 subitem_label 的單題不額外插入「答案」，直接顯示正文與輸入框；題組保留既有小題標號。屬 006 顯示修正，未變更 DTO、提交單位或活動規則。

修正後重跑六份 Node 測試：12 passed、0 failed；git diff --check 通過。尚待使用者強制重新整理確認修正外觀。此次回報未附完整操作者／版本／5 秒／各情境記錄，不代勾全部人工任務。

## 2026-11-26 跨功能人工驗收補充

本輪使用者逐步操作的真實Google／瀏覽器驗收，集中記錄於 `specs/008-teacher-course-workspace/validation.md` 的「真實 Google 操作進度」及後續第18–39步紀錄。已涵蓋兩教師隔離與權限恢復、教師登出保留學生、兩組學生全文／階段／同堂活動／恢復、單題移動欄列與建立／開始同步不到1秒、純文字／換行／Unicode及來源答案隔離、來源修改保持活動快照、重啟資料保留等相關子項。

證據為使用者回報；操作者姓名及瀏覽器版本未提供。依原聚合任務要求，未直接將整項人工任務勾選；仍需具名介面／圖意互審、未執行的子情境及正式003／回填整合。後續引用已取得證據，只補缺項，不要求重做已確認操作。
