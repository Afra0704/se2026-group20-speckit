# 007 實作後一致性分析與 Convergence 紀錄

日期：2026-11-25（Asia/Taipei）；Codex。T059 先執行唯讀 speckit-analyze，再依 speckit-converge 只追加任務；本報告由 implement 寫入作為紀錄。沒有在 analyze 中修程式或將人工工作代勾。

## Specification Analysis Report

規格／計畫／任務／契約／三圖未發現新增的阻擋實作矛盾。資料模型已同步終態清秘密，原計畫的 notes/index.html 更正為實際 import.html；內部抽象名稱與實作名已註明。005/006 狀態保留，D20 不推定雙組已確認。

| ID | 類別 | 等級 | 位置 | 結論／後續 |
| --- | --- | --- | --- | --- |
| M1 | 交付驗證缺口 | HIGH | tasks T056–T058、FR-014、SC-001/002/007 | 自動與受控測試完成，真實 Google／兩教師／兩學生組尚無證據；保留未完成，追加 T062。 |
| M2 | 協作證據缺口 | MEDIUM | tasks T060、D20、plan 介面核對 | 本輪具名互審、分工與 OpenSpec 同步未回報；追加 T063，不能聲稱具備合併核准。 |

以上為已明列的交付前置，沒有把「缺少人工紀錄」改寫為功能已通過；使用者本次授權足以進行本輪實作，未冒充對方組別或同學確認。

## Coverage Summary

| 需求 | 任務 | 主要證據 |
| --- | --- | --- |
| FR-001 | T013–T019 | Google auth routes、identity UI、原學生加入。 |
| FR-002 | T016/T018/T021/T025–T029 | 匿名 303／API 401、Google 正式入口。 |
| FR-003/004 | T020/T022–T027/T031–T034 | 官方驗簽、同 sub 並行唯一、同信箱不同 sub。 |
| FR-005 | T026/T033/T048/T050 | Google-mode A/B 課程、講義、活動、回填越權拒絕。 |
| FR-006 | T009/T010/T020–T028/T031/T032/T038 | state/browser/claim/TTL/epoch、失敗回滾、重放。 |
| FR-007/008 | T035/T038/T040/T041/T047 | 舊 cookie、登出／切換、學生真實 membership 保留。 |
| FR-009 | T004–T009/T020/T028/T037/T039/T043–T045/T049 | 加密、日誌／cookie 白名單、傳輸快照。 |
| FR-010 | T036–T051 | 雙 purpose、同 sub、scope、leased refresh、無 fallback。 |
| FR-011 | T001/T004–T007/T023/T039/T050 | 新空白 007 DB、舊 DB guard、instance 搬移拒絕。 |
| FR-012 | T012/T023/T029/T030 | 正式密碼 410、CLI 不詢問密碼、測試明確模式。 |
| FR-013 | T017–T019/T033/T045–T048/T052/T055 | 原 005/006、RAW 回讀／恢復與固定 DTO 全回歸。 |
| FR-014 | T005/T013/T014/T020–T022/T028/T031–T038/T047–T060/T062/T063 | 自動證據完整；真人與互審未完成。 |

- 功能需求 14、成功準則 7、故事驗收情境 14；原任務 61，追加後 63，需求有任務覆蓋 100%（不是驗收完成率）。
- 新增歧義 0、重複需求 0、無對應需求任務 0、阻擋實作的 CRITICAL 矛盾 0。
- 憲章六原則已檢查：圖 CLI 與實作對照、動態匯入／回填與機敏／角色檢查有自動證據；人工與協作原則尚有明列交付缺口，不宣稱整體完成。

## Convergence Findings

核對範圍：FR-001–014、SC-001–007、14 個 AC、plan 八項主要資料流決策及六項憲章原則。不是 Git diff／歷史比較；依目前程式與測試實際行為判斷，checkbox 不是唯一依據。

| ID | gap-type | 等級 | source-ref | 證據與剩餘工作 |
| --- | --- | --- | --- | --- |
| F1 | partial | HIGH | FR-014/SC-001/002/007、憲章 V、T056–058 | 合成端不能替代 Google Cloud、兩位真實教師及教師加兩組學生；T062 聚合追蹤。 |
| F2 | partial | MEDIUM | plan 介面核對、D20、憲章 I/II/VI、T060 | 本輪同學與 OpenSpec 記錄缺少；T063 追蹤。 |

missing=0、partial=2、contradicts=0、unrequested=0；HIGH=1、MEDIUM=1。未發現新增自動可修的產品缺口。

**結果：tasks_appended**，只在 tasks.md 尾部追加 Phase 7、T062/T063，未重排既有任務。未宣稱 converged，尚不能直接視為可合併。後續由真人完成對應操作／互審並補證據，再核對；不必重跑已通過測試，除非內容變更或有失敗。

前後 hooks：.specify/extensions.yml 不存在，無需執行。
