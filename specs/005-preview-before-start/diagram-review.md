# 005 圖表渲染與圖意審查

日期：2026-11-25。狀態：三圖已渲染；使用者回報同學圖意審查與 OpenSpec 確認完成，姓名與獨立紀錄待補。

## 產物與 CLI 結果

- 組件圖：[來源](../../diagrams/005-component.puml)、[PNG](../../diagrams/005-component.png)。
- 類別圖：[來源](../../diagrams/005-class.puml)、[PNG](../../diagrams/005-class.png)。
- 時序圖：[來源](../../diagrams/005-sequence.puml)、[PNG](../../diagrams/005-sequence.png)。

實際執行以下 PowerShell 指令，結束碼為 0，三張 PNG 均已產生。

```powershell
& 'C:\Program Files\Java\jdk-24\bin\java.exe' '-Djava.awt.headless=true' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar -charset UTF-8 -tpng 'D:/os_final/diagrams/005-*.puml'
```

## 審查重點與進入計畫的條件

- 三圖共同表達：準備階段顯示題號及作答欄、停用作答；教師開始後才允許提交；結束後拒絕提交。對應 FR-001–FR-007。
- 建立失敗保留原顯示，對應 FR-009。圖為概念責任，不預先指定程式類別或檔案。
- Q1 已確認：一次只能一個未結束活動。使用者澄清為大家已同意的行為補強，不是新提案；先前「人工圖意審查仍未執行」為舊狀態，現依使用者回報已確認。
- 使用者回報 D18 與三圖確認完成，據此進入 plan。此處不捏造逐圖評語；plan 中準備活動也可結束，對應現有圖中的「結束活動」。
- 本紀錄不代表 UI、提交受理、正式順位或人工端到端驗收已通過。

## 本次文件補正

2026-11-25，依使用者指示移除舊開發資料相容設計，採空白 DB 驗收。時序圖補上準備中直接結束分支，類別圖註明新資料不變量與開發資料範圍。此為既有確認規則的展開，不捏造本次重畫後另有人工審查；後續程式與圖的核對由 T031 追蹤。

本次以相同 CLI 指令重渲染三圖，退出碼 0，三張 PNG 已更新；未修改應用程式或刪除 DB。

## Implement 後一致性核對（2026-11-25）

| 圖中責任／關係／分支 | 程式與證據 |
| --- | --- |
| 課堂管理建立並發布唯一活動 | classroom_routes.create_activity 在 activity_transaction 內寫題目／關聯／目前指標／版本，classroom_access.require_no_unfinished 與 schema trigger 保護單活動。 |
| 活動固定版本、主題及作答項目 | 沿用 store_activity 的不可變 questions；state_view 排除 blank_id，課堂 state 補安全 title，兩組預覽測試核對順序、欄位與安全白名單。 |
| 預覽、明確開始、停用與啟用 | classroom.js showQuestions／refresh，每次更新 input/button；同 id 開放與斷線恢復由 Node 測試覆蓋。 |
| 提前提交拒絕 | 原 submission_context 檢查目前活動／OPEN／LIVE，未改提交契約；provider spy 驗證未開放不受理。 |
| 準備中直接結束／搶答後結束 | change_activity 限目前活動，PREPARING 或 LIVE 可 finish；started_at 空值、CLOSED 重送及歷史保留由測試覆蓋。 |
| 關課與第二次建立拒絕 | close 結束關聯未結束活動；雙連線 barrier 一 201 一 409，rollback 無殘筆。 |

圖意與本次責任、關係及主要互動一致，未新增圖外模組。相同 CLI 再次產生三張 PNG，退出碼 0；不以 AI 核對取代本次程式的人工端到端驗收。
