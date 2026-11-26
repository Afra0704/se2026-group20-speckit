# Implementation Plan: 學生查看完整題目文字

**Status**: 自動驗證範圍已實作，結果及人工／介面審查待辦見 [validation.md](validation.md)。
**Branch**: `codex/006-student-question-text`，由 005 未提交工作樹建立並保留既有修改，未 commit/push。
**Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)
**Input**: 全文顯示為雙方原先定義功能的補齊；使用者回報同學已審圖，姓名與獨立紀錄待補。

## Summary

保留 CatalogDTO v1、ResultSnapshot v1、Submission payload 與 003 question context 不變，另定義安全 DisplayContentDTO v1。從指定版本 `notes_catalogs.recognized` 的不可變快照取得文字，與同版 catalog 的有序題號、種類、小題及識別完整核對。建立活動時在既有交易內保存獨立 `activity_displays` 文字快照；學生只讀活動快照，不能即時抓 Sheets 或補寫既有活動。

沿用 005：建立即預覽，開始後才可填答，同堂只允許一個 PREPARING/LIVE，準備中也可結束。前端以純文字顯示每小題全文，保留換行、符號及長文字換行。既有版本真的缺字才提示重新匯入；已完整保存文字的 catalog 可直接供新活動使用，這是安全投影既有資料，不是遷移或改寫舊活動。

## Technical Context

**Language/Version**: Python 3.13、既有原生 JavaScript。
**Primary Dependencies**: 沿用 Flask、Jinja、SQLite 與既有 Google SDK／uv.lock，不新增套件、模型、scope 或雲端服務。
**Storage**: 保留 notes_catalogs／questions 原資料形狀；在共用 activity schema 加入 activity_displays（活動 ID 唯一、安全 DTO JSON、建立時間），內容不可變。只新增空表及 trigger，不回填舊列。
**Testing**: pytest 的契約、服務及跨模組測試；Node VM 渲染／同步測試；教師及至少兩組學生瀏覽器人工驗收。
**Target Platform**: Windows 本機 Flask、Chrome／Edge；所有程序須從目前工作樹重新啟動。
**Project Type**: 現有 Web app 功能補齊，以課堂模式為主要驗收流程。
**Performance Goals**: 沿用一秒輪詢；穩定本機環境建立後 5 秒內兩組看到全文，讀狀態不增加 Sheets 網路請求。
**Constraints**: 文字不可截斷、不可當 HTML；不提供圖片、原樣格式或數學式排版。不改答案、排名、回填與教師權限。005 人工任務保持未完成。
**Scale/Scope**: 每個主題／小題的可讀文字及其固定活動快照；不承諾未測的大型班級效能。

## Constitution Check

| 原則 | 設計前／設計後結果 |
| --- | --- |
| I 共同需求 | 使用者澄清全文是雙方原先定義，OpenSpec 原先已知；D19 改記補齊，不要求重表決。具體介面須同學核對，姓名／獨立紀錄待補。 |
| II 圖表優先 | specify 三圖已渲染、使用者回報同學已審。plan 將「固定內容」展開為安全顯示 DTO 與獨立活動快照，已同步修圖及重渲染，新增技術細節待同學核對，未冒稱另行審過。 |
| III 動態與回填 | 文字取自辨識出的題目欄、按版本與項目對齊；canonical IDs／blank 對應不改，來源答案不作文字。 |
| IV 權限與機敏 | 教師／課程／import 歸屬重檢；學生只取得白名單文字，排除來源答案／座標／他組資料；HTML 文字不得執行。 |
| V AI／人工 | 規劃來源變動、對應錯誤、安全及雙組真人驗收；目前未寫程式、未跑新功能測試。 |
| VI 文件與流程 | 本次只有 plan Phase 0/1 文件，後續 tasks→analyze→implement→converge；005 驗收不代勾，介面範圍不默默擴張。 |

原先 BLOCKED 依使用者澄清解除，未改憲章或虛構確認。無須豁免；同學須審閱 plan 細節與修圖差異，正式驗收仍是未來任務。

## Project Structure

### Documentation (this feature)

```text
specs/006-student-question-text/
  spec.md, plan.md, research.md, data-model.md
  contracts/display-content.md, quickstart.md
  diagram-review.md, checklists/requirements.md
  tasks.md  # 後續產生
diagrams/006-{component,class,sequence}.{puml,png}
```

### Source Code (repository root)

```text
src/guided_notes/notes/
  display_models.py       # 新增 DisplayContentDTO 白名單及跨資料核對
  display_service.py      # 新增指定版本安全文字提供端
  import_service.py, repository.py, course_catalogs.py, routes.py
  templates/notes/import_preview.html, templates/notes/catalog.html
src/guided_notes/activities/
  display_service.py      # 新增活動快照驗證／保存／讀取
  schema.sql, classroom_catalog.py, classroom_routes.py
  teacher_routes.py, state_routes.py
src/guided_notes/static/classroom.js
src/guided_notes/static/classroom.css
src/guided_notes/static/activity-sync.js  # legacy 安全文字與缺字提示
src/guided_notes/static/question-text.css # 新增僅正文作用的共用樣式
src/guided_notes/templates/activities/classroom.html
src/guided_notes/templates/activities/student.html
tests/contract/test_display_content.py             # 新增
tests/integration/test_student_question_text.py    # 新增
tests/student-question-text.test.cjs               # 新增
tests/conftest.py
tests/catalog_support.py                          # 測試專用有效 UUID 資料
tests/contract/test_runtime_providers.py           # 移除示範及缺服務回歸
```

**Structure Decision**: 在 001 提供安全文字、002 保存活動顯示快照、學生 state 合併投影；不把文字塞進供 003 使用的 questions.content，不另建 app factory、登入或資料庫。

## 模組責任、資料流與三圖對照

1. **動態辨識與預覽**：沿用 recognition 的題目欄／合併格邏輯。它已正規化 CRLF/CR→LF、拒絕空白 prompt，不重寫辨識。import_preview 已顯示文字且 base.html 的 td 已有 pre-wrap／overflow-wrap；先測試實際效果，沒有缺口不重複加 CSS。confirm 再讀來源及版本保存流程沿用，文字已在 semantic hash 中。
2. **固定講義版本**：`display_service.get_display_content()` 只讀教師擁有的明確 import_id/version，從不可更新／刪除的 catalog.recognized 快照做白名單投影。以 catalog 中 IDs 配對，並核對題號、種類、數量、順序與小題標號。不得把 recognized 的答案觀察或座標放進 DTO。缺字、額外／重複項及錯版皆失敗，不取最新版本補足。
3. **活動管理**：課堂 wrapper 增加 GET_COURSE_DISPLAY_CONTENT 提供端；沿用教師／course/import 綁定驗證。catalog 與 display 在持寫鎖前讀取，並驗證精確同版；進入 005 activity_transaction 後重檢教師、OPEN 與單活動限制，在同一筆交易寫 activity、questions、activity_displays 及 current/state_version。任一步失敗全部回滾。
4. **活動快照**：activity_displays 存安全 DTO 的完整 JSON 副本，主鍵 activity_id，限制 update/delete；歷史內容不被新匯入或來源變動改寫。舊活動沒有快照只回 unavailable，不在 GET 寫入或重新讀 Sheets。
5. **學生顯示**：state_view 先讀該活動 core questions，再按 ID 與順序驗證 display 快照並合併 `prompt_text`；根層加入 display_contract_version 與 question_text_status。使用新的明確 question/item 白名單，不將 core／私有資料任意透傳。classroom.js 每小題在作答欄前顯示正文，用 textContent；共用 question-text.css 僅對 .question-prompt 套用 pre-wrap、overflow-wrap:anywhere，無 max-height 截斷，classroom.html/student.html 明確載入，不為 legacy 套上整份課堂版面。活動 ID 換場時重建，保留同 ID 階段更新與防亂序。legacy activity-sync.js 也補相同全文／unavailable 提示與文字樣式，維持它原有身分及階段操作，不新增課堂行為。
6. **教師保存頁**：catalog.html 透過授權的安全 display 顯示已保存全文，保留教師專用來源對應表。JSON catalog 端點仍返回原 v1，不混入新欄位；文字缺漏明確提示重新匯入。

## 契約與相容邊界

- **不變**：CatalogDTO v1 的 strict unknown-field 拒絕測試繼續保留；ResultSnapshot、Submission payload、questions.content 及 003 context 不加 prompt，回填仍使用原身分／版本。
- **新增**：DisplayContentDTO v1 及 provider、activity_displays、安全 state 的文字欄位；格式與錯誤見 contracts/display-content.md。
- **舊 catalog**：若原不可變 recognized 已完整有字，可產生同版安全 DTO 給新活動；真的缺字則拒絕新建並提示重匯入。不產生新假版本、不批次遷移／補寫資料。
- **舊活動**：即使來源 catalog 有字也不在 state 即時接上，沒有當時快照就顯示 unavailable；老師先結束舊活動，再從完整版本建立新活動，無需為已有完整資料強迫重新匯入。
- **legacy 模式**：共用 state 可明示 unavailable。非課堂 `/activities` 建立路徑使用同一安全顯示服務（GET_DISPLAY_CONTENT）與原子保存，維持既有身份／階段語意；不把 005 的單課堂規則套到 legacy。
- **測試替代端**：tests/conftest 的 GET_CATALOG／GET_COURSE_CATALOG fixture 明確提供對應 display provider，使用有效 UUID；受控資料與替代受理只存在測試中，不新增產品示範入口。正式設定不得注入假受理／結算。
- **示範模式移除**：依使用者指示刪除 activities/demo_catalog.py、quiz/demo_submissions.py、config 的 DEMO_CATALOG／GUIDED_NOTES_DEMO_CATALOG、teacher／classroom_catalog 的示範分支及 submission_gateway 的示範受理 fallback。刪除專用 test_demo_entry，其他測試改用僅存在 tests/ 的正式形狀資料及顯式 provider，不依賴刪除的產品模組。清單、顯示或正式 003 服務缺少時分別回既有 503，不產生假資料；不刪使用者 DB 或正常活動。

## 驗證、依賴與實作前介面核對

契約先驗證 IDs／版本／順序／標號全等、未知欄位拒絕、缺字與 Unicode 原文保存；再測匯入預覽→確認→新活動→兩組安全 state，來源改版不動舊活動。Node 測文字以 textContent 顯示、標號與輸入對應、換場／重連與 005 控制；瀏覽器人工核對中文換行、長字串、特殊符號、實際不截字及 5 秒同步。

回歸必須涵蓋原 v1 契約、整組答案完整性、指定活動回填、005 單活動／準備中結束／交易競態。替代來源測試不得冒稱真實 Sheets 寫回。新測試清單與操作見 quickstart。

FR-009／SC-005 另須核對示範清單、示範作答、環境旗標、專用測試、產品 imports 與啟動說明全部移除；使用者殘留舊旗標不會切回示範路徑。tests/catalog_support.py 為測試專用資料，不可被 src/ 匯入；缺正式服務的案例必須驗證約定不可用回應，而非一律注入替代端使其假成功。

可先產生 tasks；實作前由同學核對新增 Display DTO/provider、獨立表、state metadata 與修圖技術差異，於 T002 記錄結果，未回報不代勾。這是技術介面核對，不是重新確認已同意的全文行為。示範模式依使用者指示移除，正式 UUID 驗證不設例外。不需要新增模型／OAuth；005 未完成人工任務繼續獨立追蹤。

## Complexity Tracking

沒有憲章豁免。獨立活動快照表比修改所有 003／回填嚴格契約影響較小；不新增 notes manifest，因為既有不可變 recognized 已足以提供同版文字。
