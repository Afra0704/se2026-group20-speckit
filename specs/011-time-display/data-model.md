# 011 時間顯示模型（純讀取，不新增表）

本文件是計畫，不代表型別或程式已建立。原 schema、timestamps、授權、snapshot、有效提交、accept_seq 及 result_version 全部保留。

## 1. SourcePolicy

| 值 | 來源 | naive 規則 |
| --- | --- | --- |
| `sqlite_utc` | 已盤點 courses／classrooms／classroom_activities 的 CURRENT_TIMESTAMP 欄位，由 adapter 固定選擇 | 只接受原 SQL 秒級格式並明確附 UTC |
| `offset_required` | notes repository.now() 的確認、預覽、作業、回讀時間 | 不推定缺失 offset，顯示 unknown_timezone |
| `unverified` | 未盤點的外來或舊值；預設政策 | 有明確 offset 可解讀；naive 不猜測 |

政策不由請求 query／body 或瀏覽器提供；是伺服器經核對欄位選用的常數。

## 2. EventTimeInput（內部）

- `raw_value: str | None`：只讀原值；其他型別轉 invalid，不自動轉字串或 epoch。
- `event_kind`：created、started、closed、confirmed、preview_created、operation_updated、readback。
- `source_policy`：上表固定枚舉。
- `occurrence`：occurred、not_started、not_ended、skipped_start、unknown，由既有對象狀態及可信證據決定。
- `scope`：原教師／課堂／活動／回填作業關聯，僅在原驗權後組合；不新建權限系統。

`phase`、`phase_version` 是活動 adapter 的內部輸入，不要求加進原結果 snapshot，也不把 counter 當時間或順位。

## 3. NormalizedObservation（內部暫存值）

- `instant: aware datetime | None`：可確認時保留原微秒；不寫回 DB。
- `status`：known、not_started、not_ended、skipped_start、missing、invalid、unknown_timezone。
- `event_kind`：維持原用途。

判讀順序：驗證輸入型別／長度 → 區分缺值和生命週期 → 有值時驗完整格式 → 明確 offset 或可信舊 UTC → 固定台北呈現。非空壞值優先回 invalid，不以 null／未發生提示掩蓋。存在與生命週期矛盾的值也視為 invalid，不補造事件。

## 4. DisplayTime（HTML／教師 metadata）

| 欄位 | 型別／規則 |
| --- | --- |
| `label` | 固定事件標籤，不接受原值提供 HTML |
| `status` | 上述枚舉 |
| `text` | known 為台北 `YYYY-MM-DD HH:mm`；其他為契約指定中文提示 |
| `instant_utc` | known 時為明確 UTC ISO datetime，保留原精度；其他為 null。不取代原欄位，非排行依據 |

外層 `time_display` 另帶 `version=1`、`timezone=Asia/Taipei`、`utc_offset=+08:00`，詳見契約。無 raw_value、來源診斷、憑證或其他組資訊。

## 5. 活動狀態映射

| 欄位／狀態 | 原值缺失時 | 證據與限制 |
| --- | --- | --- |
| created_at，對象存在 | missing | 不用開始／結束補造 |
| started_at，PREPARING | not_started | 非空開始值卻仍 PREPARING 時為 invalid |
| closed_at，PREPARING／LIVE | not_ended | 非空結束值卻未 CLOSED 時為 invalid |
| started_at，LIVE | missing | 應已發生，缺資料不能說尚未開始 |
| started_at，CLOSED，可信初始化及 phase_version=1 | skipped_start | 缺值才用；有壞值仍 invalid。已知生命週期僅可 PREPARING→CLOSED |
| started_at，CLOSED，但無上述證據／version≥2 | missing | 不能只憑 null 宣稱從未開始 |
| closed_at，CLOSED | missing | 不能說尚未結束 |
| notes confirmed／preview／updated，對象已存在 | missing | 獨立事件，不以活動時間替代 |
| verified_at，格狀態非 verified | 欄位層文字「尚未驗證」 | 使用 ReadbackTimeView，time=null，不新增核心時間解析枚舉 |
| verified_at，格狀態 verified | missing | 驗證成功但缺時間要如實標示 |

沒有獨立結算時間的既有 quiz_settlements 不建立 EventTimeInput，不從其他欄位推導。

`ReadbackTimeView` 為notes HTML的欄位包裝：`verification_status` 保留原逐格狀態、`time: DisplayTime | null`、`text`。原狀態非verified時time=null且text為「尚未驗證」；原狀態為verified時呼叫presenter，缺時間得到missing。此包裝不加入writeback JSON或改變既有狀態。

## 6. 資料保留與排序

不新增表、欄位或遷移；不更動既有 writer／order by。`instant_utc` 只是經原權限授予的顯示 metadata。欄位是唯讀 view，不變成新的排序鍵、截止依據、授權期限或機敏日誌。重跑 app 初始化不因本輪寫入任何事件或重建結果。
