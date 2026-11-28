# 013 學生送答提示實作計畫

**分支** `codex/013-submission-feedback`
**基底** `a8c7b8f`，包含 #17 的分頁資格
**日期** 2026-11-28（台北時間）
**依據** [規格](spec.md) · [三圖及審查紀錄](diagram-review.md)

## 摘要

在正式學生課堂的每題表單顯示欄位錯誤、操作進度及結果。沿用 #17 的分頁與未決送答作用域，及 003 的受理、冪等與順位交易。既有錯誤碼保留，按回應是否可確認原操作決定呈現和清理。

## 技術環境

- Python 3.13、Flask、Jinja、SQLite、原生 JavaScript，沿用 pytest 與 Node 測試。
- 每題即時呈現本地送出中與錯誤提示。重連或重整不自動送答，也不新增輪詢。
- 未決操作沿用既有 sessionStorage 表示與伺服器驗證的文件交接。無資料表、路由、授權或結果可見範圍變更。
- #15 的樣式尚在獨立 Issue 處理。沿用現有表單的可及性做法，等共用樣式定案再接合。

## 憲章檢查

| 原則 | 設計前與設計後 |
|---|---|
| 雙組協調 | 使用者回報已確認原樣重試及編輯保留規則，見規格及共同需求。 |
| Diagram First | 三類圖已產出 PNG，使用者回報組員審圖完成。下節逐圖落實。 |
| 匯入與回填 | 沿用既有作答欄位與結果，測試用講義含單題及多小題，整合驗證核對原結果。 |
| 權限與機敏 | 先走既有資格及 CSRF。欄位錯誤只可描述本題，不回傳答案、憑證或他組資料。 |
| 驗證及追溯 | 測試包含受理後回覆遺失及早期拒絕，另記錄教師與至少兩組學生的人工驗收。交付前完成 Analyze、Converge 和圖對碼。 |

## 專案結構與圖表對應

- **組件圖**。學生表單由 `src/guided_notes/static/student-room.js` 建立欄位與提示容器，`quiz-submission.js` 負責表單驗空、渲染送答狀態、保存與重試操作。`student-classroom.css` 補欄位錯誤及本題回饋樣式。課堂資格與連線仍由學生頁處理。
- **類別圖**。本題作用域沿用課堂、活動、組別、題目和文件識別。未決操作保存同一 UUID 和原始內容。回饋存於已授權的本頁作用域，參照 [資料模型](data-model.md)。
- **時序圖**。本地驗空後才保存並送出新操作，服務端沿用 `quiz/submission_gateway.py` 驗空與原樣重送。必要時在既有 `INVALID_ITEMS` 回應選擇性附上預期欄位識別。學生端依 [契約](contracts/submission-feedback.md) 處理結果。回覆須同時符合當前畫面、操作與嘗試識別。
- **驗證位置**。`tests/contract/test_quiz_submission.py`、`tests/integration/test_classroom_submission_races_009.py`、`tests/quiz-submission.test.cjs`、`tests/student-room-quiz-009.test.cjs`。以 [驗收指南](quickstart.md) 記錄驗證結果。

先補欄位及錯誤契約測試，再接五種狀態與原樣重試，最後跑 #17、送答結果及教師流程回歸。工作分解由 speckit-tasks 產生。
