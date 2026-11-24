# Data Model: Guided Notes 匯入與回填

對應 [spec.md](spec.md) 及 [介面契約](contracts/interfaces.md)。2026-11-25 匯入、版本、課程關聯、回填預覽、作業、逐格紀錄及 lease 已建立；正式 002／003 provider 與人工驗收仍待完成。以下含歷史設計紀錄，以最新日期實作補充為準。
欄位使用 snake_case。日期採 UTC ISO 8601，UI 以 Asia/Taipei 顯示；識別及版本不得以來源座標代替。

## 識別與計數

- `import_id` 採 UUID4，`import_version` 為同一匯入的正整數版本。明確重新匯入可選原 import_id 並加版，首次匯入建立新 id。
- `question_id` 在版本內唯一，可用 UUID5(namespace=import_id, name=version+正規化主題號) 產生。`unit_id` 是 question_id 的別名，不另設獨立主鍵。
- `item_id` 依 question_id 及正規化小題標號產生，單題使用固定的 single 標記。`blank_id` 依 item_id 產生。
- 顯示主題號為正整數的十進位字串，小題標號保留顯示文字並另存正規化序號。重複主題號或重複小題序號拒收。
- `question_count` 等於主題號數與提交單位數，`answer_item_count` 為全部作答項目數。來源行數不作題數。

## Entities

| Entity／建議資料表 | 必備欄位 | 關係與驗證 |
| --- | --- | --- |
| SourceDocument／sources | source_id、teacher_id、spreadsheet_id、sheet_id、display_title | sheet_id 為 numeric id；title 可變。來源位置與存取資料限教師可見 |
| ImportedCatalog／catalogs | import_id、version、source_id、question_count、answer_item_count、semantic_hash、confirmed_at | 主鍵為 import_id+version，確認後不可變；舊活動引用舊版本 |
| MainQuestion／questions | question_id、import_id、version、display_number、kind、order_index | kind 為 single 或 question_set；每題是唯一提交單位 |
| AnswerItem／answer_items | item_id、question_id、subitem_label、normalized_subnumber、order_index、prompt_text | 單題一項且 subitem_label=null；題組至少兩項且標號唯一。prompt 留教師端供語意重檢 |
| Blank／blanks | blank_id、item_id | 每個作答項目唯一答案，不和標號格混用 |
| SourceBinding／source_bindings | blank_id、number_range、label_range、answer_range、top_left_anchor、observed_user_value | 範圍為 sheetId+零起算左閉右開 GridRange；label 可空；answer_range 支援跨欄合併 |
| ActivityReference／由 002 提供 | activity_id、owner_teacher_id、import_id、import_version、ended | 此功能以 provider 讀取，不另寫一份可分歧的活動狀態 |
| ResultSnapshot／由 003 提供 | activity_id、import_id、import_version、result_version、ended、units | 僅已結束且結算完成可提供，結算後不可變；一個主題號一個 UnitResult，必須覆蓋整個 catalog |
| UnitResult | question_id、winner_group_id、no_winner、answers | 有勝組時所有小題恰好一次且答案非空；無勝組則 winner=null、answers=[] |
| ItemAnswer | item_id、blank_id、answer_text | answer_text 為字串；去空白只作有效性檢查，保存原字串不 trim |
| ExportPreview／export_previews | preview_id、teacher_id、activity_id、import_id、import_version、result_version、structure_hash、value_hash、items、created_at、status | 僅 server-side 保存完整內容；綁定精確來源及結果，不可用任意 client DTO 替換 |
| PreviewItem | question_id、item_id、blank_id、current_binding、original_user_value、proposed_text、action | action 為 write、already_matches、skip、requires_overwrite_confirmation；無勝組不產生寫入 |
| WriteOperation／write_operations | operation_id、preview_id、teacher_id、source_id、idempotency_key、status、started_at、updated_at | UNIQUE(teacher_id, idempotency_key)，重複 key 不建立第二份作業，不同 payload 同 key 回 409 |
| WriteItem／write_items | operation_id、question_id、item_id、blank_id、status、error_code、observed_value、verified_at | 結果詳見下方；成功只能由回讀比對產生 |
| SourceLease／source_leases | spreadsheet_id、sheet_id、owner_token、operation_id、expires_at | 來源複合主鍵，短交易條件取得／續期／釋放；保護本 app 的並行操作 |

Repository 的 catalog／preview 內部資料可採經驗證 JSON 欄位儲存，questions／items／bindings 的查詢與唯一關係仍須有明確約束。
DTO 與資料表不必逐一分檔；先維持 models.py 與 repository.py，避免為每一項建立通用框架。

## 指紋與來源匹配

2026-11-23：ImportBundle 保存候選 CatalogDTO、spreadsheet_id 與 RecognitionResult；Fingerprints 由 import_service 計算三種 hash。純函式尚未發布版本，repository 須再分配／保存版本並持久化教師來源資料。export_service 的 ExportPreview／PreviewItem 可先完成領域判定，DB 接線時再保存 preview_id、owner、origin_operation_id、timestamps 與狀態，不可把 browser 傳回的物件直接反序列化為可信預覽。

- `semantic_hash` 包含主題號、單題／題組、小題序號、題目文字及組成順序；排除座標與答案。換行統一為 LF，其餘題目內容不任意忽略。
- `structure_hash` 包含 numeric sheetId、已辨識表頭／主題號／標號／答案的座標及 merge spans。單純工作表改名可重新顯示，不改來源身份。
- `value_hash` 包含預覽相關答案錨點的 userEnteredValue（含資料型別與公式）。無關格改動不使預覽失效。
- 純位置變動時，以正規化主題號及小題序號比對不可變 catalog，再重建新 preview binding。題目文字、主題號、小題集合或歸屬改變，停止並要求重新匯入與活動端明確核對，不自動重綁舊結果。
- 回填後要求 `userEnteredValue.stringValue == answer_text`。公式算出的相同顯示值、數字與相同外觀字串不視為已寫入文字的證據。
- 讀取時保存格式及非目標值供驗收比對，寫入僅使用答案單格錨點，不發 merge／format 更新。

## State Transitions

### 2026-11-25 持久化作業與恢復

新增 notes_write_operations（preview_id UNIQUE、teacher_id＋idempotency_key UNIQUE、request_hash、origin/root operation FK、status、blocks_source、error_code、timestamps）、notes_write_items（operation_id＋blank_id PK、題／小題識別、status、safe error、verified_at、observed_value）、notes_source_leases（物理 spreadsheet_id＋sheet_id PK、operation FK、owner token、epoch expires_at），以及 notes_export_context（preview FK、origin operation FK、actions JSON）。後者避免 ALTER 舊 preview 表，舊 preview 缺 context 時沿用純函式判定。

queued 為預留狀態，確認交易直接進 writing。每次送出前將該單位未 verified 項存為 unknown；短交易續租／保存回讀，不持交易連 Google。已失有效 lease 的未終態在報告讀取時標 recovering，不能重送同 preview。恢復先觀察、保存新 preview 與原結果／勝組，再以新 operation 連 origin/root。部分失敗／未知保留 blocks_source，同一物理來源的無關作業拒絕；整個恢復 lineage 完成後解除阻擋，保留每次歷史報告。

程序 mutex 防同進程交錯，DB lease 防重送及中斷後誤寫。沒有跨系統／跨服務程序的 Google fencing 保證；已發出請求逾時可能仍遠端完成。verified_at 為該項最近回讀一致時間，不承諾外部之後未改動。

### 2026-11-24 唯讀預覽持久化

新增 notes_export_previews，主鍵 preview_id，引用 notes_sources 及 notes_catalogs(import_id,version)。保存 activity_id、result_version、可信 snapshot JSON、observed_recognition JSON、semantic／structure／value hash、created_at 及 status（ready／consumed／invalidated）。本切片只建立 ready；consumed／invalidated 留給後續確認作業，沒有新增 WriteOperation 或 SourceLease。

owner 經 source.teacher_id 查驗；保存的 snapshot 必須先與真實活動引用的固定 catalog 驗證。observed_recognition 為預覽當時重新辨識的結果，可與原始 catalog 座標不同；GET 以兩者重建 PreviewItem，不把目前座標覆蓋舊版匯入 bindings。原始儲存格型別及精確答案文字保持不變。表為冪等新增，不刪除或改寫舊講義資料。

### 匯入

`preview` → 確認時重讀 → `confirmed`。辨識錯誤保持 preview 並列錯誤，不能發布 catalog。
確認前來源變動時重建 preview，版本只在成功確認時建立。

ImportPreview 保存 preview_id、teacher_id、source_id、候選資料、三種 hash、existing_import_id、status、confirmed_import_id／version 及時間。狀態為 ready／confirmed／invalidated。
來源確認重讀在 SQLite 交易外完成；進入短交易後重檢 preview 狀態，以條件更新與唯一 preview_id 發布一次 catalog。
相同教師的重送／並行確認返回同一 confirmed catalog，不遞增版本；修改 existing_import_id 的重送視為衝突。失效 preview 不可再確認，需建立新 preview。

### 回填預覽

`ready` → `consumed` 或 `invalidated`。來源／結果變動、教師權限失效使預覽 invalidated。
每次確認有 CSRF、teacher ownership、binding 與結果版本檢查；使用者需明確確認全份覆寫差異。

### 回填作業

`queued` → `writing` → `completed`／`needs_attention`。
應用重啟或既有作業無終態時轉 `recovering`，先回讀再進入 writing；recovering 不能直接重送。
同一 idempotency key 回現有作業；重新確認的恢復預覽建立新 attempt，連回原 operation 並保留勝組快照。

### 逐項結果

| 狀態 | 判定 | 可恢復行為 |
| --- | --- | --- |
| not_processed | 尚未送出相關請求 | 重檢與確認後可寫 |
| verified | 回讀 userEnteredValue 字串與預定答案一致 | 不重寫 |
| failed | 已知請求無效／拒絕或明確失敗 | 顯示原因，修正權限／輸入後重新預覽 |
| unknown | 逾時、斷線或回讀失敗，無法證明最終值 | 先回讀，不盲重送 |
| skipped | 主題號明確無勝組 | 保留來源原值 |
| conflict | 來源不是原值也不是預定答案，或來源語意／結果版本改變 | 內容衝突需新預覽明確確認；結構／結果衝突停止恢復 |

題組狀態由小題推導，不能獨立寫成完成。同組所有應寫小題 verified 才為完成。
整體只有 verified 與 skipped 時為 completed；全 skipped 亦可完成，報告明列零格寫入。
讀後被外部修改不代表能永久鎖住答案，報告保存 verified_at 與觀察值。

## 2026-11-24 教師顯示名稱 metadata

新增 notes_preview_names（preview_id FK／PK）與 notes_catalog_names（import_id+version 複合 FK／PK），各保存 name_mode=source|custom、custom_title。source 模式 custom_title 為 null；custom 文字在服務層驗證 1–100 字元且不可包含控制字元。名稱不加入 immutable catalog DTO，也不參與任何來源／題目／blank 識別或指紋。
新增表及 INSERT ... ON CONFLICT DO NOTHING 可對舊 DB 重跑，未有記錄的舊 preview／catalog 回填 source 模式，保留原表與全部資料；已保存的 custom 記錄不被初始化覆蓋。
名稱以版本為單位：新版本可另取名稱，舊版自訂文字不變。source 模式以 notes_sources.display_title 的最近來源快取顯示；notes_sources 仍只保存原分頁名稱，永不被自訂講義名稱覆蓋。

## SQLite 一致性

### 課程關聯附表（2026-11-24）

notes_import_courses：import_id 主鍵／FK → notes_imports，course_id（002 的不透明識別）、assigned_at。一個 import 零或一份關聯，所有版本繼承，UPDATE trigger 防止搬移。notes_preview_courses：preview_id 主鍵／FK → notes_import_previews、course_id；ready／替代／confirmed preview 都保留原 context。

本輪不建立 courses 表，也不預設 002 尚未提供的 course schema／FK。每次課程操作由 get_owned_course 查核真實 ownership；course provider 缺少時失敗封閉。正式 FK／課程刪除政策需與 002 對齊，不宣稱已具跨模組 DB 外鍵保障。

初始化只 CREATE TABLE／INDEX／TRIGGER，沒有為舊 import 自動 INSERT 關聯。舊資料由教師明確 assign；短交易查既有 assignment，ON CONFLICT DO NOTHING 保障同關聯重送，不同課程拒絕。CatalogDTO／UUID／版本及已存在活動完全不改；版本更新在寫交易前與交易內核對相同課程，防止並行分配造成跨課程更新。

- 開連線後設定 foreign_keys=ON、busy_timeout，連線限本 request 使用。只在短交易修改本機狀態。
- 本機 source lease 的主鍵與 operation 唯一約束以 BEGIN IMMEDIATE 交易取得，持有者必須有 owner token，網路期間不保持 SQLite transaction。
- 本機單進程以同來源互斥序列化網路階段，DB lease 提供崩潰／重送紀錄。單次 HTTP timeout 設 30 秒，有限重試須續租；建議 lease 300 秒，失去租約停止後續寫入。
- 重啟後先將無終態作業置 recovering，回讀全部已送出項目後才接受新的同源回填，避免到期後立即重送。
- 日誌只留 operation id、題目 id、錯誤碼、計數及時間，不記 token、完整 Sheet 回應或學生答案。
