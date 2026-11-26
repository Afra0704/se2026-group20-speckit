# 003 合併前 Analyze／Converge

**日期** 2026-11-26（Asia/Taipei） · **執行者** Codex · **審查版本** `ce2a470`（PR #9）。

## Analyze

唯讀核對 `spec.md`、`plan.md`、`tasks.md`、003 契約及憲章 I–VI。11 項 FR 與 4 項 SC 全數有對應任務，41 項原任務編號連續。C1 已按 D22 明定開放中課堂與關課後的歷史查閱資格；I1 的 v1 版本與固定歷史清單已對齊 001；A1 的同分頁重整與回覆競態均有回歸案例。沒有發現新增的文件契約互斥或無對應任務的需求。

## Converge 結果

| ID | 類型／等級 | 需求 | 實際證據與後續 |
| --- | --- | --- | --- |
| F1 | partial／HIGH | US2/AC3、FR-008、T022 | 以暫存 DB 建立準備中、有相容 001 清單的活動。課堂入口直接結束回 200，結果為 settled 且每題無勝組；非課堂入口回 409 `INVALID_PHASE`，仍顯示 active。相容路由 `activities/teacher_routes.py` 限 LIVE，相容教師前端 `static/activity-sync.js` 也在 PREPARING 停用結束按鈕。已追加 T042。 |

檢查 15 項需求與驗收準則、3 個設計階段及 6 條憲章原則。新增實作缺口為 partial 1 項，HIGH 1 項；missing、contradicts、unrequested 各 0 項。結果為 `tasks_appended`。已存在的人工／外部驗收保持列在 T035（真實 Sheets）、T037（真人與計時）及 T041（PR 複審），沿用原任務追蹤。

本輪核對的自動證據來自同一提交，427 Python、98 子測試與 31 Node 測試均通過。F1 是額外覆核發現的情境。T040 保留未勾，待 T042 修正並重驗後複查。

## T042 修正複核

相容入口現可在 PREPARING 或 LIVE 關閉，沿用原教師擁有權核對、CLOSED 與結算待辦的同一寫入交易。新增回歸確認準備中關閉會發布逐題無勝組結果、其他教師無權關閉、已結束活動拒絕重開與重複關閉。相容頁面在 PREPARING 與 LIVE 開放結束按鈕，結束後停用。F1 已在本機修正並通過針對性重驗；T035、T037、T041 的真實驗收及組員複審仍待完成。

完整回歸為 428 個 Python 測試、98 個子測試、31 個 Node 測試全數通過。F1 重驗後結案，T040 與 T042 標記完成。人工驗收及 PR 複審仍由原任務追蹤。
