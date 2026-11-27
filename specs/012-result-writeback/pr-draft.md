# Issue #19：從活動結果預覽回填並保留原課堂脈絡

## 變更與目的

教師從目前／歷史活動結果直接建立指定活動的回填預覽，不必抄活動識別。預覽、報告與返回結果保留原活動／講義版本，顯示原課程、課堂、活動及原堂「第 N 組」。缺失／跨堂勝組明確報錯並阻止新增寫入，既有報告保留。

沿用原覆寫、冪等、來源租約及先回讀恢復；全無勝組 UI 顯示略過且不提供確認。時間沿用 #20 的共用 presenter，台北至分鐘。沒有更動結果快照、順位、勝組、版本或新增 schema。

## 關聯 Issue 與需求

Refs #19；FR-001–013、SC-001–006。C1-A–C 依本聊天室使用者「已雙組確認」回報，確認者姓名／外部紀錄未提供。不先寫 Closes，真人驗收仍待完成。

## 文件與圖表

specs/012-result-writeback 的 spec／plan／tasks／contracts／quickstart／validation，以及 diagrams/012-{component,class,sequence}.puml／PNG。實作對圖見 diagram-review.md，未完成證據見 convergence.md。

## 自動驗證

- `.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -q --tb=short`：607 passed、98 subtests passed、1 skipped（Windows 無 POSIX tzset）。
- `node --test` tests/*.test.cjs 的實際檔案陣列：82 passed。
- 後續追加同名活動／重用同講義版本 1／2 的整合案例：1 passed；此為完整回歸後額外案例，不將其混稱完整回歸 608 項。
- 三圖 CLI 退出碼 0，已逐圖視覺核對；文件及 staged diff 格式檢查。

## 人工驗收

未執行本輪教師加兩組／第二教師驗收、兩份真 Sheets 副本格值與格式核對。T043／T044、T047–T049 保持未完成。受控替代來源不代替真 Google 證據。

## 已知限制與共同需求變更

本機基底整合 #16 PR22（80510a6）及 #20 本機提交 4199675（核心 aecb22e、接線 772af09）。發 PR 前應先同步 #20 的正式合流狀態，避免把其未發布功能誤稱為已在 master；#20 自身未完成的人工／POSIX任務不由本輪代勾。沒有 push、發 PR 或對外留言。

## 請審查者確認

- [ ] 實作與原活動／課堂／版本關聯正確，圖表與程式一致。
- [ ] 真人及真 Sheets 證據完成，失敗修正有重驗。
- [ ] #16／#20 相依與 C1-A–C 共同規則對照正確。
- [ ] 提交及附件不含憑證或真實學生資料。

## 2026-11-27 正式整合交付更新

本檔前文為#19分段草稿。#19與#20已整合並完成真人／真來源及Linux跨時區證據；正式PR內容改用[整合PR草稿](../../docs/issues-19-20-pr.md)，交付檢核見docs/issues-19-20-delivery-review.md。原未完成紀錄作為歷史保留，僅組員本輪技術互審依實際PR回覆補記。
