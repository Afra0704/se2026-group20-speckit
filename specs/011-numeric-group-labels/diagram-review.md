# 圖表渲染紀錄

2026-11-27（台北時間），基底 e9a29c7。使用 PlantUML CLI，以 JDK 21 執行如下，退出碼 0，核對三張 PNG 簽章：

    java -Djava.awt.headless=true -jar plantuml-speckit-003.jar -charset UTF-8 -failfast2 -tpng ./diagrams/011-*.puml

[組件圖](../../diagrams/011-component.png) · [類別圖](../../diagrams/011-class.png) · [時序圖](../../diagrams/011-sequence.png)

2026-11-27，使用者回報組員已完成首版圖意審查。審查者姓名與外部紀錄連結未提供。若釐清改變圖意，須重繪並複核。

## 實作對照

- 組件圖的加入欄位、組號驗證與映射，分別對應 `student-entry.js`、`classroom_routes.enroll`、`classroom_membership.group_number` 與 `group_label`。
- 類別圖的固定課堂／組別 ID 沿用既有資料關係。結果與回填呈現使用讀取投影；快照、答案、順位、勝組 ID 與作業識別保留。
- 時序圖的有效路徑在伺服器驗證後建立資格；無效路徑在寫入前回傳欄位錯誤，由原頁保留輸入。原圖組件、關係與時序仍適用。

## 2026-11-27 交付複核

Codex 對產品版本 e4c3b00 檢查三份 puml 並開啟三張既有 PNG 核對：

- Component：加入欄位與前端檢查對應 student-entry.js；後端驗證在 enroll 呼叫 group_number；師生結果、在線與 notes 回填共同使用 group_label。
- Class：classroom_groups 保留固定 classroom_id／group_id，同堂組號查找與顯示標籤分開，沒有資料遷移或識別改寫。
- Sequence：先驗證輸入，無效於寫入前拒絕；有效才建立 membership／grant。錯誤原值保留於前端，後端不替換原資格。

未發現須改圖的責任、關係或分支差異，既有 PNG 可讀且與 puml 一致，因此本次不重繪。新增 T016 僅補跨堂回填測試，不改圖意或產品程式。真人驗收已由使用者回報完成；程式 review、自動驗證與 Converge 結果見 delivery-review.md。
