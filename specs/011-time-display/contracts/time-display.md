# 時間顯示契約 v1

狀態：2026-11-27 計畫設計；未實作。固定政策由使用者本次 plan 指令指定。2026-11-27 使用者回報 OpenSpec 已確認，並將畫面精度指定為到分鐘；確認者姓名與獨立紀錄未提供。

## 純函式介面與來源政策

預計 `src/guided_notes/time_display.py`：`present_time(raw_value, *, event_kind, source_policy='unverified', occurrence='unknown') -> DisplayTime`。不得讀 DB、request、系統目前時間、主機本地時區、OAuth 或 Sheets；同輸入得到同輸出。另由 adapters 決定事件與來源，不讓不可信參數指定 source_policy。

有效格式：完整日曆日期＋`T`或單一空白＋`HH:mm:ss`，可帶1～6位小數秒；aware 只接受 `Z` 或 `±HH:mm`。可信 sqlite_utc 的 naive 只接受 `YYYY-MM-DD HH:mm:ss`。datetime 解析只在前置格式驗證後使用。不是標準 writer 格式的 week-date、date-only、epoch數字、時區縮寫、閏秒、非法日期、首尾非空空白及超過128字元輸入為 invalid。空值／空字串／純空白按事件缺值規則處理。UTC／台北轉換若溢位也回 invalid，不拋到整頁。

明確 offset 的同一瞬間直接轉換；sqlite_utc 才能為合法 SQL naive 附 UTC；其餘格式合法的 naive 為 unknown_timezone。`replace(tzinfo=UTC)` 僅可用於已證明的 naive UTC，不可覆蓋 aware 的既有偏移。

年份固定四位、其餘數字固定兩位，輸出不能依賴不同平台對小年份的strftime補零差異。最小／最大日期若UTC正規化或台北轉換溢位，回invalid；不夾到邊界日期。

## 狀態文字

| status | text | instant_utc |
| --- | --- | --- |
| known | `YYYY-MM-DD HH:mm` | 帶 UTC offset 的 ISO，原精度保留 |
| not_started | 尚未開始 | null |
| not_ended | 尚未結束 | null |
| skipped_start | 未開始即結束 | null |
| missing | 時間未記錄 | null |
| invalid | 時間資料無法辨識 | null |
| unknown_timezone | 時區未確認 | null |

標籤用「建立」「開始」「結束」「匯入確認」「預覽」「更新」「回讀」。區塊標示一次「台北時間（UTC+08:00）」，不讓「未知」提示仍像有效的台北時間。非 verified 格的「尚未驗證」由欄位層明示，不向 presenter 傳現在時間。

## 已知樣本

| raw | policy | occurrence | 結果 |
| --- | --- | --- | --- |
| `2026-11-27T03:04:05Z` | unverified | occurred | known：2026-11-27 11:04 |
| `2026-11-27T11:04:05+08:00` | offset_required | occurred | 同上，不再加8小時 |
| `2026-11-26T22:04:05-05:00` | unverified | occurred | 同上 |
| `2026-11-27 03:04:05` | sqlite_utc | occurred | 同上 |
| `2026-11-27 03:04:05` | offset_required／unverified | occurred | unknown_timezone |
| `2026-11-26T16:03:07.999999Z` | offset_required | occurred | known：2026-11-27 00:03，原精度保留、不進位 |
| null | sqlite_utc | not_started／not_ended／skipped_start | 各自文字 |
| null | 任意 | occurred | missing |
| `2026-11-27`／`bad`／`true`（布林） | 任意 | occurred | invalid |

另測跨月／年、年份溢位、24:00、閏秒、錯誤偏移與不存在日期。不得把上述樣本視為操作者 DB 的實際內容。

## 相容性

- 既有 raw timestamps、CatalogDTO、結果 snapshot、result_version、writeback 狀態與時間 writer 不改。
- 保留 `notes_time` filter 名稱，以本 presenter 產生安全文字；notes 的舊裸 filter 預設 offset_required。新增情境使用明確事件 view model，不用 filter 猜生命週期。
- 使用端以 textContent 或 Jinja 自動 escaping 顯示文字；不對 `text` 再 new Date／本地化／加八小時。
