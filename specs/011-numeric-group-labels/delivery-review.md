# Issue #16 交付檢核

2026-11-27（台北時間），Codex 依 speckit-converge 核對本功能的 spec、plan、tasks 與憲章；人工驗收由本對話使用者執行及回報。產品版本為 `e4c3b00f427ac9f8306c1a1145c68e21d655473c`，本次僅補測試與交付文件。

## Converge

檢查 3 項 FR、2 項 SC、3 個使用者情境、15 個原任務、4 項計畫決策（技術棧、輸入驗證、固定識別與讀取投影、原課堂回填映射）及憲章 I–VI 的適用要求。未設定 extensions.yml，無前後置 hooks。

| ID | 類型 | 嚴重度 | 來源 | 證據與處理 |
| --- | --- | --- | --- | --- |
| F1 | partial | MEDIUM | FR-011-02、FR-011-03、T009 | 原整合測試已驗證單堂回填標籤，但缺少不同課堂同號組別的預覽／報告直接對照。Converge 僅追加 T016，再於交付補正階段實作並驗證。 |

第一次發現統計：missing 0、partial 1、contradicts 0、unrequested 0；MEDIUM 1，其餘 0。T016 完成後再次核對：0 個剩餘可執行缺口，implementation satisfies the spec, plan, and tasks；第二次 Converge 不新增任務。

## 要求與證據

| 來源 | 實作／驗證 |
| --- | --- |
| FR-011-01、SC-011-01 | classroom_membership.group_number、classroom_routes.enroll、student-entry.js；test_classroom_memberships.py 與 student-entry-009.test.cjs 驗證拒絕、原資格、欄位與修正。 |
| FR-011-02、SC-011-02 | group_label、classroom state、workspace roster、results_gateway；test_classroom_results.py、test_workspace_routes.py 及 test_classroom_notes_integration.py 覆蓋顯示與回填。 |
| FR-011-03 | 無 schema 遷移或 ID 改寫；原順位、結算、課堂關閉、歷史與授權回歸通過。新增同號跨堂案例核對兩個不同 winner_group_id、各自預覽與報告，以及關閉原堂後的教師歷史。 |
| T002 相依契約 | 已提交 contracts/group-number.md 為 #17 的交接依據。tasks 提及的 specs/012-tab-classroom-membership/spec.md 屬作者本機規劃，未包含在本 PR；不將其視為已交付文件或 #17 已實作證據。 |
| T009 測試位置 | 原回填顯示整合證據實際位於 tests/integration/test_classroom_notes_integration.py；T016 在同檔補齊跨堂案例。原 export_previews/export_routes 測試仍由完整回歸涵蓋。 |

## 自動與人工結果

- Codex 在獨立 PR 副本對產品版本執行完整 Python：507 passed、98 subtests passed；Node：74 passed，兩者退出碼 0。
- T016 補測後執行 `python -m pytest tests/integration/test_classroom_notes_integration.py -q -p no:cacheprovider`：3 passed，退出碼 0。測試使用暫存 DB 與 WritableSheets，沒有真實 Google 寫入。
- 使用者依本對話的 11 項案例回報「測試皆已完成」。案例與預期／結果見 validation.md。這是使用者回報，非 Codex 親自操作或獨立讀取真實 Sheets 的證據。
- 多分頁無法同時保留不同課堂資格，經使用者確認留在 Issue #17；不擴張 Issue #16 範圍。
- 三類 PlantUML 原始檔及 PNG 已核對，無結構或時序差異，毋須重繪；詳見 diagram-review.md。

程式審查未發現待修缺陷，驗收與交付紀錄齊備，允許將 PR #22 轉為 ready、核准及合併。GitHub 最終審查與合併事件以 PR 頁面紀錄為準。
