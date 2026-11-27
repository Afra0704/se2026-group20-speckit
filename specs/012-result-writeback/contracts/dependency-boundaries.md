# 相依契約與檔案責任

此文件是 #19 的整合需求與建議，不代表相依作者已承諾函數名、提交或本輪協作完成。

| 功能 | 提供／負責 | #19 使用方式 | 整合檢查 |
| --- | --- | --- | --- |
| #16 組號 | trim 後接受 canonical 1–999、共用「第 N 組」formatter；原堂組 ID／組號資料表示 | 從原堂查到記錄後才格式化，不依 ID 推組號；不改學生表單或 INVALID_GROUP_NUMBER | 紀錄合流 SHA、實際模組函數、輸入／輸出與錯誤政策；1／42／999、跨堂同號、無效記錄 |
| #20 時間 | 共用 UTC／offset 傳輸、台北至分鐘（YYYY-MM-DD HH:mm，截取不進位）、缺值／未知／壞值處理 | 傳原欄位及事件語意，不自建時間核心 | 紀錄 helper、來源 tag、fallback 契約；naive SQLite UTC、帶 offset、跨午夜、空／壞值 |
| 003 結算 | get_ended_snapshot、固定 result_version、原 winner_group_id／答案 | 不改不可變 snapshot exact keys；所有 label 在外層 | digest／winner／rank／answers 完全不變 |
| 001／PR14 回填 | 預覽、冪等確認、覆寫、source lease、回讀恢復及安全重連 | 沿用原端點與狀態機，加 context／原堂勝組檢查 | restart、原覆寫同意、新衝突、部分／未知、重新授權回原活動 |

## 修改責任建議

- #19：新增 notes/export_context.py；結果入口 classroom.js；notes context 接線與模板；正式課堂回填回歸。
- #16：組別資料／驗證／formatter 核心。#19 不在其核心塞回填邏輯，也不猜舊名稱。
- #20：共用時間核心及 notes_time 接線；#19 只新增需要呈現的語意欄位。notes/routes.py、classroom.js 可能共同涉及，應以小範圍提交／明確接線避免整檔覆蓋。
- 無權在本輪代替他人認領、發 issue 留言或把未回報的 OpenSpec 確認勾選。

## 實作前清單

- [x] #16／#20 已提供可引用版本及實際介面，與本契約對照完成；實作版本見下方最新紀錄。
- [ ] RESULT_INVALID 的安全 reason 與報告保留行為經相關模組作者核對。
- [x] #19 新入口／顯示流程 C1-A–C 已依 2026-11-27 本聊天室使用者回報「已雙組確認」記錄；範圍與來源見下文。
- [ ] 同步當時最新已合併 master，保留其他功能的未提交修改。

#20 最新共同需求及 011 規格已記錄固定台北、顯示到分鐘的確認；#19 沿用，不另選時區。#16 雙組確認依使用者回報，真人驗收仍待完成。

## C1 已確認的共同規則範圍

2026-11-27（Asia/Taipei），使用者在本聊天室針對下列 C1-A–C 回報「已雙組確認」，據此記為 SpecKit／OpenSpec 已確認。確認者姓名、獨立紀錄連結及實際討論時間未提供，不補造具名或外部審查證據。

| 編號 | 已確認的新增行為 | 共同規則 |
| --- | --- | --- |
| C1-A | 從活動結果進入及返回回填 | 目前／歷史結果可直接按「預覽回填講義」，不用抄 ID；預覽、報告、返回結果均固定所選原活動，刷新不換成最新活動 |
| C1-B | 找不到原堂勝組時的可見處理 | 清楚顯示資料對應錯誤並禁止新寫入，不猜組名；既有預覽／報告仍可供原教師檢查，保留操作明細，停用確認／恢復 |
| C1-C | 回填狀態提示與全部無勝組 | 未結束、未結算、無勝組各自提示；全部無勝組可顯示略過預覽，但 UI 不提供確認；部分無勝組僅略過該題 |

已確認／既有規則不列入重新確認：#16 的 1–999／「第 N 組」與原課堂組 ID 對應；既有教師歷史權限、關課與移除清單保留歷史；先預覽再確認、覆寫同意、授權恢復、先回讀及不重送已完成題。實際套用仍需依原確認紀錄核對，不擴張 #16 為 #19 新流程已確認。

formatter 函數名、SQLite JOIN、檔案分工、HTTP 內部診斷 reason、結果頁 query 名稱屬技術對齊，不要求 OpenSpec 採同一程式結構。#20 的時區／格式由其自身確認流程負責，#19 不另創規則。

C1 共同行為確認門檻已滿足。此不表示 formatter／時間 helper 已合流、HTTP 診斷 reason 已由模組作者核對、認領留言已發布，亦不代表實作、技術互審或真人驗收通過；這些項目按原任務分別核對。後續若改變 C1-A–C 行為，須先確認變更並同步規格，不將本次確認外推。

## 2026-11-27 implement 實際介面查核

#16 已由 PR22 合併並整合至本分支 `80510a6bbf6310bf4634052a7a56066f8f1e8baf`，PR head 為 `86c59bfcd4aa2ee7e40e7984d0ae14df0daa4293`。實際共用函數為 `activities.classroom_membership.group_number(value)`／`group_label(name)`，組號存 `classroom_groups.name` canonical 字串，ID 仍維持原身分。group_label 對舊非數字值 passthrough；#19 resolver 須明確檢查可合法格式化的新數字組，不能猜舊文字。notes.routes.export_group_labels 已提供原堂 HTML 投影，後續集中接線，避免複製 formatter。

#20 當時僅有契約與規劃，`src/guided_notes/time_display.py` 尚不存在。提案 present_time／DisplayTime 與分鐘政策可對照，但無可呼叫實作／合流 SHA；T003 維持未完成。此為程式相依缺口，不是要求重新確認 C1 或時間政策。詳細基底與 10 項實際測試見 [validation.md](../validation.md)。

### 接續實作的最新狀態

後續重新執行 implement 時，已找到本機獨立 worktree 的 #20 提交並整合至 `4199675`（核心 aecb22e、接線 772af09）。實際 `time_display.present_time`／`DisplayTime` 與契約一致，`time_views.activity_time_display` 接原課堂 UTC 事件、`notes_time`／`readback_time` 接帶 offset 的 notes 時間，畫面至分鐘。原先「T003 未完成」段落是前次查核歷史，目前 T003 技術相依已解除。

#19 的 module 責任現為：`notes/export_context.py` 集中原活動權限、批次原堂勝組、教師投影；`export_service` 在來源前與保存前校驗；`writeback` 在新操作／恢復前與每批 `_snapshot` 校驗；routes／模板只作接線，group_label／時間核心保持相依實作。#20 的未完成人工／POSIX紀錄仍依其原驗證文件，不因合流代勾。
