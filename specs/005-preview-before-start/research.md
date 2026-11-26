# Phase 0：研究與選擇理由

日期：2026-11-25。依目前 repo 程式與鎖定環境研究，無新增依賴；未讀取使用者 DB、憑證或改寫雲端資料。依 plan skill 由研究代理唯讀複核競態與舊資料策略，結論納入下列決策。

## R1 建立與發布原子化

**Decision**：create_activity 的寫交易同時設定 current_activity_id 及遞增 state_version；state 新增 activity.title。
**Rationale**：現有 classroom_routes.py 建立只插關聯，start 才設目前指標；state_view 已能返回 PREPARING 題目，因此毋須另建題目來源。
**Alternatives considered**：學生另查歷史會有多個顯示權威；建立即 LIVE 違反統一開始。

## R2 同堂一個未結束活動

**Decision**：沿用 db.py 的 BEGIN IMMEDIATE，鎖內重檢所有同堂 PREPARING/LIVE；搭配關聯插入與 phase 更新 trigger。
**Rationale**：現有 schema trigger 只阻止兩個 LIVE；前端或鎖外檢查擋不住雙視窗。
**Alternatives considered**：記憶體鎖不能涵蓋多程序；跨表 partial unique index 不適合現有分表；重複存 phase 增加同步負擔。

## R3 準備中結束及開發資料

**Decision**：允許教師結束目前 PREPARING，保留新流程題目與歷史。使用者於 2026-11-25 澄清仍在開發，可丟棄舊測試資料，改用空白開發 DB，不實作多準備資料相容。
**Rationale**：單活動是大家已同意的規則，本次補齊實作。準備中結束支援選錯講義後重建；不必為可丟棄的開發資料增加清理 UI、遷移及例外狀態。
**Alternatives considered**：保留舊多準備流程已依使用者指示移除；每次啟動自動清空仍不可採用，因為會破壞新流程驗收資料。明確的開發 DB 重置不影響 OAuth 憑證或雲端講義。

## R4 同一活動跨階段更新

**Decision**：沿用一秒輪詢、selection/request/version，更新全部 input/button；建立後刷新 state，錯誤後不無條件啟用按鈕。
**Rationale**：目前 showQuestions 只停用 button，同 id 不重建；建立完成只刷新 history。兩處均需補強才符合預覽與轉 LIVE。
**Alternatives considered**：WebSocket 會擴大依賴；整頁重載干擾課堂操作，兩者皆無本次必要。

## R5 介面與驗證

**Decision**：只增補課堂 state 名稱，不改 CatalogDTO／Submission payload，無新套件或授權需求。
**Rationale**：顯示時間與建立限制不需要完整題目、來源資訊或重做正式 003。既有套件版本依 pyproject/uv.lock，不聲稱已查核新版本。
**Alternatives considered**：增加題目全文擴大使用者未要求範圍；測試 provider 不能作為正式順位完成證明。

技術選擇已定義，沒有未決技術問題；實作、效能與人工驗收仍待執行。
