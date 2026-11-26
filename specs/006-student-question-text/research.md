# Phase 0：全文資料流與契約研究

日期：2026-11-25；根據目前本機程式與現有套件鎖定檔。未讀使用者 DB／憑證、未呼叫 Sheets，未修改應用程式。本次使用研究代理唯讀複核，主代理核對程式後選擇下列方案；沒有新增第三方技術或需要查核的新套件版本。

## R1 保留 canonical 契約，另加 DisplayContentDTO

**Decision**：CatalogDTO v1、ResultSnapshot v1 及 Submission 不改，新增 DisplayContentDTO v1。
**Rationale**：notes.models 嚴格拒絕未知欄位，test_catalog_contract 已要求 prompt_text 不能混入 v1。文字顯示不需要改回填與排名的資料定義，單獨 DTO 可明確列出安全欄位。
**Alternatives considered**：CatalogDTO v2 有單一入口優點，但需改 001 validator、活動正規化、回填及多套 fixture；直接鬆綁 v1 會破壞既有契約保障。

## R2 從不可變 recognized 投影，不另存 notes manifest

**Decision**：取得已授權的 notes_catalogs.recognized，與同版 catalog 有序比對後只抽文字；不新增 notes display manifest、不重複儲存講義全文。
**Rationale**：save_catalog 已保存 recognized 與 notes_answer_items.prompt_text；真正斷點在公開 catalog 與活動投影。catalog 本身有 no_update/no_delete triggers，獨立 answer_items 未有同等保護，所以以 frozen recognized 為文字權威，避免只查可變關聯表。
**Alternatives considered**：新增講義 manifest 能強調新發布，但會多一個版本狀態並迫使已有完整文字的講義重匯入；本次不需要。學生直接取得 recognized 會洩漏觀察到的答案與來源範圍，禁止。

## R3 獨立活動文字快照

**Decision**：新 activity_displays 表，和活動／questions 在同一寫交易保存安全文字副本；state 只讀此快照。
**Rationale**：submission_context 會把 questions.content 給 003 provider；若在既有 content 加 prompt 就擴大其 context。獨立表可不改答案交換介面，又固定活動文字；同交易避免「活動建好但沒有字」。
**Alternatives considered**：讀 state 時再查講義會讓舊活動無聲多出內容；即時讀 Sheets 則破壞公平、增加延遲與權限負擔。兩者均不採用。

## R4 原文保留與既有預覽

**Decision**：沿用 recognition 的 LF 正規化與空白檢查，保存原文而非 strip 結果；學生採 textContent、pre-wrap／overflow-wrap，逐小題正文緊鄰其作答欄。
**Rationale**：recognize 已對每個合併題目區取得唯一 prompt，且空白會報 ANSWER_AMBIGUOUS；import_preview 已有文字，base.html 的 td 已有 pre-wrap。先用測試驗證，不重做已完成部分。catalog 保存頁目前只有題號，需加安全全文顯示。
**Alternatives considered**：innerHTML／Markdown 解析增加執行或格式歧義；AI 生成／摘要會改原意。原樣儲存格格式、圖片與數學排版不在此範圍。

## R5 缺字與版本錯配

**Decision**：新活動必須有完整且同版的 Display DTO；缺字回 QUESTION_TEXT_UNAVAILABLE，識別錯配回 DISPLAY_CONTENT_MISMATCH。舊活動無快照僅明示 unavailable，不 GET 補寫。已完整保存文字的 catalog 可直接供新活動使用；真的缺字才重新匯入。
**Rationale**：將「舊活動缺快照」與「講義本身缺文字」分開，避免假造資料或無必要重匯入。既有 UUID 與 import_version 決定對應，不查 latest。
**Alternatives considered**：遇到缺字默默只顯示題號會誤報功能正常；填入來源答案或 AI 猜題會違反需求。

## R6 確認狀態與工作範圍

**Decision**：依使用者澄清，全文為雙方原先定義的功能，同學已審圖，不要求重表決；新增技術介面仍交同學審閱。
**Rationale**：先前 pending/BLOCKED 是未取得這次澄清的歷史狀態，不能繼續當目前阻擋，也不虛構確認者姓名。005 與 006 的人工／實作證據分開。
**Alternatives considered**：沿用 005 的同意推論 006 不正確；本次採使用者直接回報作依據，而非推論。

技術疑問均有選擇與理由；方案未實作、未宣稱新測試通過。

## R7 移除示範模式，統一實作前核對

**Decision**：依使用者指示刪除產品示範清單、示範作答受理、設定旗標與專用測試；正式 UUID 契約不增加例外。其他單元／整合測試資料改放 tests/，明確注入 provider，不能出現在正式缺服務的 fallback。
**Rationale**：產品已接真實講義，無需維護示範模式，也就沒有 demo 字串與 UUID 衝突。保留測試隔離才能驗證失敗、競態與安全，不代表保留可啟動的示範功能。
**Alternatives considered**：為 demo 開放例外或改成固定 UUID 映射皆依使用者選擇不採用。保留課程 Demo 影片要求，那是交件規定。

I2 同步改為 tasks 可先產生，新增技術介面／修圖細節在實作前由同學核對並於 T002 記錄，不沿用先前「tasks 前」的文字，也不重問已確認的產品行為。
