# Interface Contracts v1

對應 [data-model.md](../data-model.md)、[format.md](format.md) 與 [examples.json](examples.json)。
欄位名稱為本輪設計，兩位 SpecKit 組員需在設計 PR 對齊。以 UTF-8 JSON 交換，避免跨模組直接存取資料表。

## Shared application boundary

- `create_app(test_config=None)` 由共用 shell 建立一次，註冊 auth、activity、notes Blueprints，設定 DB、CSRF、Google gateway 及 providers。
- 002 的 `require_teacher()` 返回 `TeacherContext(teacher_id)`，來源／活動 ownership 必須在後端檢查；不能信任 body、query 或 cookie 中自填的 role。
- 001 可先用 `create_app({"NOTES_BLUEPRINT": notes_blueprint, ...})` 在測試注入自己的 Blueprint，沿用 `guided_notes.db.connection()` 與 `write_transaction()`，再在整合階段接上正式 app 註冊。
- 001 提供 `get_catalog(teacher_context, import_id, import_version)` 給 002，回傳 CatalogDTO。002 檢查教師擁有來源，固定活動引用該版本。
- 002／003 提供 `get_ended_snapshot(teacher_context, activity_id)`，驗證 ownership，只有活動 CLOSED 且結算完成才返回 ResultSnapshotDTO；未結束回 ACTIVITY_NOT_ENDED，已結束但仍結算回 RESULT_NOT_READY。snapshot 結算後不可變，回填前仍需重檢結果版本。
- 單機只設定一個教師 Google profile；Google token 屬 gateway 的本機設定，不能放在上述 DTO、Flask session cookie 或回傳給瀏覽器。
- 僅供學生的 catalog view 可含主題號、小題標號及識別；教師来源綁定與未公開勝組不出現在學生回應。

## CatalogDTO

| 欄位 | 類型 | 規則 |
| --- | --- | --- |
| contract_version | integer | 固定 1 |
| import_id | UUID string | 對應已確認 catalog |
| import_version | positive integer | 精確匹配，不能自動取最新取代舊版 |
| question_count | integer | 等於 questions 長度 |
| submission_unit_count | integer | 等於 question_count |
| answer_item_count | integer | 等於各 question.items 長度總和 |
| questions | array | 主題號唯一，依來源順序 |
| question_id | UUID string | 同時為提交單位識別，unit_id 若出現必須相等 |
| display_number | string | 正規化正整數題號 |
| kind | enum | single、question_set |
| items | array | single 恰一項；question_set 至少兩項，item_id、blank_id 皆唯一 |
| item_id、blank_id | UUID string | 精確對應該 catalog 版本 |
| subitem_label | string or null | 題組為來源標號，如 (1)；單題為 null |

CatalogDTO 不包含來源範圍、原值、憑證或題目敘述。題組前端一次呈現其所有 items，全部 answer_text 去空白後非空才能提交。

## ResultSnapshotDTO

| 欄位 | 類型 | 規則 |
| --- | --- | --- |
| contract_version | integer | 固定 1 |
| activity_id | opaque string | 使用 provider 的同一活動 |
| import_id、import_version | UUID、integer | 精確匹配活動及 catalog |
| result_version | opaque nonempty string | 結束後不可變的結果版本 |
| ended | boolean | 必須 true，且由可信 provider 驗證 |
| units | array | 完整覆蓋 catalog 主題號，不重複、不漏題、不額外多題 |
| question_id | UUID string | 對應一個提交單位 |
| winner_group_id | string or null | 有勝組時非空、無勝組 null |
| no_winner | boolean | 無人勝出時明確 true；缺資料不推斷為無勝組 |
| answers | array | 有勝組恰好包含該主題號每個 item；無勝組為空陣列 |
| item_id、blank_id、answer_text | UUID、UUID、string | 身分對應且文字非空，答案保留原字串 |

勝組只出現在單位層，全部答案共享同一 winner_group_id。
若相鄰模組還提供小題層 group id，每項必須和單位層相同，否則 RESULT_INVALID。
排序演算法屬 003；001 僅驗證完整性與身份，不能重新挑選較快小題拼成題組答案。

## Teacher HTTP / UI contracts

2026-11-25 匯入、catalog、export confirm／operation／recovery 路由均已建立；正式課程／結算 provider 與人工驗收待接線。所有 `/teacher/notes` route 必須登入教師，並檢查對象 ownership；
所有 POST 使用共用 app 的 CSRF 驗證。JSON POST 使用 `X-CSRFToken`，既有 002 也可使用 `X-CSRF-Token`。HTML 表單用 `name="csrf_token"` 的隱藏欄位，值由共用 Jinja 的 `csrf_token()` 取得。

| Route | 輸入 | 成功結果 |
| --- | --- | --- |
| GET /teacher/notes | 無 | 匯入頁，顯示 Google 授權是否可用 |
| POST /teacher/notes/worksheets | spreadsheet_url | 列出可讀 worksheet 的 sheet_id、title，gid 僅用預選 |
| POST /teacher/notes/import-previews | spreadsheet_url、sheet_id | preview_id、來源、主題號數、小題數、對應與辨識錯誤；不寫來源 |
| POST /teacher/notes/import-previews/{id}/confirm | 確認，及明確重新匯入時的 existing_import_id | 重讀來源後返回 CatalogDTO，建立／新增版本 |
| GET /teacher/notes/catalogs/{import_id}/versions/{version} | 路徑識別 | 教師可查看 catalog 及自己的來源對應，與學生 DTO 分開 |
| POST /teacher/notes/export-previews | activity_id | server 取得 snapshot，回傳 preview_id、結果版本、逐項原值／預定值／動作 |
| POST /teacher/notes/export-previews/{id}/confirm | Idempotency-Key、confirm=true、overwrite_item_ids | 取得／執行作業，回傳 WriteReportDTO；key 重送回同作業 |
| GET /teacher/notes/operations/{id} | 作業 id | 報告及逐題／逐格狀態，不觸發新的寫入 |
| POST /teacher/notes/operations/{id}/recovery-preview | 無 | 回讀並重檢原 snapshot，建立連回原作業的新預覽 |

恢復預覽沿用相同 confirm route，必須保留 origin_operation_id 與原 result_version。
`overwrite_item_ids` 必須精確列出預覽中需要覆寫確認的小題，缺少確認時 OVERWRITE_CONFIRMATION_REQUIRED。
客戶端不能指定 spreadsheetId、範圍、預定答案或勝組取代已保存 preview。範圍只由 server 重新辨識。
若 source 或 result 變動，回 409 並使舊預覽失效，教師重新取得預覽及確認。

確認回填在本機 request 中執行，UI 停用重複按鈕但仍以 idempotency 為準；其他 request 可查作業。
作業已存在且正在 writing 時回 202 與相同 operation_id；終態則回 200 報告。
首次確認完成或需要注意時回 200，Google 失敗以作業報告表達；尚未建立作業的驗證錯誤採下表 HTTP code。
大活動逐題組處理，若本次執行期限已到，剩餘維持 not_processed，明確回報需恢復，不把剩餘工作留在未管理的背景執行緒。

## WriteReportDTO

包含 operation_id、origin_operation_id（可空）、activity_id、import_id、import_version、result_version、status、units、counts、updated_at。
每個 unit 有 question_id、winner_group_id、status 與 items；每個 item 有 item_id、blank_id、status、error_code、verified_at（可空）。
整體 status 為 queued、writing、recovering、completed、needs_attention。
逐項 status 為 not_processed、verified、failed、unknown、skipped、conflict；單位只在所有應寫 items verified 時完成，無勝組標 skipped。
UI 必須顯示未知與衝突，不能用「已送出」當作「已成功回填」。Google 原始錯誤、完整 API payload 及 token 不直接回傳。

## Error envelope

```json
{
  "error": {
    "code": "SOURCE_CHANGED",
    "message": "來源已變更，請重新預覽並確認。",
    "retryable": false,
    "context": {"sheet_id": 123, "question_number": "1"}
  }
}
```

context 僅限已授權教師可見的定位欄位。驗證先查權限再提供資源細節，未知／其他教師資源用 404 避免洩漏。

| HTTP | Codes | 恢復 |
| --- | --- | --- |
| 400 | INVALID_SHEETS_URL、INVALID_REQUEST | 修正輸入 |
| 401 | TEACHER_LOGIN_REQUIRED | 應用登入 |
| 403 | TEACHER_REQUIRED、CSRF_INVALID、SOURCE_READ_FORBIDDEN、SOURCE_WRITE_FORBIDDEN | 權限與授權檢查，區分應用身分與來源權限 |
| 404 | CATALOG_NOT_FOUND、PREVIEW_NOT_FOUND、OPERATION_NOT_FOUND、SOURCE_NOT_FOUND | 核對識別及 ownership |
| 409 | PREVIEW_STALE、SOURCE_CHANGED、SOURCE_STRUCTURE_CHANGED、RESULT_VERSION_CHANGED、ACTIVITY_NOT_ENDED、RESULT_NOT_READY、SOURCE_BUSY、IDEMPOTENCY_CONFLICT、OVERWRITE_CONFIRMATION_REQUIRED | 顯示原因，重新預覽／等待／核對結果 |
| 422 | HEADER_MISSING、HEADER_AMBIGUOUS、DUPLICATE_QUESTION、DUPLICATE_SUBITEM、ANSWER_AMBIGUOUS、ANSWER_OVERLAP、RESULT_INVALID | 定位修正，禁止確認 |
| 503 | SOURCE_READ_UNAVAILABLE、GOOGLE_REAUTH_REQUIRED、GOOGLE_RATE_LIMITED | 讀取有限重試或教師 CLI 重授權；寫入的不確定結果以 unknown 報告 |

## 同學介面審查清單

1. 共用 app factory、DB connection、teacher context、CSRF 及設定名稱，由一人建立骨架並讓另一人引用。
2. 002 固定 catalog 版本；主題號是 question_id／提交單位，小題是 items，不把每格算成一題。
3. 003 整組選唯一勝組、回傳完整小題答案及明確 no_winner，提供 immutable result_version。
4. ended snapshot 與 owner 由 provider 認定；本機示範可用受控測試 provider，正式路由不接受瀏覽器送入勝組。
5. errors、版本及 examples.json 加入契約測試。未確認的 D01–D04、D06、D08 交由相關功能共同定案。

## 001／002 已統一的接線（2026-11-23）

- package 為 src/guided_notes，001 notes、002 activities、003 quiz；Python 3.13。
- import_id／import_version 統一使用 CatalogDTO，001 對外函式位於 notes/import_service.py；002 的 activities/teacher.py 呼叫，不重寫 001 的儲存或格式辨識。
- CatalogDTO 的 questions 順序為來源順序，question_id 是提交單位，items 包含所有小題；002 的 position／order_index 為該陣列的本機排序記錄。
- 002／003 的 get_ended_snapshot 必須在 CLOSED 且結算完成時才交付全部 units。結算中回 RESULT_NOT_READY（409），001 不建立可確認的回填預覽。
- 共用 app factory、config.py、auth.py、db.py、http.py、pyproject／uv.lock 由 002 先建立；001 接 Blueprint 與既有連線。notes 模組不建立第二個 Flask app 或另一份活動資料庫。

## 2026-11-23 離線實作交接（尚未接線）

可直接匯入的純函式／類別：

| 入口 | 行為 | 接線責任 |
| --- | --- | --- |
| `notes.models.validate_catalog(catalog)` | 嚴格 v1 欄位、UUID、版本、計數與小題識別驗證；返回獨立複本 | 002 使用已發布清單；不可把來源綁定加進公開 DTO |
| `notes.models.validate_snapshot(snapshot, catalog, *, activity_id, result_version=None)` | 精確題目／小題集合、唯一勝組、原字串與固定版本 | 003 provider 先驗教師 ownership、CLOSED 且已結算；純驗證器無法替代這些檢查 |
| `notes.sheets_gateway.parse_sheets_url(url)` | 標準 HTTPS Sheets URL → `(spreadsheet_id, gid_or_none)`，不抓任意 URL | 001 routes 先教師授權，再解析及列工作表 |
| `build_google_service(credentials)` | 延遲載入官方 SDK，30 秒 timeout，停用授權層自動 refresh／重播 | 002 安裝共同依賴；001 CLI／服務在作業開始前更新憑證，不從學生輸入取得 credentials |
| `SheetsGateway(service).list_worksheets(id)`／`read_sheet(id, sheet_id)` | 列名稱與 numeric id，或取得單張 Sheet resource 含 data／merges | 回傳是教師來源資料，不可直接回傳學生 |
| `read_anchor_values(id, sheet_id, anchors)` | 取得目前錨點的原始 userEnteredValue 型別；省略的空白回 `{}` | export service 先重新辨識、驗證來源語意；不能只拿舊座標回讀 |
| `write_unit(id, sheet_id, writes)` | `AnchorWrite(question_id,row,column,text)` 清單，同主題號一次 RAW 請求；成功不產生 verified 狀態 | export service 必須先驗整組完整性、確認預覽／授權／lease，寫後回讀並保存報告 |

`ContractError`／`GatewayError` 暴露安全的 code、http_status，不包含原始 payload。
`CATALOG_INVALID` 是新增的內部 DTO 驗證錯誤（422），避免把壞清單當來源無資料；HTTP 接線時由共同錯誤 adapter 採相同 envelope。
`GOOGLE_DEPENDENCIES_MISSING` 僅供本機設定診斷，503；`SOURCE_WRITE_UNCERTAIN` 是底層寫入分類，export service 必須轉成逐項 unknown 報告，不直接當一般可重試 HTTP 錯誤。
`GatewayError.write_outcome` 為 failed／unknown（讀取為 null）；所有寫入都不自動重試。讀取 429／暫時 5xx 最多三次，延遲 1+jitter、2+jitter 秒。
缺少 settled provider 時不可呼叫回填，結算中由 provider 拋 RESULT_NOT_READY（409）；本輪未把這個跨模組檢查標為完成。
目前沒有 `get_catalog()` 持久化實作、Flask routes、CLI 或 DB；接線前先同步 002 骨架並驗證套件鎖檔。

### 同日續作：完整離線核心

上段「沒有 CLI」是第一個進度 commit 的狀態；目前已有獨立 CLI，仍無 Flask 註冊與 DB。

- `google_authorization.authorize(client, token, *, repo_root, interactive=False)` 回傳官方 credentials；預設不開瀏覽器，失效回安全 AuthError。環境／路徑只能由教師本機設定傳入，不接受 HTTP body 指定 token 路徑。`notes.cli.main()` 提供 check-config／authorize-sheets；002 Flask CLI 可沿用 helper。
- `import_service.build_import_bundle(spreadsheet_id, recognized, *, import_id=None, import_version=1)` 返回 ImportBundle，包含候選 catalog 與教師來源資料。UUID 依 import／版本／主題號／小題識別產生，與座標無關。這不是已發布版本；repository 必須在短交易內分配版本、保存與確認後，才能提供 get_catalog。
- `fingerprints(recognized)` 分開 semantic／structure／value hash；`match_source(bundle, current)` 先驗語意／sheetId，再按精確主題號與有序小題重綁目前答案範圍，變更題意或集合時 SOURCE_STRUCTURE_CHANGED。
- `export_service.build_export_preview(bundle, current, snapshot, *, activity_id)` 建立教師預覽，動作為 write／already_matches／skip／requires_overwrite_confirmation；來源及 snapshot 必須從可信服務取得。
- `build_recovery_preview(previous, current, snapshot, *, activity_id)` 保持原結果版本與勝組；先以目前結構重綁，再用目前值判斷原值／已完成／衝突。
- `prepare_writes(preview, current, snapshot, *, activity_id, overwrite_item_ids)` 重新檢查來源／結果及精確覆寫確認集合，返回每主題號一批 AnchorWrite；本函式不送出請求，也不取得授權或 source lease。
- `classify_readback(preview, observed_by_blank, outcomes_by_question)` 返回逐項／單位與整體狀態。observed_by_blank 映射 blank_id→userEnteredValue，缺 key 表示未取得觀察、`{}` 才是觀察到空白。outcomes_by_question 是 accepted／failed／unknown；未送出的題目不放入映射。接受回應但回讀失敗仍 unknown；只有精確字串一致才 verified。這是領域判定，DB 尚須補 operation／attempt／verified_at 與所有權等欄位。

**接線順序不能省略**：teacher ownership／settled provider → 保存 server-owned preview → 使用者確認 → 短交易 consume／idempotency／lease → 重檢來源與結果 → prepare_writes → gateway.write_unit → 回讀並 classify → 保存報告／釋放 lease。網路階段不持 SQLite 寫交易。

### 2026-11-24 共用骨架已取得

PR #4 已合併並整合至本機 001 分支。app factory／TeacherContext／require_teacher／DB／CSRF 入口已可沿用。正式依賴已包含 Google SDK。共用設定沿用 GUIDED_NOTES_SECRET_KEY／GUIDED_NOTES_DATABASE，Google 憑證保留 NOTES_GOOGLE_CLIENT_SECRETS／NOTES_GOOGLE_TOKEN。
001 後續資料表必須使用 notes_ 前綴（例如 notes_questions），避免與 002 的 questions 表衝突；來源／清單／預覽歸屬由 001 依 teacher_id 驗證，不直接跨寫 002 的題目表。
唯讀本機診斷已提供 `python -m guided_notes.notes.cli inspect-sheet --url ...`，不等同 HTTP 授權入口或已確認 catalog。

### 2026-11-24 匯入端已接線

- 預設 app 註冊 `notes` Blueprint，沿用共享 auth／CSRF／db；新增 `NOTES_GOOGLE_TEACHER_ID` 將單一 Google profile 綁到本機教師 ID。正常服務未設定或教師不符即拒絕；NOTES_GATEWAY 是 server config 的受控注入點，不由 HTTP body 設定。
- `GET /teacher/notes/import-previews/{id}` 為教師 HTML 預覽，列出題目／小題與 A1 範圍，confirmed／invalidated 不再顯示確認按鈕。
- JSON 確認須 `confirm=true`；HTML 表單須隱藏欄位 `confirm=true`。首次確認可選 existing_import_id，確認後重送須相同 target，回同一 CatalogDTO 且不重讀 Google。並行確認只發布一次；不同預覽更新同一 import 則原子取得下一版本。
- 確認前語意／結構／原值 hash 改變，舊預覽 invalidated，409 SOURCE_CHANGED 的 context 回 new_preview_id／preview_url，需再次確認。權限在讀取後再次驗證；不在 Google 網路期間持 SQLite 交易。
- `get_catalog(teacher_context, import_id, import_version)` 現已提供真實 provider；002 未注入 demo／替代 provider 時直接使用。未知或他人清單 404，不默認最新版本。
- JSON catalog 僅公開 DTO；教師 HTML 額外顯示已保存來源對應。HTML／JSON 的匯入均不寫 Google；只有本機 notes_ tables 發生變更。
- catalog 頁面呼叫既有 `/activities` 建立活動，再沿用 002 的 `guided-notes:teacher` localStorage 恢復活動畫面；提交資料仍僅 import_id／import_version，權限與清單驗證在後端完成。
- notes routes 的錯誤採原定 nested envelope，將共用 auth／CSRF 的代碼映射為 TEACHER_LOGIN_REQUIRED／TEACHER_REQUIRED／CSRF_INVALID；不改動 002 原有 flat error 回應。

### 教師顯示名稱擴充（共同需求 D12）

POST import-previews 可選 `name_mode`（source|custom，預設 source）與 `custom_title`。custom 模式需字串，trim 後 1–100 個字元且不含換行／控制字元；source 模式忽略未使用的 custom_title。無效輸入 400 INVALID_LECTURE_NAME，發 Google 請求前即檢查。
preview JSON 的 title 為有效顯示名稱，新增 source_title 與 name_mode；不返回任何憑證。命名選擇儲存於 server preview，confirm 不接受 name_mode／custom_title；來源變動新建 preview 時複製原選擇。
CatalogDTO／ResultSnapshotDTO 不改。教師 HTML 從 notes_catalog_names 取得各版本顯示 metadata，並另外顯示原始分頁與來源連結。不同分頁仍分別建立 sources／imports，不支援跨分頁重綁或自動合併。
目前沒有 production 的執行 driver，測試中的 InMemorySheets 僅是替代來源；不能拿它代替正式 provider／儲存。

### 2026-11-24 唯讀回填預覽已接線（T063–T065）

- 新增 `activities.teacher.get_activity_reference(teacher_context, activity_id)`，返回真實活動的 activity_id／import_id／import_version／ended，驗證目前教師與 ownership；未知或其他教師活動為 404 ACTIVITY_NOT_FOUND。不改既有活動 DTO／狀態／加入規則，需與同學互審此新增 adapter。
- `POST /teacher/notes/export-previews` 僅接受 activity_id；HTML 另接受 csrf_token。額外 snapshot／答案／來源等欄位一律 400 INVALID_REQUEST。先核對活動與固定 catalog，再使用既有 `quiz.results_gateway.get_ended_snapshot`；未結束／未結算／不完整或跨版本結果在 Google 呼叫前拒絕。
- 讀取後重新核對權限、活動引用與完整結果（不只 result_version）。短交易保存 source／catalog 外鍵、可信 snapshot、目前辨識及三種指紋；所有來源／provider 呼叫在交易外。回 201，包含 preview_id、status、activity_id、import_id/version、result_version、title、source_title、sheet_id、created_at、題數／作答數、items、counts、preview_url；不返回原始 Google payload 或完整 snapshot。
- items 僅含題／小題／blank 識別、顯示標號、winner_group_id、answer_range、original_user_value（保留 string／number／bool／formula 型別）、proposed_text 與 action。四種 action 沿用原契約，counts 是各 action 格數，並非回填成功數。
- `GET /teacher/notes/export-previews` 提供表單及擁有者保存的預覽清單；HTML POST 成功 303 轉向 `GET /teacher/notes/export-previews/{id}`。該 GET 預設 HTML，Accept: application/json 返回上述資料，只讀本機保存觀察，不驗證外部即時性，也不觸發 Google 讀寫。
- 確認／operation／恢復 route 尚未提供；沒有預覽確認按鈕，不存在寫入捷徑。沒有正式 GET_SETTLED_RESULTS provider 時維持 RESULT_NOT_READY，測試的 substitute 不加入正常啟動設定。

### 2026-11-24 課程講義接線（T066–T068）

完整交接、範例與 002 待辦見 [001-course-handoff](../../../docs/001-course-handoff.md)。以下為 001 本輪實作約定，待 002 接線審查，不宣稱對方已實作或 OpenSpec 已確認。

- 002 提供 `activities.course_service.get_owned_course(teacher_context, course_id)` → `{course_id,teacher_id,title}`。course_id 為 1–128 個英文字母／數字／底線／連字號；未知／他人課程 404 COURSE_NOT_FOUND。缺 provider 503 COURSE_UNAVAILABLE，001 不自行建立課程。
- 001 提供 `notes.course_catalogs.list_course_catalogs(teacher_context,course_id)`，返回 course_id、title、lectures（import_id 與 versions metadata）；versions 包含明確 import_version、title、source_title、question_count、answer_item_count、confirmed_at，按版本降冪。沒有來源座標／憑證。
- `get_course_catalog(teacher_context,course_id,import_id,import_version)` 核對教師／課程／關聯後返回原 CatalogDTO。002 建立課程活動必須呼叫此入口，不能只用舊的教師範圍 get_catalog。
- GET `/teacher/notes/courses/{course_id}` 為 HTML 匯入與版本清單；GET `.../catalogs` 及 `.../catalogs/{import_id}/versions/{version}` 為教師 JSON。
- POST worksheets／import-previews 可帶 course_id，後端在建構 Google client 前驗證；service 亦在讀取前後驗證。course_id 缺省保持 legacy；顯式 null／空白／非法格式 400。preview 回傳 course_id（legacy null）；confirm 若帶 course_id 一律 400，不接受換課程。
- POST `/teacher/notes/courses/{course_id}/lectures` 明確將自己未分配的 import 及所有版本加入課程，僅接受 import_id（HTML 另 csrf_token），成功 200 `{course_id,import_id}`；HTML 303 回課程頁。同關聯重送不重複，不同課程 409 COURSE_MISMATCH；不改 DTO／來源／舊活動。
- 不改原 snapshot 契約或活動碼；002 課程生命週期／刪除政策與活動 reference 仍須對齊，正式 FK 及課堂接線不在此切片完成範圍。

### 2026-11-25 既有回填作業與恢復已接線

本節取代 11/24 的「僅預覽」實作狀態；不改上方原定公開 DTO 與路由。

- confirm 僅接受 confirm／overwrite_item_ids；JSON 必須 Idempotency-Key header（1–128 個可見 ASCII、無空白），HTML 表單另帶 csrf_token／idempotency_key。key 綁教師與正規化 payload，同 key 改 preview／覆寫集合 409 IDEMPOTENCY_CONFLICT，已 consumed preview 改 key 409 PREVIEW_STALE。缺少／多餘覆寫項目 409，缺項驗證不 consume preview。
- 短交易保存 operation、逐格狀態與 preview consumed，物理 spreadsheet_id＋sheet_id lease／owner token，網路呼叫在交易外。相同 key 執行中回 202，終態回 200；正常確認完成後 HTML 303 到報告。
- 寫前／逐題組重檢教師、真實活動引用、完整結果及來源。每次 send 前先保存 unknown，故中斷不會被誤認未送出。每題組一次既有 RAW gateway；已相同／無勝組不寫。寫後即重新辨識來源並按身份讀值，只有精確 stringValue 相同為 verified。
- 寫前失效回 409（或對應權限／來源錯誤），context 含 operation_id，可查終止報告；舊 preview invalidated。送出後失敗／未知以 needs_attention 報告表達，未送出的單位保留 not_processed，不自動重送。lease 遺失停止後續寫入。
- GET operations 僅讀本機；無有效 lease 的 queued／writing 可改 recovering，但不連 Google／不寫 Sheets。報告含原契約欄位及安全 error_code；不含原始 API payload／答案／憑證。
- POST recovery-preview 僅接受空 JSON（HTML 另 csrf_token），先重檢原結果與目前來源／語意，再回讀；201 回原預覽格式及 origin_operation_id，HTML 303。新預覽保存原勝組、原 result_version 與判定 actions；再以新 key 明確確認才會寫入。即使已全部相同也可返回無待寫項的新預覽，舊報告同時記錄已回讀一致。
- 同源未完成 attempt 保留 blocks_source；只有該 lineage 的恢復可接續，完成後解除 root lineage 阻擋。程序 mutex 與 DB lease 皆以物理來源作鍵，跨教師各自的 source_id 也不得交錯。單程序／共用 DB 為適用邊界，不能代替 Google 外部編輯鎖。
- 執行預算預設 120 秒（server config NOTES_WRITE_SECONDS 可供測試調整），在題組邊界保留剩餘工作，不啟動未管理背景執行緒。lease 300 秒、SDK 30 秒 timeout；逾時不能證明遠端取消，恢復仍先讀後確認。
