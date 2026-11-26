# 003 圖表渲染與審查紀錄

**日期**：2026-11-26（Asia/Taipei）

**執行者**：Codex

**基底**：`39d6275e0b3f005957764327c16c443d7a60825e`

**分支**：`codex/003-quiz-results`

## 初版 CLI 渲染

從 repository 根目錄使用 PlantUML 1.2026.10。JAR 位於本機暫存目錄。

```powershell
$jar = 'C:/Users/User/AppData/Local/Temp/plantuml-speckit-003.jar'
java.exe '-Djava.awt.headless=true' -jar $jar -charset UTF-8 -failfast2 -tpng './diagrams/003-*.puml'
```

實際命令退出碼 0。每張 PNG 均檢查簽章、尺寸、區塊 CRC 和同名來源。

| 圖 | 渲染檔 | 尺寸 |
| --- | --- | --- |
| Component | [003-component.png](../../diagrams/003-component.png) | 1537 × 754 |
| Class | [003-class.png](../../diagrams/003-class.png) | 605 × 1023 |
| Sequence | [003-sequence.png](../../diagrams/003-sequence.png) | 1128 × 1340 |

## 初版圖意核對

- Component 對照既有活動授權、固定題目、003 的提交與結果入口，以及 001 回填交接。
- Class 表達活動固定版本、一次題組提交的完整小題，以及每個活動至多一份已結算快照。D01 的同組提交基數留待確認。
- Sequence 覆蓋準備中、教師進度、截止兩種順序、結算等待、結果投影與 001 回填。D01、D02 排序細節和 D08 均保留待確認。
- 分工介面待 Plan 核對，包括 `ACCEPT_SUBMISSION`、`GET_PROGRESS`、`GET_SETTLED_RESULTS`、`get_ended_snapshot` 及既有的 `validate_snapshot`。組員圖意審查仍待實際執行與具名記錄。

## 2026-11-26 Clarify 重繪

沿用上方 PlantUML 1.2026.10 指令，退出碼 0。三張 PNG 均重新檢查簽章、區塊 CRC、尺寸，並核對 PNG 更新時間不早於來源。

| 圖 | 尺寸 | 校對的改動 |
| --- | --- | --- |
| Component | 1767 × 754 | 受理保存、有效答案換新與結算責任 |
| Class | 657 × 1040 | 同組同題維持一筆有效提交、唯一受理順序 |
| Sequence | 1219 × 1520 | 重送成功才取代，截止先發生則保留原提交，依有效順序選勝組 |

此版本的網路重試行為當時尚待釐清，後續見下節。

## 2026-11-26 D01 網路重試補充

沿用 PlantUML 1.2026.10 指令，退出碼 0。Component 加入讀取原受理結果的責任，Class 補上同一次送答的識別，Sequence 補上回應遺失後重試的分支。

三張圖重新通過 PNG 簽章、區塊 CRC 和時間檢查。Component 為 1712 × 770，Class 為 657 × 1067，Sequence 為 1219 × 1651。使用者已採用網路重試方案，雙組確認和組員圖意審查仍待補。

## 2026-11-26 雙組確認與組員審查

`@itsusername15` 在本次對話回報 SpecKit／OpenSpec 已確認 D01、D02 排序與 D08，組員已審查 Component、Class、Sequence。組員姓名與外部紀錄連結未提供。收到回報後只更新圖名及確認狀態文字，保留原圖的責任、資料關係與互動。

沿用上方 PlantUML 1.2026.10 指令，退出碼 0。三張 PNG 均驗證簽章、區塊 CRC 及更新時間。Component 為 1712 × 770，Class 為 657 × 1058，Sequence 為 1219 × 1651。

## Analyze 修訂：重新整理與歷史清單驗證

時序圖補上同一分頁重整後的手動重試，以及依原歷史清單驗證快照。沿用 Plan 的 PlantUML 1.2026.10 指令，輸入改為 `./diagrams/003-sequence.puml`，退出碼 0。新版 Sequence PNG 為 1240 × 1704，簽章、區塊 CRC 及更新時間檢查通過。

## Analyze C1 修訂：開放中課堂的歷史查閱（D22）

Sequence 區分開放中課堂的有效同堂組別資格（含新加入）與關課後的原瀏覽器證明。沿用 PlantUML 1.2026.10 指令渲染 `./diagrams/003-sequence.puml`，退出碼 0。PNG 為 1266 × 1861，簽章、區塊 CRC 及更新時間檢查通過。這個新增分支待雙組確認及組員圖意複核。

2026-11-26，`@itsusername15` 於本次對話回報雙組已確認 D22，組員已複核新增的時序分支。個別確認者姓名及外部紀錄連結未提供。將圖上的待確認標示更新後，以同一指令重繪，退出碼 0，PNG 為 1266 × 1861。簽章、區塊 CRC 與更新時間檢查通過。

## 2026-11-26 實作對圖

| 圖 | 實作位置與核對 |
| --- | --- |
| Component | `activities/submission_context.py` 提供既有學生資格與固定問題。 `quiz/submission_gateway.py`、`results_gateway.py` 與 `settlement.py` 實作受理、結果投影、結算及 001 快照交接。001 延續既有 Google Sheets 寫入與讀回責任。 |
| Class | `quiz/schema.sql` 保存受理及同組同題有效指標，每活動至多一筆結算。固定題目與小題仍由 `activities/teacher.py` 在建活動時寫入。 |
| Sequence | 受理及教師關閉共用 SQLite 寫入交易，確立兩種截止先後。原操作重試由前端和受理閘道處理。CLOSED 同交易保存待辦，結算在 commit 後獨立發布並可恢復。師生投影、D22 開放中歷史與歷史清單驗證已對應實作。 |

三圖的責任、資料關係與行為分支相符，本次實作對圖未改圖。目前的圖意核對是實作技術檢查，分支 PR 另由組員互審。

2026-11-26，009整合補充：原PR9互審與上述紀錄保留。本輪由Codex修改003 Sequence的關課學生分支，採009-D22拒絕恢復／內容，003-D22僅指OPEN晚加入結果；補預檢驗權、外部結算重試及最終重新驗權。沿用Java CLI全24圖成功exit0，已開圖核對分支及文字，無錯誤頁；詳見[009對圖](../009-release-classroom-codes/diagram-review.md)。新技術圖不宣稱已經同學人工複核。
