# 012 學生分頁課堂資格實作計畫

分支 `codex/012-tab-classroom-membership`，開發基底為合併 PR #22 後的 `80510a6`。來源 [規格](spec.md)、[組件／類別／時序圖](diagram-review.md)。

## Summary

以分頁資格取代現行學生的共用課堂 grant。保留 003 正式受理、009 固定課堂與關課限制、010 在線去重。學生端維持同一瀏覽器跨堂並存，同堂只啟用一組。

## Technical Context

沿用 Python 3.13、Flask、SQLite、Jinja 與原生 JavaScript。使用既有 CSRF、SQLite 寫入交易及伺服器時間。依 010 保留每秒心跳、4 秒在線判定及 5 秒端到端驗收目標。沿用現有恢復最長 7 日及 grant 最長 8 小時作為上限，寫入端仍須逐次驗證原堂及目前組別世代。

## Constitution Check

- 兩組已確認分頁與組別行為，組員已複核新版圖。設計中的操作名稱和資料欄位為技術方案。
- 保留角色授權、教師回填、結果截止、既有識別和不破壞資料的可重跑升級。
- 使用測試庫、測試講義副本、至少一位教師與兩組學生。實作後補 Analyze、Converge、圖表比對及人工證據。

## Project Structure

- **組件圖**。現有 `student-entry.js` 處理加入及欄位提示；`student-room.js` 管理分頁啟用、恢復、結束和重新加入。伺服器以 `classroom_membership.py`、`classroom_routes.py` 的集中授權驗證狀態、歷史、正式送答、結果與在線。
- **類別圖**。現有 classroom/group、membership 和結果資料保留；用附加表保存瀏覽器同堂組別世代及分頁資格。將分頁資格與 010 liveness 分開持久化。
- **時序圖**。加入時先於單一交易建立可見的在線保留，再回傳資格。複製或恢復在顯示內容前取得本頁獨立資格。重新加入只撤回本頁，丟棄失效世代回應。關課與角色授權由後端判斷。
- **送答與回歸**。與 #18 對齊 `quiz-submission.js` 的未決操作命名與清理責任。沿用 003 結算與 idempotency；驗證房間與組別後才查重送，避免舊資格利用重送入口。教師與既有獨立活動走原授權路徑。

先做資料表、原子加入與錯堂拒絕，再作分頁恢復，最後接重新加入及完整回歸。#16 的組號契約取自 PR #22；開工前核對合併提交，可先以其契約準備測試。見 [研究](research.md)、[資料模型](data-model.md)、[介面契約](contracts/tab-membership.md) 與 [驗收指南](quickstart.md)。
