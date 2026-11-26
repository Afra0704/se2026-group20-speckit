# Phase 0 Research：008 教師課程工作區

2026-11-25（Asia/Taipei）。Codex 與本技能要求的兩個唯讀研究代理，核對現有原始碼及 Google 官方文件；沒有啟動 app、開啟實際 DB／私人憑證、操作 OAuth、安裝套件或跑產品測試。

## R1 — 分層 HTML 保留原 JSON

**Decision**：Flask/Jinja、現有 JavaScript 與同一 app；新增 `workspace` HTML Blueprint。`/teacher` 變歡迎頁，`/teacher/workspace` 是課程卡片；課程／講義／課堂頁位於 `/teacher/workspace/courses/<course_id>/...`。

**Rationale**：現有 `GET /teacher/courses`、`.../classrooms`、`.../activities` 是 JSON，被 classroom.js 與測試使用；直接替換 HTML 會壞原介面。新頁以明確路由恢復上下文，不以全域 selectedCourse/localStorage 決定歸屬。課堂控制 JS 接受固定 course/room id，原學生腳本仍獨立。

**Alternatives considered**：同路由 Accept 協商會使舊 fetch 及一般瀏覽器預期混淆；SPA 增加路由、打包與狀態管理成本；沿用單頁大量隱藏表單不符合本輪操作脈絡。選新 HTML namespace，沿用現有 JSON mutation，不新增第二套教學服務。

## R2 — 官方 Picker、專用窄權限 client

**Decision**：同一 Cloud project 新增專用 Picker Web client；後端 code exchange、PKCE、nonce、`access_type=online`、`include_granted_scopes=false`。請求 `openid email profile`＋`https://www.googleapis.com/auth/drive.file`，前者核對／呈現目前 Google 身分，後者限 app 建立或使用者選擇的檔案。只選 Google Sheets、一次一份、沒有上傳功能。007 Sheets client／refresh credential 完全分開。

**Rationale**：Google 推薦每檔 `drive.file`；相較列出整個 Drive 的 metadata scope，能提供原生選擇且減少額外檔案資訊。專用 client 方便辨識與驗 `aud/azp`，不是隔離 project grants 的保證。API key／App ID／Picker client 必須屬同 project。

**官方事實與推論界線**：GIS 的 CodeClientConfig/TokenClientConfig 明說 false 只涵蓋本次 requested scopes；Web Server REST 表只明說 true 會合併既有 grants，且可跨同 project 的不同 clients。沿用 Python Flow 發同一 false 參數是協定推論，尚未真實 smoke。交付前須驗「已授權 broad Sheets 後仍只回窄 scope」；實際 scope 缺少、額外或無法確認一律拒交 Picker，不以 requested 補 granted。若 Google 行為不符，修配置／方案，不放寬 allowlist；貼連結路徑仍可用。

Sources：[GIS reference](https://developers.google.com/identity/oauth2/web/reference/js-reference)、[Web OAuth / incremental](https://developers.google.com/identity/protocols/oauth2/web-server#incrementalAuth)、[Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)、[Picker sample](https://developers.google.com/workspace/drive/picker/guides/web-picker-sample)。

**Alternatives considered**：

- 後端 `files.list`＋`drive.metadata.readonly` 不外露 token，但會讀取較廣 metadata，屬 restricted scope，非首選。
- GIS token model 雖有 false 明確行為，token 先進瀏覽器才輪到後端核對，不符合本輪先排除 broad scope 再交付的目標。
- 第二 Cloud project 隔離更強但增加 Console／測試使用者／client 管理；目前不是必要設定。
- 用 007 refresh token 加 scope 參數縮限：未找到 Google 官方保證，拒用。

## R3 — 有限的瀏覽器 token 邊界

**Decision**：後端先驗 Google ID-token 簽章、Picker client aud/azp、nonce、canonical issuer/sub 同目前教師、實際 scope allowlist，再把唯一窄 access token 由 CSRF/no-store POST 交 Picker。JS 只存記憶體，不放 cookie/localStorage/sessionStorage/URL。不交 refresh、ID-token、client secret 或任何 007 token。

窄 token 仍是 bearer credential，`drive.file` 可能涵蓋本 app 先前已獲選檔權限的多個檔案，不能宣稱只限本次單檔。Google 真正期限採 expires_in／expires_at；本系統 300 秒 delivery ticket 只限制交付及接受選擇，不表示 Google token 被提前撤銷。取消／離頁清理 JS 引用，不呼叫 Google revoke，以免同 project 的 grant 一起被撤。

**Rationale**：Picker 必須收到 access token，這是 007「任何 OAuth token 不送瀏覽器」的明確、限用途技術擴充，須在新契約與圖中列出；不弱化原登入與 Sheets 憑證邊界。憲章 IV 禁明文持久化與日誌，不禁止對必要 Google 元件提供短期窄 token。

原http.py全站強設no-referrer，而受網站來源限制的API key需真實驗Referer相容；只在乾淨workspace.import_page HTML用strict-origin-when-cross-origin，跨站僅origin，callback/token回應仍no-referrer。這是為key來源限制規劃的局部相容設計，不代表已實際驗過Google iframe。不得改成不限制API key。

**Alternatives considered**：直接把現有 Sheets token 填入 Picker 不可接受；把 API key 當使用者授權亦不可行；API key 是受來源與 API 限制的瀏覽器設定，不是 OAuth client secret。

Sources：[Picker overview](https://developers.google.com/workspace/drive/picker/guides/overview)、[OIDC](https://developers.google.com/identity/openid-connect/openid-connect)、[OAuth revocation](https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke)。

## R4 — online-only Picker 與兩種授權續接

**Decision**：Picker 只保存 Fernet 加密的窄 access token／真實 expiry，不保存或使用 Picker refresh；有效時沿用，剩餘不足 60 秒再發起授權。省略強制 prompt，不每次 consent/select_account；login_hint 只是提示，仍驗同 sub。若後端 token response 意外附 refresh／ID-token，驗完後不保存、不交付。

主 Sheets credential 沿用 007 的持久授權及顯式刷新。第一次 cloud 匯入可能需要 Picker 同意，選檔後若還沒有 Sheets 授權，再在同一匯入流程取得；已連接的老師直接沿用。兩步是不同存取需求，UI 明示，不能把窄 Picker credential 存入 google_sheets_credentials 或替代歷史回填來源。

**Rationale**：避免 Picker refresh 拿到 project 合併 scope 後被誤發給瀏覽器，也不新增一套 refresh lease。過期後是必要重新取 token，Google 既有同意／登入可能仍有效，不假承諾永不再跳 Google。

## R5 — 沿用一次 OAuth attempt，加 sidecar 與匯入上下文

**Decision**：007 的 `google_oauth_attempts.purpose IN(login,sheets)` 不改 CHECK、不重建舊表。008 的授權使用原 purpose=sheets，再以新 sidecar `credential_kind=sheets|picker`、flow_id 決定可信路由；沒有 sidecar 的既有 007 attempt 僅能用原 main client。Picker client 必須不同 main client。建立 attempt 與 sidecar、更新 flow.oauth_attempt_id 同短交易。

`configuration/validate_current/provider/service.finish` 都要按 DB sidecar 派發，不能只在 UI 加一個選項；Picker 成功走 picker_service，不走 sheets_service.connect。Picker sidecar 缺失、client 不符、flow 存在但續接關係缺失時拒絕，不降級 broad token。固定 callback 仍 `/auth/google/callback`，只 303 固定 flow 頁，無任意 next。原 login/sheets 整合測試須回歸。

**Rationale**：延續原 browser epoch/current grant、claim、nonce、PKCE；同 browser 同時只有最後開始的 Google 互動有效。不同匯入 flow 可並存，但被 supersede 的授權明確重試，不把一個 flow 的結果接給另一個。

## R6 — import_id tombstone 與所有新引用入口

**Decision**：新增 `notes_lecture_removals(import_id PK, removed_by, removed_at)`；無列=active。只插一次，不硬刪 notes_sources/imports/catalogs/questions/bindings。來源可共享，不以 source_id 移除；重匯同來源走新 UUID/version1。

**Rationale**：`notes_catalogs_no_update/no_delete` 明確保護版本，`owned_import/catalog_row` 被 export_service/writeback 共用，不能全域加 active filter。新增明確 `require_active_import`／同交易 `require_available_for_activity`；一般清單、同來源更新選項、未分配講義、重新分配、新版本、直接一般版本網址、新活動都檢查；歷史另以受權 activity reference 讀原 immutable catalog。

現有 create_activity 在交易前取得 Catalog/Display，交易內目前未重查可見性；008 必須在同個 BEGIN IMMEDIATE、store_activity 前重查，與 remove/version publication 線性化。confirm_preview 的已 confirmed 冪等分支也不能把 removed catalog 當一般可用結果回傳。

**Alternatives considered**：硬刪會破壞 FK／歷史；修改 immutable DTO 加 removed 欄位會影響嚴格驗證與其他模組；ALTER 多個舊表容易破壞 `INSERT ... VALUES`。tombstone 是最小附加狀態。

## R7 — 007 資料原地保留，附加 schema 原子化

**Decision**：沿用現有 `instance/classroom-007.sqlite3`、auth_instance UUID、教師／grants／密文及持久 key。008 使用新表／索引與明確 schema version；不對舊表刪除／重建／改 ID，不另開空白 DB 掩蓋相容問題。

原 notes.init_schema 與 google_login.initialize 是裸 executescript；008 附加步驟使用已確認的無外層交易連線，單個 `BEGIN IMMEDIATE; ... COMMIT;` 腳本，失敗明確 rollback、拒啟動。不得在現有 write_transaction 內呼叫會 implicit commit 的 executescript。既有 core 初始化可分段冪等執行，008 步驟與 schema marker 同交易，不聲稱整個歷代初始化天然跨段全原子。

**Rationale**：採 absence=active 不須回填全部舊講義；新 table 不重寫 credential ciphertext。測試用含 007 資料的暫存 fixture 驗兩次啟動／init-db 與注入中途失敗，不打開操作者 DB 測試。

Sources：[Python sqlite3 executescript](https://docs.python.org/3.13/library/sqlite3.html#sqlite3.Connection.executescript)、[SQLite transactions](https://sqlite.org/lang_transaction.html)。

## R8 — 驗證與相容限制

**Decision**：無新 Python 依賴；沿用鎖定 Python 3.13／Flask 3.1／Google SDK／cryptography。Picker 以官方瀏覽器庫載入，只在雲端選項操作時需要；不為本輪引入前端框架或 build pipeline。UI/JSON 分離，歷史 DTO／TeacherContext 不改。

測試須新增 populated 007 fixture、remove/create/version 屏障競態、受控 Google scope 輸出、真 Picker 同帳號 smoke、teacher+two students 人工矩陣。Google SDK／範例內容已查證不等於本機 Cloud 可用；本輪沒有這些實測，也不改 005/006/007 checkbox。

所有初期技術未知已作決策；仍需驗證的 Cloud 能力、窄 scope 真實往返及同學介面核對列入 quickstart／plan 待辦，不標成已完成或未解的需求問題。

## R9 — Phase 1 交叉檢查修正

兩研究代理唯讀核對已產出契約，發現原007會清除超過一天的terminal attempts；008的sidecar／flow若用預設FK RESTRICT會阻止隔日登入。已在資料模型指定attempt→sidecar CASCADE、flow.oauth_attempt_id SET NULL，過期不自動續接，並列超過24小時後新login／authorize測試。這是設計修正，沒有改DB或程式。

另明列selection外網後也重查credential generation/revision；flow清理前invalidate ready previews，避免失去mapping後從舊確認網址出版；補PICKER_SCOPE_REQUIRED=403與source_kind命名。原誤植notes檔名清單與HTTP Referrer相容亦在plan精確指向現有http.py。未發現剩餘阻擋tasks的明確route/status/DTO矛盾；這是AI交叉核對，不代表同學互審或speckit-analyze已完成。

## R10 — Analyze I1／U1 的使用者確認（2026-11-25）

使用者回覆「可以 使用你的建議」。I1採120秒未到busy、到期後原flow有效即可明確retry，保留輸入並以新claim/revision排除舊結果。U1採同輸入才冪等；修改分頁／名稱先revise，invalidate舊預覽並遞增choice_revision，completed不能改。這是本組設計補充，未代填OpenSpec D21或技術圖意互審。沒有新的Google事實查證或產品實測。
