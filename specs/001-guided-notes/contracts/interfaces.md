# Interface Contracts v1

對應 [data-model.md](../data-model.md)、[format.md](format.md) 與 [examples.json](examples.json)。
欄位名稱為本輪設計，兩位 SpecKit 組員需在設計 PR 對齊。以 UTF-8 JSON 交換，避免跨模組直接存取資料表。

## Shared application boundary

- `create_app(test_config=None)` 由共用 shell 建立一次，註冊 auth、activity、notes Blueprints，設定 DB、CSRF、Google gateway 及 providers。
- 002 的 `require_teacher()` 返回 `TeacherContext(teacher_id)`，來源／活動 ownership 必須在後端檢查；不能信任 body、query 或 cookie 中自填的 role。
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

以下路由為實作目標，尚未建立。所有 `/teacher/notes` route 必須登入教師，並檢查對象 ownership；
所有 POST 驗證 CSRF token。JSON POST 使用 `X-CSRFToken`，頁面隱藏欄位由共用 Flask-WTF 提供。

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
