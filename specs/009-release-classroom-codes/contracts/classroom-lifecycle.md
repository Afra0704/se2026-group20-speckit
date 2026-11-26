# 009 課堂生命週期與有效碼契約

設計提案；使用者行為已確認，機器代碼／冪等回應為本次技術選擇，尚待課堂／003 同學核對。沿用同源 CSRF、no-store、ownership。

## HTTP

| 入口 | 成功／失敗 |
| --- | --- |
| POST /teacher/courses/{course_id}/classrooms | 原 title；驗有權教師。201：classroom_id、title、code、state=OPEN。code 仍五碼；新 ID 獨立。唯碼碰撞可重選，12 次候選仍失敗回 503 CLASSROOM_CODE_UNAVAILABLE；不得部分建堂。 |
| POST /teacher/classrooms/{classroom_id}/close | confirm 必須 true，否則 400 CONFIRM_REQUIRED。驗 teacher／owner 後，同一 BEGIN IMMEDIATE 完成未結束活動 transition、課堂 CLOSED／版本／時間。200 `classroom_state:CLOSED`；CLOSED 重送亦 200，不再 transition、重算、改版本或時間。 |
| POST /classroom-memberships | code＋group_name；沿用原長度／trim／大小寫規則。201：原 classroom_id、group_id；伺服器發新 grant／proof。無 OPEN 有效對應時 403 JOIN_DENIED，畫面一律「查無此課堂」，不區分從未存在與舊堂結束。 |

無有效身份 401 AUTH_REQUIRED，跨教師／課程沿既有 403／404 不暴露內容；busy 回 503 TEMPORARILY_UNAVAILABLE，不報成功。輸入非字串、空白或 code 原始長度>32 回 400 INVALID_REQUEST，group_name 原始最多80，trim後同堂同名仍同組。

## 碼／唯一性

- 產碼 `[A-Z]{2}[0-9]{3}`；輸入 strip＋upper，不移中間空白、不額外接受字形轉換。格式不合但符合原輸入門檻且無對應，一律 JOIN_DENIED，不新增碼格式錯誤分類。
- code 永久保留歷史值，只有 OPEN 進 `classrooms_open_code_unique`；查碼固定帶 `state='OPEN'`。舊全域 UNIQUE 必須透過 data-model 升級移除。
- insert_room 的 conflict target 改為與部分索引一致的 code＋OPEN predicate，只處理該衝突，其他 FK／CHECK／PK 失敗應 rollback，不能 `INSERT OR IGNORE` 吞掉。
- 無冷卻、全域系統分配；同教師／課程及跨教師／課程均可重用。不回收 ID／membership／group，不保證下一堂取得原碼。
- CLOSED 不可重開；教師有權亦同。單一活動結束不釋放課堂碼。

## 確認順序／R1～R8

| 情境 | 設計保證 |
| --- | --- |
| R1 同碼競爭 | DB 部分唯一約束為最後防線；另一新堂重選或 503，最多一個 OPEN。 |
| R2 先加入後關課 | 加入 commit 固定 A／原組；關課後所有原學生內容權失效，只顯示結束。 |
| R3 關閉與新分配間 | 無 OPEN 對應，JOIN_DENIED／查無此課堂。 |
| R4 新堂先確認 | 新的明確加入取得 B 新資格；原證明不參與選堂。 |
| R5 已解析目標失效 | 生產設計在同寫入交易解析及加入，不存在中間關課空隙；未來若預解析，確認仍須固定原 ID，失效拒絕，不重找 B。 |
| R6 關課失敗 | 所有活動／課堂狀態與索引占用一起 rollback，零半完成成功。 |
| R7 結束 A 重送 | 先驗 A owner；A 已 CLOSED 直接回狀態，不按碼刪除任何對應，B 無變更。 |
| R8 提交競爭 | 同寫入範圍驗原 activity／classroom／group；關課先 commit 則拒絕，先受理的答案仍固定原活動，不因後關課刪除。 |

資料庫 busy 的自動 retry 只能在尚未解析目標的取得鎖階段；已讀目標後的失敗整筆回錯，不同請求重試須是使用者明確送出的新加入。查碼／建組／membership／grant 不可分交易；session／cookie 僅在 commit 成功後更新。
