# 實作計畫：改善人工驗收體驗

分支 `codex/010-acceptance-experience`。基底 `edb42c3`（PR #11，含 `ea5efbb`）。依據 [規格](spec.md) 與 [九張已渲染圖表](diagram-review.md)。

## 摘要與技術背景

沿用 Python 3.13、Flask、SQLite、Jinja 與原生 JavaScript。A 與 C 可獨立實作及驗收。B 已由使用者回報雙組確認；實作採頁面心跳與伺服器逾時。

## 憲章檢核

- I、IV：A 保留既有 Sheets 驗證，C 保留 D06、003-D22 的 OPEN 歷史及 009-D22 的 CLOSED 禁讀。B 的身分、計數與時限已由使用者回報確認，後端授權與資料隔離列入驗收。
- II：初版圖意已由組員審查；使用者確認 PR #11 後，本輪依 009 更新 B／C 圖，B／C 的更新處已由組員複核。實作後逐項核對程式、契約與圖表，若釐清改變圖意便重新渲染並請組員複核。
- III：沿用既有匯入、結算及回填，驗收須覆蓋有效 Sheets 連結完整流程。
- V、VI：先由 Tasks 與 Analyze 定義驗收及檢查一致性，實作後執行 Converge，記錄自動與人工證據。

## 專案結構與圖表對應

| 圖表 | 程式落點 | 行為 |
| --- | --- | --- |
| A 匯入 | `templates/workspace/lectures.html`、`static/import-flow.js`、`static/workspace.js`、`workspace.css` | 將原生 invalid 與 INVALID_SHEETS_URL 引導至同一欄位提示。沿用後端來源驗證，依實際錯誤碼分開處理權限及讀取失敗。 |
| C 結果 | `templates/activities/student_room.html`、`static/student-room.js`、`static/student-classroom.css`；教師 `templates/workspace/classroom.html`、`static/classroom.js`、`static/workspace.css` | OPEN 時依活動階段驅動學生結果區。使用固定課堂 ID、世代、活動 ID 與結果選取識別隔離請求；結果請求與關課狀態輪詢分開。CLOSED 走 009 終止流程。教師維持作答進度、歷史與回填，兩端沿用正式結果入口。 |
| B 在線 | `activities/classroom_membership.py`、課堂路由及 schema、`workspace/routes.py`、學生 `static/student-room.js`、教師 `static/classroom.js` | 依固定內部課堂 ID 授權，按穩定參與身分與頁心跳彙整；CLOSED 停止更新。以附加式 schema 保留既有資料。 |

先交付 A，再交付 C。A 的人工驗收使用一份可用 Sheets 副本；整體交付另核對憲章 III 的兩份講義匯入與回填證據，缺證據時補做。B 的共同需求、契約與驗收時間依確認回報同步。產物包含 [研究](research.md)、[資料模型](data-model.md)、[介面契約](contracts/acceptance-interfaces.md) 及 [驗收指南](quickstart.md)。
