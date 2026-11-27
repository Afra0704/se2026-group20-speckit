# 教師顯示投影契約

投影只加在教師 preview／report DTO 外層，原 v1 snapshot、result_version、items 身分與既有欄位保持相容。實作命名可依相依功能調整，調整時同步本契約。

## activity_context

| 欄位 | 型別／語意 |
| --- | --- |
| activity_id / activity_title | 字串；原活動 ID／名稱 |
| result_url | 伺服器以原課程／課堂／活動產生的只讀結果選取 URL，見 HTTP 返回契約；獨立活動為 null 並提供一般教師頁連結 |
| course_id / course_title | 字串；原課程 |
| classroom_id / classroom_title | 字串；原課堂；獨立活動為 null 並顯示「非課堂活動」 |
| classroom_state | OPEN／CLOSED；不是教師歷史讀取的阻擋條件 |
| created_at / started_at / closed_at | 原活動欄位，依 #20 傳輸契約；不冒充結算時間 |
| times | 各事件經 #20 helper 產生的安全顯示投影；不用格式化字串排序 |
| result_version | 原快照版本；不產生新的版本 |
| import_id / import_version | 原活動固定講義；版本以整數顯示 |
| lecture_title / source_title / sheet_id | 系統講義名稱、來源分頁名稱與識別；名稱不參與來源格位對應 |

沒有原事件值時不補造；若未保存獨立結算時間，僅顯示「結算時間未記錄」或省略該時間欄，仍保留結算版本。

## 勝組欄位

preview.items[] 與 report.units[] 各增加 `winner_group_label: string|null`；有效例為「第 1 組」、「第 42 組」。`winner_group_id` 原欄位保留，僅作相容／診斷，不當一般表格組名。

`no_winner`／原 null ID：label=null，表格顯示「無勝組／略過」。非空 ID 查無／跨堂：label=null 並有 `context_error={code:"RESULT_INVALID",reason:"WINNER_GROUP_SCOPE_MISMATCH",message:...}`；不得把此情境顯示為無勝組。新建立／寫入直接拒絕，既有歷史讀取保留報告。

## 顯示順序

1. 課程 → 課堂 → 活動；活動真實時間附 #20 時區說明。
2. 講義名稱、版本與來源分頁；預覽建立／報告更新各自標示。
3. 題號、小題、勝組標籤、原值／建議值或回讀狀態。
4. 原活動結果返回連結、原預覽／報告接續；原課堂即使已關閉也使用原識別。
5. 內部活動／版本／組別／操作識別可置診斷 details。所有文字使用 Jinja escaping 或 DOM textContent，不用 innerHTML 插入名稱／答案。
