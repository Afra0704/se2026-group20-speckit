# 008 資料模型與狀態（計畫）

以下表／欄位尚未建立。沿用原007 DB、auth_instance、teachers、Google identities、grants、notes與classroom表；沒有資料重置或原DTO變更。

## 1. notes_lecture_removals

| 欄位 | 限制 |
| --- | --- |
| import_id | PK/FK notes_imports.import_id；整份講義，不是source或單版本。 |
| removed_by | NOT NULL FK teachers.id，必須與source owner及course owner一致。 |
| removed_at | NOT NULL UTC時間，首次移除時固定。 |

absence=active，插入=removed；沒有一般DELETE/復原路徑。原import/course/source/catalog及不可變觸發器保持。重複移除同owner回同結果，不覆寫時間。新匯入同來源可共享source_id，但新import UUID/version1，不復活舊import。

防線：一般查詢加NOT EXISTS；新activities或notes_catalogs的INSERT trigger只檢查removal並拒絕；服務內同transaction驗owner/course/active，trigger錯誤映射LECTURE_REMOVED。舊活動UPDATE與回填不能被這些trigger阻擋。

## 2. workspace_import_flows

| 欄位 | 限制／用途 |
| --- | --- |
| flow_id | 高熵UUID PK，可放本地URL但不是授權本身。 |
| teacher_id / course_id | NOT NULL FK teachers/courses；建流程與每次操作核對owner。 |
| instance_uuid | NOT NULL，與目前auth_instance一致。 |
| browser_hash | NOT NULL FK auth_browsers.binding_hash。 |
| expected_grant_hash | NOT NULL，原teacher_grant hash快照；不設cascade FK，登出後可保留失效流程並回清楚錯誤。 |
| source_kind | CHECK cloud/link；建後不可切換，改入口需取消舊flow並另建。 |
| spreadsheet_url / spreadsheet_id / suggested_sheet_id | 可空；link只存已解析Google Sheets canonical URL與識別，不接受任意URL；cloud ID在後端metadata核對前僅候選。 |
| source_verified_at | 可空；cloud後端驗MIME/trashed後才設定，link在本人Sheets成功讀取後設定。 |
| status | source_pending、awaiting_picker_auth、picking、awaiting_sheets_auth、reading、worksheets_ready、preview_ready、completed、cancelled、expired、invalidated、failed。 |
| revision | 正整數，每次有效狀態／上下文改變遞增，用於CAS。 |
| choice_revision | 正整數初始1，明確revise才遞增；previews輸入須匹配，避免修改後舊請求重建舊選擇。 |
| request_state_json | 有界JSON，僅selection/read/preview/confirm各一步的canonical白名單輸入、SHA-256、選擇版次與成功結果識別；不含憑證／題目答案／來源格原值。外網前與claim同交易保存，failed仍保留，terminal按原24小時規則清理。revise清舊preview快照／引用，保留已驗來源。 |
| retry_action | 可空selection/read/preview；reading及可重試failed保留動作，與只在reading存在的claim_action區分。成功清空；無可信輸入快照不得retry。 |
| oauth_attempt_id | 可空 FK google_oauth_attempts.attempt_id ON DELETE SET NULL；每次重新授權更新，舊attempt不能續接。原007的24小時attempt清理不應被此參照阻擋。 |
| worksheets_json | 可空，只存安全的sheet_id/title候選；不存題目答案或token。 |
| current_preview_id | 可空 FK notes_import_previews.preview_id，僅本人／同課程可關聯。 |
| confirmed_import_id / confirmed_version | completed必有，FK原catalog版本；不自行複製題目。 |
| claim_id / claim_action / claim_until | reading時必有；claim_action=selection/read/preview，最長120秒，外網外的原子claim與finalize用；其他狀態為NULL。 |
| error_code | 可空，安全白名單；無provider raw message、URL、nonce或token。 |
| created_at / expires_at / updated_at | UTC epoch；expires_at=建立後1800秒，不因反覆GET延長。 |

flow不儲存OAuth code/state/verifier；原attempt負責。flow也不以browser epoch作固定不變條件，因自身OAuth start會遞增epoch；固定的是原browser＋目前grant，原attempt另外驗它自己的epoch。switch/login成功換grant、logout、停用、grant自然到期均使原flow失效。

一般狀態流：

```text
cloud: source_pending → [awaiting_picker_auth] → picking
       → reading(selection) → [awaiting_sheets_auth] → reading(read)
link:  source_pending → [awaiting_sheets_auth] → reading(read)
共用:  reading(read) → worksheets_ready → reading(preview) → preview_ready → completed
任何未完成: → cancelled / expired / invalidated
外部暫時失敗: reading → failed（安全code，可由明確retry回前一合法步驟）
```

方括號只在需要授權時發生。挑選取消不建preview。未完成read claim到期可由新明確retry取得新claim，舊claim的晚回CAS失敗；不自動replay寫入。confirmed重送僅在原flow／preview／active catalog匹配時回既有結果，不能復活removed。

重試邊界：failed或reading且now >= claim_until可明確retry；未到期限仍FLOW_BUSY，flow先到1800秒則FLOW_EXPIRED。短交易驗grant/course及保存的動作／輸入後，以CAS取新claim並遞增revision；兩個重試只有一個成功，舊claim無論何時回來都不得finalize。selection仍驗ticket/cache期限，不借重試延長授權；缺前置條件返回重新授權／選檔。GET不自動重試。

重送與修改：同動作、同choice_revision、相同canonical輸入才可回既有成功結果；不同輸入FLOW_STEP_CONFLICT。教師明確revise（附expected_revision）才可修改分頁／名稱；需已有候選、未完成且無有效claim。單交易invalidate舊ready previews、清current_preview_id與舊preview快照、遞增choice_revision/revision、清claim/retry_action後回worksheets_ready；舊notes確認URL與舊版請求均拒絕。原命名在清快照前取出供編輯，不自動建preview。completed禁止revise，換來源另建flow。確認請求的existing_import_id亦納入相同比對。

## 3. google_oauth_attempt_context

| 欄位 | 限制 |
| --- | --- |
| attempt_id | PK/FK 原google_oauth_attempts ON DELETE CASCADE。 |
| flow_id | NOT NULL FK workspace_import_flows ON DELETE CASCADE。 |
| credential_kind | CHECK sheets/picker，可信server欄位，不能由callback query覆寫。 |
| created_at | UTC。 |

原attempt purpose仍是sheets，Sheets或Picker由sidecar區分。attempt＋sidecar＋flow.oauth_attempt_id同短交易建立；原claim/status/300秒/nonce/PKCE/epoch保持。callback finalize需驗flow仍指向本attempt、同grant/course、有效且處於對應awaiting狀態。

沒有sidecar的原007流程只可用main client；Picker專用client不同main，不能因sidecar遺失誤走main。若flow已指向某attempt但context遺失亦拒絕。不修改既有CHECK或重建原表。

## 4. google_picker_credentials

| 欄位 | 限制 |
| --- | --- |
| teacher_id | PK/FK google_identities.teacher_id；每教師目前一份窄cache。 |
| instance_uuid / issuer / subject / client_id | NOT NULL，與當前DB、教師Google身分、專用Picker Web client一致。 |
| credential_id / revision | 新連接UUID generation與正revision；新grant結果替換同教師cache時更新。 |
| actual_scopes | 排序JSON；必含openid/email/profile/drive.file且正規化後不得超出這四者。 |
| expires_at | Google真實epoch expiry，不是本機ticket TTL；剩餘<=60秒不交付。 |
| secret_blob | NOT NULL Fernet，payload僅access_token/scopes/expiry；envelope另綁purpose=picker、owner/instance/issuer/sub/client/generation/revision/scopes/expiry。 |
| created_at / updated_at | UTC。 |

不存refresh token、ID token、verifier、client secret，不使用007的Sheets refresh取得Picker token；未知scope fail closed。007與Picker密文不可互換。cache可在同教師之後有效grant使用，權限不是由舊grant繼承，交付仍驗新grant。

過期後新online OAuth，不假裝本地清空就撤銷Google token，不呼叫revoke。Google實際grant未撤時可免再次同意，但不承諾永遠不跳帳號頁。

## 5. workspace_picker_tickets

| 欄位 | 限制 |
| --- | --- |
| ticket_id | 高熵UUID PK；只限受權flow，非獨立登入token。 |
| flow_id | NOT NULL FK flow ON DELETE CASCADE。 |
| credential_id / credential_revision | 綁本次窄cache generation，不接受被新連接取代的結果。 |
| expires_at | min(now+300, flow expiry, Google expiry-30秒)。 |
| used_at | 可空；接受selection時原子claim，不能用同ticket改選另一檔。 |
| created_at | UTC。 |

交付token與接受selection均驗本人grant、flow.course、client/scope/expiry。selection重送若flow已往後且file_id同，可回既有狀態，不能重新網路讀取；不同ID回衝突。popup blocked/cancel清JS引用，取消flow不撤整個Google grant。此ticket不會縮短Google token真正有效期。

## 6. workspace_preview_flows

preview_id PK/FK notes_import_previews、flow_id NOT NULL FK flow ON DELETE CASCADE、created_at UTC；一個flow可有來源變動後的多個歷史preview，current_preview_id只指目前可確認者。create_preview／confirm_preview須在各自最終transaction內驗flow guard並更新對應；不要外層包transaction跨原服務網路。

確認成功時catalog publication、flow completed及confirmed reference同transaction。confirmed preview既有結果分支亦檢查removal；來源變動新preview更新映射，不接受前端指向其他preview繞過課程。

## 7. 附加 schema marker 與初始化

`workspace_schema_versions(version INTEGER PK, applied_at UTC NOT NULL)`，008版本標記與新增schema同transaction。無全域PRAGMA user_version接管，無ALTER舊表、強制重置或密文rewrite。notes tombstone表與workspace新表按FK順序初始化；原core/Google/notes先完成，008步驟再BEGIN IMMEDIATE。executescript不能在舊transaction內偷偷commit；錯誤明確rollback並拒啟動，不補空白DB。

分段界線：notes_lecture_removals與純visibility triggers歸notes.schema，所有模式都初始化；notes附加段以明確transaction包住，失敗回滾該段。flow／Picker／context等Google依賴表歸workspace.schema，只在Google＋classroom模式初始化，其marker只代表這一段。失敗可能保留先前已成功的冪等DDL，但不改既有業務資料；修復後重跑，不能假稱整個歷代app init全原子或給舊fixture正式bypass。

原TeacherContext、CatalogDTO v1、DisplayContentDTO v1、ResultSnapshot不加可見性或Google欄位。一般可用性與歷史讀取是不同服務意圖，低階owner查詢不作全域active filter。

## 8. 有界清理與舊preview安全

007 start已會清除expires_at早於一天前的terminal attempts；上方attempt FK的CASCADE/SET NULL必須落實，不能以預設RESTRICT令隔日Google登入失敗。被清理的flow不得因oauth_attempt_id=NULL被當新流程自動繼續。

flow取消／過期／grant失效時，在同短交易將其所有仍ready的notes_import_previews改invalidated（已confirmed不改），取消ticket與綁定續接。保留terminal flow至少24小時供安全提示；之後有界刪除flow，cascade context/ticket/preview mapping，不刪catalog／activity／operation。刪mapping前再次確保無ready preview，避免失去flow guard後舊notes確認URL重新出版。測試涵蓋24小時後新登入、取消／expired preview走舊API確認被拒、completed版本與歷史保留。

失效標記及ready-preview invalidation必須commit後再回錯誤，不在同交易內拋ApiError而使這些清理回滾；未能寫入時仍依原flow期限／grant guard拒絕，後續有界清理再處理。清理不得把曾綁flow的ready preview變成無flow的一般可出版預覽。
