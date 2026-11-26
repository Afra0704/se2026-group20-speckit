# Phase 1：題目顯示資料與活動快照

## 既有權威資料

- notes_catalogs 以 `(import_id, version)` 唯一，dto 為 canonical v1，recognized 為同次確認的完整不可變快照。
- recognized.questions/items 與 canonical catalog 按題號、種類、順序、數量及小題標號精確配對；只借 canonical IDs，不把來源座標或 observed_user_value 放進顯示資料。
- notes_answer_items.prompt_text 已有保存，本次不重建或回填此表，也不把它當獨立可變的文字權威。

## DisplayContentDTO v1

| 欄位 | 型別與限制 |
| --- | --- |
| display_contract_version | 整數，必須為 1，bool 不接受。 |
| import_id | 與所選 CatalogDTO 相同的 UUID 字串。 |
| import_version | 正整數，與所選版本完全相同。 |
| questions | 非空有序陣列；question_id/display_number/kind/items 與 canonical 清單完全一致。 |
| question_id | 該版本唯一、與 canonical 相同。 |
| display_number | 與 canonical 主題號相同，不重新編號。 |
| kind | single 或 question_set，與 canonical 相同。 |
| item_id | 該版本唯一、同題且同序，與 canonical 相同。 |
| subitem_label | 單題 null，題組沿用 canonical 標號。 |
| prompt_text | 非空字串（strip 僅用判空），保留字串本體；換行採既有 LF 正規化，不截斷、不自行改字。 |

各層嚴格拒絕未知欄位；不得含 blank_id、格位、來源 URL、observed_user_value、機敏設定或他組資料。缺漏、額外、重複、換序、跨版、錯題／小題均拒絕。

## activity_displays（新增）

| 欄位 | 限制 |
| --- | --- |
| activity_id | TEXT PRIMARY KEY，FK activities.id，一活動最多一個快照。 |
| dto | TEXT NOT NULL，寫入前已驗證的完整 DisplayContentDTO JSON。 |
| created_at | 建立時間，預設 CURRENT_TIMESTAMP。 |

新增表及防 update/delete trigger，在共用 activities/schema.sql 初始化；只新增結構、不遷移舊活動。catalog／display 同版比對後，以既有寫交易原子保存 activity、core questions、display 及課堂目前指標／版本。DB 失敗或權限／單活動衝突不得留下部分資料。

此表不取代 questions.content；003 仍收到原核心問題資料，排名與回填不依賴文字。重跑 init-db 保留全部新資料。

## 活動安全顯示狀態

- 有有效快照：`question_text_status=complete`；學生 item 包含 prompt_text。
- 無快照：`question_text_status=unavailable`；prompt_text 為 null，畫面明示舊活動缺全文，不能讀來源補字或改寫既有活動。
- 有快照卻身分／內容損壞：回明確錯誤，不能降級偽裝成正常 complete。
- activity phase 獨立維持 PREPARING→LIVE→CLOSED；讀到文字不代表可作答。完整版本可建立新活動，正常流程必須先結束目前活動。
