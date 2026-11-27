# 012 圖表與階段紀錄

日期：2026-11-27；執行：Codex；基底：`e9a29c7`（PR #14 合併）。

## 產出與實際驗證

- [規格](spec.md) 與 [品質核對](checklists/requirements.md) 已完成文字檢查。
- [Component](../../diagrams/012-component.png)、[Class](../../diagrams/012-class.png)、[Sequence](../../diagrams/012-sequence.png) 及同名 `.puml` 為概念設計，不代表實作已完成。
- CLI：`& 'C:/Program Files/Java/jdk-24/bin/java.exe' '-Djava.awt.headless=true' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar -charset UTF-8 -tpng 'D:/os_final/diagrams/012-*.puml'`，退出碼 0。
- Codex 已開啟三張 PNG：中文、關係、權限及恢復分支可讀，無錯誤頁或裁切。檢視時發現 PlantUML 將井字號解讀為編號，已改寫為 Issue 16／Issue 20 並重渲染。
- 未修改產品程式，未執行產品測試；未操作真實 DB、Google 憑證或 Sheets。

## 待審事項與相依契約

- [x] 使用者於本聊天室回報「已審查」後呼叫 speckit-plan；視為本輪原三圖審查回報，審查者姓名／獨立紀錄未提供。技術細節補註仍列於後文，不冒稱組員另行審查。
- [x] #16 實際格式化介面及 PR22 合併版本已由 Codex 核對，證據見 validation.md；不代表具名互審。
- [x] #20 契約與本機實作 4199675 的時間來源／事件／分鐘格式已核對並整合，核心不重做；未改另一 worktree。
- [x] #19 C1-A–C 共同操作規則依 2026-11-27 本聊天室使用者回報「已雙組確認」記錄；姓名／外部紀錄未提供。
- [ ] 具名認領與模組技術介面（含資料對應錯誤 reason）仍依整合任務核對，不與共同行為確認混同。
- [x] Phase 0／1 plan：研究、資料模型、三份契約及 quickstart 已產出；不代表 tasks／analyze／implement 或驗收完成。
- [ ] 後續 tasks／analyze／implement／驗收與收斂；真人 Sheets 與教師加兩組驗收均未執行。

## 工作區保留

另建 `codex/012-result-writeback` 分支；原 `specs/011-time-display/` 草稿及其他未追蹤檔保留。本機 `.specify/feature.json` 改指 `specs/012-result-writeback`；接續 #20 時應切回其分支並恢復指向 `specs/011-time-display`。本輪未 push 或代發 GitHub 留言。

## Plan 技術核對（2026-11-27）

研究確認原服務允許全無勝組的 skip 預覽；為保留低階契約，Sequence 補明全 skip 預覽可顯示，UI 停用確認。未結束／未結算仍各自拒絕。這是原「無勝組提示、零寫入」規則的技術補註，不新增使用者流程。勝組錯誤沿用 RESULT_INVALID 加安全 reason，既有歷史報告保留；Component／Class 補註此點。實際 CLI 與原產圖命令相同，重渲染退出碼 0；Codex 已開啟三圖核對，新增分支、文字及關係可讀，無錯誤頁或裁切。此次技術核對不代替具名互審、OpenSpec 確認或產品測試。

## Plan 產物驗證

### 實作對圖（2026-11-27）

Component 的權限／脈絡對應 notes/export_context.py 的 activity_context／winner_labels；結果入口對應 static/classroom.js 的 refreshResult／activityList。Class 原課堂組號已依 #16 真實欄位改為 classroom_groups.name canonical 字串，ID 與 label 分開，不新增 DB 欄位；DTO 投影不改 snapshot。Sequence 的來源前／保存前／每批寫入前／恢復前校驗分別對應 export_service.create_saved_preview、writeback.confirm／_snapshot／recovery_preview，返回 query 對應 workspace.classroom。既有恢復／覆寫狀態機保持。

三圖以既有 CLI 命令重渲染 exit 0，Codex 已逐張檢視文字、關係及分支可讀、無錯誤頁或裁切。Component 最新時間註記指向已整合的 time_display／time_views；這是 AI 實作核對，不代表組員新一輪技術互審或人工驗收。

### C1 確認回報更新（2026-11-27）

使用者針對 C1-A–C 回報「已雙組確認」，已同步 spec、plan、research、相依契約、T004 與共同需求；確認範圍及證據限制詳見 dependency-boundaries。先前「C1 未解決」為歷史紀錄，以本段為最新狀態。U1 返回契約、I1 唯讀與後續保存分離、I2 並行依賴修正均保留，C1 行為門檻通過。#20 最新文件已確認台北至分鐘，本次同步 012 的舊到秒描述；技術函數、提交版本、模組互審及真人驗收不因此完成。

### Analyze 後獲授權修正（2026-11-27）

使用者指示「其他照你的建議修改」，據此於 analyze 之外的本次編輯修正 U1／I1／I2：補原結果返回 URL／同堂驗權／query 初始化與刷新測試，將 analyze 的唯讀執行與後續獲授權保存分開，統一 T024／T025 並行相依。C1-A–C 待確認規則已列入 dependency-boundaries，未把使用者詢問當作雙組確認，也未將 C1 標為已解決。

Sequence 只補返回原結果的技術註記；以既有 Java／PlantUML CLI 重渲染該 PNG，退出碼 0，Codex 已開圖確認文字可讀且無裁切。46 個任務仍全部未勾選，9 個 [P]；連號、依賴圖、文件連結及行尾空白檢查通過，`git diff --check` 通過。未重新呼叫 analyze，未改產品程式、執行產品測試或操作真實來源。

10 份本功能 Markdown 的本機連結、範本殘留、行尾空白，以及三份 PNG 格式／更新時間檢查通過；`git diff --check` 通過。原 `.specify/extensions.yml` 不存在，before_plan／after_plan 無 hook 可執行。setup-plan JSON 的 BRANCH 為工具正規化值 `012-result-writeback`；實際 Git 分支以 `git branch --show-current` 核對為 `codex/012-result-writeback`。本輪僅 plan 文件與圖表檢查，未跑產品測試，未 commit／push。
