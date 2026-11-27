# 008 匯入流程契約（計畫）

每個mutation需原CSRF與有效教師，flow固定原browser/current grant/teacher/instance/course；flow ID不可代授權。source_kind只能cloud/link，credential_kind另為picker/sheets。request body不接受teacher_id、grant、任意redirect或覆寫course。JSON錯誤保留notes巢狀envelope：`error.code/message/retryable/context`，內容無憑證或Google raw message。

## 新接口

基底 `/teacher/workspace/imports`。本節是新契約，不替換原notes API。

| 方法／路徑 | 輸入／效果 |
| --- | --- |
| POST `/teacher/workspace/courses/<cid>/imports` | `{source_kind:cloud}` 或 `{source_kind:link,spreadsheet_url:...}`；驗本人課程，201 `{flow_id,flow_url,status,source_kind}`，HTML表單303固定flow頁。link只在使用者明確讀取時發出，不在輸入中保存半流程。 |
| GET `/<flow_id>` | HTML目前步驟；無OAuth自動跳轉、無token。Accept JSON回安全狀態，含revision、choice_revision、retryable及reading的claim_until安全時間供顯示；是否可重試仍由POST後端當下判斷。 |
| POST `/<flow_id>/authorize` | `{credential_kind:picker|sheets}`；只准flow當前缺的kind。有效credential回200下一步，需授權時建立原attempt＋sidecar，API200 `{authorization_required:true,authorization_url}`，HTML303到Google固定endpoint；URL不包含access token。 |
| POST `/<flow_id>/picker/token` | 空body，cloud且可選檔；回窄token與ticket，詳picker-authorization.md。 |
| POST `/<flow_id>/picker/selection` | `{file_id,ticket_id}`，不能傳token或信任前端MIME/title；原子claim ticket＋flow，再於交易外驗Drive metadata。成功若Sheets可用即續讀分頁；缺授權202安全狀態needs_authorization=sheets。 |
| POST `/<flow_id>/read` | 空body；link已存canonical URL，cloud已有驗證file_id。無Sheets授權202 needs_authorization=sheets；有則claim→讀取→重檢→保存分頁清單200。 |
| POST `/<flow_id>/previews` | `{choice_revision,sheet_id,name_mode,custom_title?}`；choice_revision須匹配目前選擇版次，sheet_id須為目前候選，仍重讀來源驗內容。接原create_preview，201 `{preview_id,preview_url,flow_url}`。 |
| POST `/<flow_id>/revise` | `{expected_revision}`；教師明確按「重新選擇／修改名稱」。只允許已有分頁候選的worksheets_ready/preview_ready/failed，或claim已到期的reading；驗flow revision後，同交易使舊ready previews失效、清current_preview_id及舊preview請求快照，choice_revision與revision遞增。回worksheets_ready、候選及原命名供編輯，不讀Google或自動建預覽。來源／課程不變；completed、仍忙碌或舊revision拒絕。 |
| POST `/<flow_id>/confirm` | `{confirm:true,preview_id,existing_import_id?}`；只接受flow.current_preview_id，不允許course/name/source覆寫。呼叫原confirm_preview，成功200原CatalogDTO＋單獨外層導覽metadata或HTML303原課程講義頁，不能把flow欄位塞進嚴格DTO。 |
| POST `/<flow_id>/cancel` | 空body，原子標cancelled，清flow未用ticket；既有lecture不改，教師不登出、不revoke。 |
| POST `/<flow_id>/retry` | 空body，允許安全可重試的failed步驟，或reading且now >= claim_until；原flow/grant/課程仍須有效。以保存的動作／輸入快照原子取得新claim並遞增revision，再交易外重試；未到claim期限回409 FLOW_BUSY。selection仍驗ticket/cache期限，前置條件已失效則引導必要授權／重新選檔，不繞期限。expired/invalidated須新flow，不重送回填。 |

原notes確認預覽API格式仍是CatalogDTO。本輪confirm JSON成功明確採：`{"catalog": <原CatalogDTO>, "course_url": <固定本地URL>, "flow_id": ...}`，不在同一層混DTO欄位；preview/read等只回各安全格式。HTML正常POST成功303。

安全狀態例：

```json
{"flow_id":"flow-example","course_id":"course-example","source_kind":"cloud","status":"awaiting_sheets_auth","needs_authorization":"sheets","next_action":"authorize","retryable":false}
```

分頁成功例：

```json
{"flow_id":"flow-example","status":"worksheets_ready","worksheets":[{"sheet_id":7,"title":"學習單"}],"suggested_sheet_id":7}
```

GET流程狀態不能回source原答案／座標、google sub、grant、nonce、verifier、client secret、token或密文。只有獨立的picker/token POST是限用途窄token例外。

## 外網、續接與防重送

1. 建流程固定目前teacher與grant；flow預設30分鐘。登出、切換、grant失效、停用使flow失效；不因同一teacher重新登入就接到新grant。
2. authorize時原007 browser epoch遞增，最後開始的Google互動有效。OAuth attempt 300秒，sidecar固定kind/flow。callback只303 `.../imports/<flow_id>`，結果不從query purpose/next決定。
3. 多flow分別存course/source；同一browser兩個OAuth競爭時舊flow顯示GOOGLE_FLOW_SUPERSEDED，不誤存或改寫另一flow。callback失敗仍能回原課程，取消原有效教師不變。
4. read/selection/preview均先短交易原子claim，外網不持鎖，回來以claim/revision/current grant/flow TTL/原course重檢；selection另重查ticket的credential generation/revision仍是目前cache。120秒claim失效後舊結果不得保存。不得只在route開頭驗。
5. 同一flow、相同選擇版次及相同輸入才算重送：後端對白名單輸入做canonical JSON並保存SHA-256與原輸入快照；preview包含choice_revision/sheet_id/name_mode/custom_title（缺省null），confirm包含preview_id/existing_import_id（缺省null），selection包含file_id/ticket_id，read綁固定來源。沿用既有名稱驗證，不新增trim等改寫。已成功且指紋與原輸入均相同才回已有結果，不重讀或重建preview；同階段不同輸入回409 FLOW_STEP_CONFLICT，不回另一選擇的舊預覽。處理中未到claim期限回409 FLOW_BUSY＋Retry-After:1。
   failed或reading的claim到期後，只有明確retry可用原輸入原子取新claim；伺服器UTC時間now >= claim_until即到期，仍先驗30分鐘flow未過期。兩個retry只准一個取得claim；舊結果即使先於新結果回來亦不得保存。GET只顯示可重試狀態，不自動取得claim或呼叫Google。
   修改分頁或名稱必須先revise，回新choice_revision；舊版previews/confirm一律衝突，舊預覽經原notes確認URL亦不得出版。換檔或換入口另建flow。completed只准相同confirm冪等返回，不可revise。輸入快照不含憑證、題目答案或來源格原值。
6. 原create_preview及confirm_preview內增加可信flow guard，在它們自己的最終transaction驗並寫mapping／completed。不可在外層包write_transaction跨網路。confirmed重送返回既有結果前仍驗講義未removed；catalog與flow completed同commit。
7. 原SOURCE_CHANGED產生新preview時關聯同flow，更新current_preview_id，回409及新preview_url，老師需再次確認。既有preview不得以任意body指向他人的flow。
8. cancel/expire/invalidated同交易使flow綁定的ready notes previews失效；清理terminal flow/mapping前再確認無ready preview，舊notes URL不得繞flow期限。原007隔日attempt清理以sidecar CASCADE、flow.oauth_attempt_id SET NULL兼容；不能將NULL續接為新授權。

## 錯誤

| HTTP/code | 語意 |
| --- | --- |
| 401 AUTH_REQUIRED / 403 INVALID_CSRF | 原教師／CSRF失敗；notes畫面按原巢狀翻譯。 |
| 404 FLOW_NOT_FOUND / COURSE_NOT_FOUND | 不存在或非本人，不洩漏名稱。 |
| 410 FLOW_EXPIRED | flow TTL到期，回原課程重新發起。 |
| 409 FLOW_INVALIDATED | grant、instance、身分或授權續接關係改變，不能套用晚到結果。 |
| 409 FLOW_BUSY | 同步驟處理中，Retry-After:1，不多送Google請求。 |
| 409 FLOW_STEP_CONFLICT | 目前步驟不允許該操作／ticket不同檔重送。 |
| 409 GOOGLE_ACCOUNT_MISMATCH | 不同Google身分，保留原教師與credential。 |
| 503 PICKER_NOT_CONFIGURED / PICKER_SCOPE_UNSAFE | 專用client／key設定不全或token過寬，不交付；可明確改用新link flow。 |
| 403 PICKER_SCOPE_REQUIRED | 實際回覆缺必要scope或未同意，提示需要的權限，不破壞原有效cache。 |
| 400 SOURCE_NOT_GOOGLE_SHEETS / SOURCE_TRASHED | cloud metadata不符，不能保存；不自行刪檔或轉檔。 |
| 409 SOURCE_CHANGED / PREVIEW_STALE | 原預覽流程及重新確認。 |
| 410 LECTURE_REMOVED | 嘗試更新／重送已移除講義，另行新增才能產生新UUID。 |

原SOURCE_READ_FORBIDDEN、Google refresh busy/timeout Retry-After、recognition issues仍由原notes envelope傳遞；不把可讀不可寫誤報登入失敗。picker popupblocked／cancel在UI為可理解狀態，不假存成功。

## 2026-11-27 驗收補修

已連接的 Sheets 憑證被 Google 拒絕時，失敗流程提供明確重新連接表單，透過原 007 connect POST 的受限 return_to 返回同一 flow GET。這是獨立 Sheets 重連，不改 Picker sidecar、範圍或原 authorize 流程。返回後保留失敗來源連結及 pending flow，使用者須再次明確按讀取／重試；不另建流程或自動保存。單純分享權限不足與網路錯誤仍顯示各自錯誤，不誤導重新授權。