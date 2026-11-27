# 011 數字組別實作計畫

基底 e9a29c7，分支 codex/011-012-student-join。依 [規格](spec.md) 與 [已審首版圖](diagram-review.md)。設計已依雙組確認更新，可進入 Tasks。

## 技術範圍

沿用 Python 3.13、Flask、SQLite、Jinja 與原生 JavaScript。加入入口在 classroom_routes 與 student-entry.js，組別隔離沿用 classroom_membership 的內部課堂與組別 ID。結果、老師進度、在線與回填介面共用顯示規則，保留舊資料、正式結算與回填快照。

## 憲章檢核

組員首版圖意審查已記錄。使用者回報雙組確認新組號規則。使用空白測試庫驗收，舊測試組名的顯示與恢復排除在驗收外。若改變圖意則重繪與複核。

## 接線與驗收

先定加入驗證與欄位錯誤契約供 #17 使用。#19 沿用原課堂映射。見 [資料模型](data-model.md)、[介面契約](contracts/group-number.md) 與 [驗收指南](quickstart.md)。
