# 教師時間 metadata 與 #19 接線

## 既有活動清單

`GET /teacher/classrooms/{classroom_id}/activities` 仍先執行原教師及 owned_classroom 驗權，回原 `activities` 清單。原 activity_id、phase、import_id、import_version、title、created_at、started_at、closed_at 原樣保留；清單順序不變。

每一列新增教師專用 `time_display`：

```json
{
  "version": 1,
  "timezone": "Asia/Taipei",
  "utc_offset": "+08:00",
  "created_at": {"label": "建立", "status": "known", "text": "2026-11-27 11:00", "instant_utc": "2026-11-27T03:00:00+00:00"},
  "started_at": {"label": "開始", "status": "skipped_start", "text": "未開始即結束", "instant_utc": null},
  "closed_at": {"label": "結束", "status": "known", "text": "2026-11-27 11:04", "instant_utc": "2026-11-27T03:04:05+00:00"}
}
```

這是 raw 值以外的新顯示欄位，不以 formatted 字串取代原值。adapter 可在既有 SELECT 讀取 `a.phase_version` 作內部直接結束證據；不修改資料、不要求公開該 counter。來源／狀態規則見 [data-model](../data-model.md)。

前端 `classroom.js` 在既有 `activityList` 以 textContent 分別呈現三種事件，仍維持選取、晚到回應保護與按鈕。遇到缺少／未知 version 的 metadata 時顯示「時間資料尚未提供」，不可退回把無時區 raw 當本地時間；保留其餘活動內容與操作。前後端靜態資源應同版本載入，舊快取需重新載入。

## notes 畫面

匯入確認、export_form、export_preview、report 使用共用 presenter。依已驗權的原 row/report 建立 HTML view model：confirmed_at、preview_created_at、operation_updated_at、verified_at；不把內部 row／來源診斷直接交給學生。

本輪 notes JSON responses 不新增時間欄位：`export_preview_data`、writeback.get_report 及其重試契約保持。需要顯示的安全值只供原教師 HTML，`notes_time` 作相容橋接。未來 #19 可在自己的私有脈絡 envelope 加入同一 DisplayTime，但不得混入 CatalogDTO／snapshot／勝組答案／idempotency payload。

## 給 #19／012 的責任分界

- #20／011 主責 `time_display.py` 的解析／文字政策、`time_views.py` 的來源與活動生命週期映射、既有教師歷史及 notes 時間顯示修補。
- #19／012 主責脈絡查詢、教師結果直達回填、名稱及組別映射；從已驗權資料呼叫共用 presenter，不另建 timezone formatter。
- 欄位互對：活動 created_at／started_at／closed_at；原 preview.created_at；原 report.updated_at；item.verified_at。無 settled_at 時不增加假時刻。
- 雙方都可能修改 notes/routes.py、notes 模板與 classroom.js；實作前約定函式區塊或先合併011 presenter，再接012。原012檔案本輪未修改，介面屬設計提案，未冒稱另一對話已確認。
- #16／#17 不需等待時間修正；其資格、組別、presence 或期限欄位不交由本 presenter 改寫。本輪不擴充學生結果欄位。

## 不變條件與權限

不新增匿名時間查詢或可指定他人活動的入口。原AUTH_REQUIRED／FORBIDDEN／COURSE_NOT_FOUND與學生關課規則保持。所有 DisplayTime 為導覽／呈現資料，不作排名、截止、資格、lease或恢復操作的依據。讀取／重新整理不觸發 Sheets、重新授權或結算重建。

## 2026-11-27 最新呈現政策

使用者回報 OpenSpec 已確認時間呈現規則；畫面 text 統一為台北 `YYYY-MM-DD HH:mm`，只截取、不進位。instant_utc、原始欄位與解析所需秒／小數秒保留原精度。確認者姓名及獨立紀錄未提供；#19／012 介面及檔案責任核對仍依 T002，不能由時間政策確認推定接線也已確認。

## 2026-11-27 實作介面與分工確認

來源：本對話使用者回覆同意011先完成時間接線、012後續沿用。原先待約定文字為計畫時狀態，不代表仍須重問。

- `guided_notes.time_display.present_time(raw_value, *, event_kind, source_policy="unverified", occurrence="unknown") -> DisplayTime`，精確原instant_utc與到分鐘text分離。
- `guided_notes.time_views.activity_time_display(row, *, trusted_lifecycle=False) -> dict`；原history驗權後傳dict(row)，本程式可追溯的活動writer以trusted_lifecycle=True，phase_version只供內部並移除後回應。
- `notes_time(value, *, event_kind="operation_updated") -> DisplayTime`；`readback_time(verification_status, value) -> ReadbackTimeView`。兩者只格式化已驗權HTML資料，不查Google／DB。
- notes blueprint context提供event_time、readback_time、time_zone_notice；原notes_time Jinja filter保留安全字串結果。012後續在自己外層context取用同helper，不在嚴格snapshot／CatalogDTO加欄位。
- 011本次修改classroom.js的activityList文字、notes/routes.py格式化橋接及四張模板的時間區塊；保留master的第N組映射，未改012名稱／回填入口文件。012合流時應對照這些函式區塊，不能整檔覆蓋。
