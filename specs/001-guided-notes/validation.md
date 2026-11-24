# 001 實作與驗證紀錄

## 2026-11-23：離線辨識核心

- 執行者：Codex；人工驗收尚未執行。
- 分支：`codex/001-guided-notes-implementation`，基準 `0486332`（已合併 PR #3）。本輪修改尚未提交。
- 使用者回報同學已審查並合併設計 PR；記錄審查事實，不推定實作或人工操作已驗收。
- 共用骨架仍依已合併分工由 002 建立；使用者回報同學尚未開始實作。
- 為讓兩人同時前進，先獨立實作無 Flask／DB／Google 依賴的純解析切片。這是 T003、T015、T017 的離線工作；T002 及 Phase 2 接線未完成，不宣稱整個前置階段已通過。

### 已完成產物

- `src/guided_notes/notes/recognition.py`：教師端辨識候選資料、GridRange、定位錯誤、表頭與合併區解析。
- `tests/fixtures/sheets_layouts.json`、`build_layouts.py`：九份可重產合成版型。
- `tests/unit/test_recognition.py`：11 個測試方法，錯誤矩陣另涵蓋六種無效版型。
- 辨識結果尚未發布 UUID／版本，不是可直接交給學生的 CatalogDTO；來源位置與原值只保留於教師候選資料。

### 驗證

先建立測試並執行，因模組尚未存在得到 `ModuleNotFoundError`（預期失敗）；實作後宿主 Python 3.14.7 的 11 項測試全通過。團隊 Python 3.13.1 重驗亦為 11／11 通過，退出碼 0。`git diff --check` 通過。未安裝 Flask／Google 套件，不宣稱整套環境 smoke 通過。

```powershell
$env:PYTHONPATH = 'D:\os_final\src'
& 'C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe' -m unittest discover -s tests/unit -p test_recognition.py -v
```

涵蓋單題、題組、分隔列、欄列位移、變寬答案、Google 省略的空白尾格、合併錨點、公式原值、題目換行與空白保留，以及重號、缺表頭、標號重複、未對應列、答案歧義／交疊。解析不修改輸入。

### 圖表與程式對應

- Component 的 Import and Recognition 對應 `recognize()`。
- Class 的 MainQuestion／AnswerItem／SourceBinding 在本切片為 RecognizedQuestion／RecognizedItem／GridRange 候選；持久化實體與 UUID 留給後續 models／repository。
- Sequence 的讀取後辨識與拒絕歧義分支已離線驗證。授權、來源讀寫、預覽確認與恢復尚未實作；不把整張時序圖標為完成。
- 既有三圖的責任／流程未改動，本輪不需重渲染。

### 未完成與交接

- 002 先提供 pyproject／uv.lock、create_app、auth、DB 與共用錯誤處理；001 會沿用，不建立第二套。
- 匯入預覽持久化、版本化 CatalogDTO、Google gateway／授權、Flask 頁面、回填與恢復仍未完成。
- 完整 Sheets 中繼資料、權限與真實讀寫，以及兩位組員各自完整操作 M01–M10，皆未驗收。
- 之前分析的恢復順序、預覽狀態及人工驗收範圍補入 plan／data-model；全套 analyze／converge 尚待後續階段執行。

## 2026-11-23：資料契約、Sheets gateway 與授權準備

**範圍**：使用者明確要求共用骨架前先執行純資料、Google 邊界、模擬測試及準備文件。沿用目前分支／未提交修改，不重做 T003／T015／T017。共用 app factory、登入、DB、pyproject／uv.lock 均未新增或修改。

**技能門檻**：check-prerequisites 回 FEATURE_DIR=`D:\os_final\specs\001-guided-notes`；requirements.md 16／16 勾選、0 未勾選。檢查表檔未修改；前後皆沒有 `.specify/extensions.yml`，因此沒有前後 hooks。

### 產物與任務

- `notes/models.py`：validate_catalog／validate_snapshot，嚴格 v1 欄位、UUID／版本／計數、單題／題組、精確成員集合、唯一勝組與原字串保留。未知欄位拒收，來源綁定／憑證不能混入公開清單。這是 DTO 驗證，不是身分授權或結算證明。
- `notes/sheets_gateway.py`：標準 Sheets URL／gid 解析（query 與 fragment 同 gid 可接受）、列工作表、numeric sheetId 的 getByDataFilter、原始型別回讀、同主題號單次 RAW 錨點批次。官方 client factory 延遲載入，30 秒 timeout，停用授權層自動 refresh 重播。
- 讀取 429／暫時 5xx 最多三次，假時鐘驗證 1+jitter、2+jitter；寫入 num_retries=0，400／401／403／404／429 為明確 failed，timeout／5xx 等為 unknown，無自動寫入重送。低階 gateway 不產生 verified；服務接線後必須先驗來源、授權、lease、確認，再寫後回讀。
- `docs/google-sheets-setup.md` 與 README：Cloud project、Sheets API、Desktop client、測試使用者、repo 外 client／token 路徑、後續授權順序及當前限制。
- 完成 T005／T014／T018／T032，本輪加 4 項，累計 7／59。T010、T026、T029、T044 僅有子部分進度，尚未具備所有成果，維持未勾選；T019 OAuth CLI 完全未完成。

### 實際驗證

執行者 Codex，Python 3.13.1，基準 commit 0486332，本輪工作樹尚未提交。

```powershell
$env:PYTHONPATH = 'D:\os_final\src'
& 'C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe' -m unittest discover -s tests/unit -v
& 'C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe' -m unittest discover -s tests/contract -v
& 'C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe' -m unittest discover -s tests/integration -v
```

| 預期 | 實際 |
| --- | --- |
| 先建契約與 gateway 測試，確認無實作時失敗 | 新增 models／gateway 前均 ModuleNotFoundError；原 11 項辨識測試通過 |
| 單元測試通過，含原辨識與讀寫失敗分類 | 28／28，退出碼 0 |
| 契約測試通過，含七組既有範例及無效資料矩陣 | 10／10，退出碼 0 |
| 離線元件交接通過 | 2／2，退出碼 0；gateway→辨識含移動版型，DTO 清單→結果保留文字 |
| Google fields mask 含 grid／merges 且括號有效 | 最後檢查發現多一個右括號，已修正並加結構檢查，重驗通過 |
| 不變更共用骨架、不連真實 Sheets | 所有測試使用替代 service／依賴，無網路或實際帳號；無共用 app／登入／DB 檔案 |

合計 **40／40** 個測試方法通過，另外包含多個 subTest 錯誤矩陣。這不代表 Google 服務端已接受請求；SDK 安裝 smoke、OAuth、Google API 格式及真實權限仍須在鎖定環境驗證。

### 圖表／憲章與交接

- Source Access 對應 SheetsGateway，MainQuestion／AnswerItem 的交換規則對應 models 驗證。既有 Component／Class／Sequence 的責任與流程未改動，因此沿用已渲染圖；並未宣稱 Export、Store、教師流程已實作。
- 改用 numeric sheetId getByDataFilter 是 Source Access 內部定位選擇，理由與官方來源記於 research.md；不更動雙組作答規則。
- 模組沒有 import Flask／DB／auth；呼叫者仍須採 002 的 teacher context、ownership、CSRF、同一 app／DB。來源資料留教師端，gateway 錯誤不包含 token／API 原始錯誤或學生答案。
- 002 需提供共享依賴環境、app factory、auth／DB；001 後續接 Google CLI、預覽持久化及 routes。003 需提供 CLOSED 且已結算的可信快照，未結算回 RESULT_NOT_READY；本輪不以純 DTO 驗證器替代 provider。
- 實際介面簽章、安全錯誤代碼及先後條件記於 contracts/interfaces.md「離線實作交接」。
- 真實 SDK／Sheets、完整 HTTP／DB／活動流程、組員人工驗收、analyze／converge 仍未完成。

## 2026-11-23：完成共用骨架前的離線領域核心

### 授權範圍與版本

使用者要求先完成不依賴同學的部分，允許先 commit 保留進度。已建立本機進度 commit `05186ed`，包含前輪 40 項測試成果；本輪在同一分支繼續，尚未 push／開 PR。
本輪沒有新增共用 app factory、教師登入、DB、pyproject.toml 或 uv.lock。未碰既有不明名稱的未追蹤檔案。
check-prerequisites 指向 001，requirements.md 仍 16／16，檢查表未修改。沒有 extensions.yml，因此無前後 hooks。

### 已完成的可獨立測試部分

- `import_service.py`：候選 catalog 與非座標 UUID4／UUID5 識別、版本識別、semantic／structure／value 指紋、純位置移動重綁、題意／題號／成員改變停止。尚非 DB 已發布版本。
- `export_service.py`：完整快照驗證後產生預覽，保留字串／原值與同一勝組；確認精確覆寫集合；舊預覽遇來源或結果改變停止；恢復先重新定位再按目前值分類，相同答案不列入待寫；回讀分類與逐單位完成條件。這是純資料判定，尚無 production 寫入 driver。
- `google_authorization.py`／`cli.py`：repo 外且不同的 client／token 路徑、Desktop config／scope 檢查、token 載入／刷新、CLI-only loopback 同意、原子保存。一般請求不開瀏覽器，invalid_grant／儲存失敗只回安全代碼。Windows 私人目錄權限依使用者／ACL 管理。
- `tests/integration/test_offline_recovery_flow.py`：受控來源模擬全題組寫入後回應遺失，回讀證實成功後恢復不重送；無真實 Google／DB／HTTP。
- `tests/integration/test_import_capacity.py`：100 個主題號 × 10 小題，1000 個唯一 blank、100 個每次 10 項的 mock RAW 批次。
- T027／T038／T053 已有適用成果及驗證，新增完成三項，累計 **10／59**。含接線的 T019／T020／T021／T031／T033／T034／T041 等雖有核心進度，保持未完成。

### 最終驗證

執行者 Codex，Python 3.13.1，無 Google 憑證／網路來源，PYTHONPATH 僅 src。先建立新測試，import_service／export_service／google_authorization 尚不存在時確認 ModuleNotFoundError，再完成實作。

| 指令（Python 3.13.1） | 實際結果 |
| --- | --- |
| `-m unittest discover -s tests/unit -q` | 58／58，退出碼 0 |
| `-m unittest discover -s tests/contract -q` | 10／10，退出碼 0 |
| `-m unittest discover -s tests/integration -q` | 4／4，退出碼 0 |
| `-m guided_notes.notes.cli --help` | 成功列出 check-config／authorize-sheets，退出碼 0 |
| `git diff --check` | 通過；只有既有 LF／CRLF 提示 |

合計 **72／72**。容量觀察在 tracemalloc 開啟下為 **1.398 秒、peak 4.27 MiB**；只代表本機合成案例，不是延遲 SLA、拒收上限或 Sheets API 負載測試。

### 官方 SDK 實際 smoke（與離線測試分開）

首次沙箱安裝遇 DNS 限制，經工具核准後以 uv 安裝至忽略的 `tmp/sdk-smoke`，不改共用環境：google-api-python-client 2.202.0、google-auth 2.63.1、google-auth-oauthlib 1.5.0、google-auth-httplib2 0.4.4（含間接依賴共 25 套件）。
Python 3.13 成功 import 官方 SDK，使用合成 token 建立 service／numeric sheetId getByDataFilter／RAW batchUpdateByDataFilter 的 request 物件，**沒有呼叫 execute、沒有 Google 授權或來源讀寫**。查核 InstalledAppFlow.run_local_server 的 host／port／timeout_seconds／kwargs 簽章；真正 loopback／consent 尚未實測。
SDK import 出現系統 grpcio 未來版本支援的 FutureWarning，不影響本次 request 建構；正式環境仍待 002 鎖檔安裝驗證，不以此暫存環境取代共同基準。

### 圖表與剩餘接線

Class 新增 ImportBundle／Fingerprints，Component 標示 CLI-only consent，Sequence 修正恢復先讀目前結構與重新辨識錨點；三張 PlantUML CLI 渲染退出碼 0、同目錄 PNG 更新。AI 檢視 Class／Component 圖面，新增圖意待組員審查；命令見 render-report。
本輪可獨立測試的領域切片已就緒，但**不是整個 001 完成**。剩餘包括：

1. 002 的正式套件環境、app factory、teacher context、DB；001 接 ownership／CSRF、來源及活動授權。
2. ImportPreview 持久化、並行確認只發布一次、不可變 catalog、get_catalog、版本與來源歸屬約束。
3. export preview／operation／attempt／source lease／idempotency／verified_at、重啟恢復與執行期限；production driver 按介面文件先檢查後寫入並保存報告。
4. 003 的 CLOSED 且已結算可信 snapshot，結果未就緒必須拒絕，不能由純 DTO 檢查替代。
5. Flask CLI 註冊、routes／UI；真實 OAuth／完整 Sheets 中繼資料、可讀不可寫、外部競態、兩位組員完整人工驗收。
6. 全功能 analyze／converge 與 PR 互審仍待接線及收尾階段，本次不宣稱已通過完整交付門檻。

## 2026-11-24：整合 PR #4 與真實雲端唯讀驗證

使用者回報 PR #4 已合併。已核對 origin/master=c428ba0 包含 ef660ee 三項審查修正，於 codex/001-guided-notes-implementation 合併 master，無衝突且保留 001／002 兩邊程式。沒有推送或自動合併新的 GitHub PR。

### 正式環境

沿用 002 的 Python 3.13／src layout／Flask app／教師授權／DB／CSRF，Google 四個直接依賴加入同一 pyproject／uv.lock，不建立另一套 app 或 DB。uv lock 與 uv sync --locked 實際成功，解析 39 套件；Python 3.13.1 的正式 .venv 可 import Flask／Google SDK。共用 CSRF 已審查並在 001 介面記錄，因此不再另裝原建議 Flask-WTF。
初次離線解析因快取不完整失敗，經工具核准後連線解析／安裝成功；不將離線失敗誤列為套件不相容。

### 測試

執行者 Codex，本機正式 .venv：

| 指令 | 實際 |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -q` | **89 passed、98 subtests passed，15.85 秒，退出碼 0** |
| `node tests/activity-sync.test.cjs` | Stale phase response: passed |
| 正式環境 import smoke | Formal environment imports OK |

新增 tests/unit/test_inspect_cli.py 三項測試：唯讀且不輸出題目／原值、缺 gid 先拒絕、無效 URL 先拒絕；mock gateway 僅呼叫 read_sheet，沒有 write_unit。

### 真實 Google Sheets 讀取

使用者已授權，並在本對話提供兩份講義副本，明確同意先只讀取。透過私人目錄中的既有 credentials／token，直接以官方 Sheets API 讀取 GridData／merges；未呼叫任何寫入方法，未下載 .xlsx。
沙箱初次回 GOOGLE_REAUTH_REQUIRED，允許連線後使用既有授權成功，未要求使用者重登。沒有輸出、記錄或提交 token／client JSON 內容，也不在本文件保存私人副本的 spreadsheetId 或問題／答案原文。

| 來源 | 認得主題號 | 作答格 | 結構與錨點（A1） |
| --- | --- | --- | --- |
| 使用者提供第一份：題組副本 | 4 | 6 | 題號1：H5、H6；題號2：H8、H9；題號3：G11；題號4：G13 |
| 使用者提供第二份：單題副本 | 6 | 6 | G5、G7、G9、G11、G13、G15 |

同一結果再由正式環境的新 `inspect-sheet --url ...` 唯讀指令重現；輸出 read_only=true，兩次退出碼均為 0。API 回傳的 merges 數分別 13、21，解析成功。此處是 AI 的來源讀取／辨識證據，未作答、未回填，尚未由兩位組員完成網頁預覽／確認／活動人工驗收。

### 下一段接線

新增完成 T002，累計 11／59。其餘任務未因合併或讀取成功而自動勾選。
001 將以 notes_ 表名前綴接入同一 DB，避免與 002 questions 表衝突；沿用共用登入與 CSRF，實作持久化預覽／確認發布／get_catalog，再接教師頁面。需要的共用骨架已可用，不再將它列為阻塞；production 回填仍待 source lease／idempotency／可信結算 provider 與人工驗收。
目前三圖的 Source Access 責任已涵蓋此唯讀診斷，沒有變更作答或寫入流程，不需為 CLI 額外新增圖；完整程式／圖意核對仍依 T056 執行。

## 2026-11-24：US1 匯入網頁、持久化與活動接線

### 範圍與前置

使用者要求繼續實作。沿用 codex/001-guided-notes-implementation，基準 d4011ad，依 speckit-implement 推進 Foundation 與 US1。check-prerequisites 指向 001，requirements.md 16／16，未修改該檢查表。前後沒有 extensions.yml，無 hooks。
本輪完成可操作的匯入增量；production 回填、來源鎖、作業／重啟恢復與人工完整驗收不在完成宣告中。

### 實作

- 共用 app 註冊 notes Blueprint，沿用 002 教師登入／session／CSRF。設定採 GUIDED_NOTES_SECRET_KEY／GUIDED_NOTES_DATABASE；新增 NOTES_GOOGLE_TEACHER_ID，單一 Google profile 僅允許指定教師使用，其他教師在載入憑證／連 Google 前即拒絕。
- 同一 SQLite 連線使用 autocommit=True、顯式 BEGIN IMMEDIATE／SQL COMMIT／ROLLBACK、foreign_keys=ON 與有限 busy_timeout。init-db 只 CREATE IF NOT EXISTS，重跑及重啟不清空既有教師／活動／catalog。Google 網路期間無 DB 寫交易，測試 gateway 對此斷言。
- notes/schema.sql／repository.py：notes_sources、notes_imports、notes_catalogs、notes_questions、notes_answer_items、notes_blanks、notes_source_bindings、notes_import_previews。來源歸屬有 teacher FK，版本有複合主鍵，小題／blank／位置有唯一與 FK 約束；confirmed catalog 禁止 UPDATE／DELETE。
- import_service：保存 server-owned preview，確認時重新讀取與核對三種 hash，再進短交易重查授權／狀態、分配版本、保存 catalog／bindings 並標 confirmed。同一預覽重送與競爭回同一版本；兩個新預覽更新同一 import 會各自取得下一版。來源改動時使舊預覽失效，回新預覽連結，需重新確認。來源改名保留 numeric sheetId 並更新顯示名稱。
- 真實 get_catalog 已接入 002；固定版本 DTO 排除來源位置與題目原文。他人／未知版本 404，舊活動仍讀原 catalog。
- 教師 HTML／JSON 匯入路由、來源錯誤定位、A1 答案範圍、來源與保存版本清單、catalog 建立活動入口。HTML 使用 Jinja escaping／隱藏 CSRF，動態回應用 textContent；日期存 UTC，UI 台北時間。
- authorize-sheets 已註冊到共用 Flask CLI；init-teacher 顯示新教師 ID，供綁定 profile，不輸出密碼。notes assets 是公開程式碼，所有來源／清單操作須教師授權。

### 自動驗證

執行者 Codex，正式 Python 3.13.1 .venv。新測試先出現預期 404；接線期間修正 CLI 例外區塊位置造成的 SyntaxError，並將 unit/test_google_authorization.py 更名為 test_google_authorization_core.py，避免與 integration 同名測試的 pytest collection 衝突。修正後完整重驗：

| 指令／情境 | 實際 |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -q` | **109 passed、98 subtests passed，27.71 秒，退出碼 0** |
| `node tests/notes-ui.test.cjs` | activity handoff 與失敗後恢復按鈕通過 |
| `node tests/activity-sync.test.cjs` | 舊 phase 回應不覆蓋新狀態通過 |
| `git diff --check` | 通過，僅既有換行格式提示 |

另以暫存 DB、隨機 session secret 執行 Flask CLI help／init-db，成功列出 authorize-sheets／init-db／init-teacher 並初始化，無清空既有資料。未設定 secret 時 app 明確拒絕啟動，符合 fail-closed 設定。瀏覽器未登入直接進匯入頁時回 401 HTML 與教師登入導覽；API 則保留 nested JSON error。

涵蓋未登入／學生／其他教師拒絕、缺 CSRF、profile 不符、來源權限不足、無效 URL／gid、缺表頭、XSS escaping、HTML 表單與 redirects、原值／位置變動、改名、重送、並行確認只發布一次、並行新增版本、確認期間授權失效、舊活動固定版本、重啟保存與 immutable catalog。Google token／路徑不進 session 或錯誤回應。

### 真實雲端副本經 HTTP 路由驗證

以暫存本機 DB 與暫存教師，使用既有私人 token 經真實 gateway 執行列工作表 → 建預覽 → GET 預覽 HTML → 確認 → 重送確認 → get_catalog → 建立活動。沒有對雲端工作表寫入；本機測試資料放忽略的 tmp，沒有建立使用者的正式教師帳號或設定其密碼。

| 副本 | 題數／格數 | 預覽 HTML | 保存／重送 | 活動 |
| --- | --- | --- | --- | --- |
| 題組副本 | 4／6 | 200 | 第 1 版，重送同版本 | 201，state 題數一致 |
| 單題副本 | 6／6 | 200 | 第 1 版，重送同版本 | 201，state 題數一致 |

### 圖表、限制與任務

Class 新增 ImportPreview、來源擁有者與發布關係；Sequence 補 server-owned ready preview、確認重讀、短交易發布及重送回原版本。PlantUML CLI 渲染三圖退出碼 0，同目錄 PNG 已同步。Source Access、Import／Catalog／Store 與實作位置對照見 plan／render-report。
瀏覽器預覽工具開啟 127.0.0.1:5011 的暫存測試站時連線逾時，未完成瀏覽器外觀操作檢查；HTML 表單流程由 Flask test client 驗證。已停止暫存站，新畫面／圖意與完整人工驗收仍待組員。

新增完成 T006–T013、T016、T019–T024，累計 **26／59**。T001 本輪互審、T004 後續回填測試 provider、T025 完整人工驗收及 US2／US3 production 作業保留未完成。完整 analyze／converge 及最終 PR 交付檢查仍待收尾階段，不宣稱整個 001 完成。
使用者可依 quickstart 的 CMD 指令建立自己的教師、綁 Google profile，再由 /teacher 登入並點講義匯入；不需再等待 002 骨架。

## 2026-11-24：使用者回報的人工匯入驗收

執行者：本對話使用者，具名姓名／GitHub 帳號尚未提供。測試版本依本對話操作順序為 e924ac0 的匯入增量，未另外取得使用者當時 HEAD；以下為使用者回報，非 AI 觀察畫面。

| 操作 | 預期 | 使用者回報 |
| --- | --- | --- |
| 教師登入、讀取副本、預覽、確認匯入、建立活動 | 保存講義版本並顯示活動碼 | 已操作到活動碼出現 |
| 重新整理並回到講義匯入頁 | 剛才保存的版本仍存在 | 測試成功 |
| 建立預覽後修改雲端副本，再按確認 | 舊預覽不可直接確認，要求檢查新預覽 | 測試成功 |

尚未回報本次使用的是單題／題組哪份副本、是否兩份皆測、題數與逐格對應核對、第二位組員操作或瀏覽器截圖。因此不將 T025／T054 或 SC-005 全部勾選；M06 的匯入確認前來源改動子情境有回報證據，回填前變動與回填恢復仍未驗收。

## 2026-11-24：講義顯示名稱與多分頁匯入行為

使用者明確同意「沿用分頁名稱／自訂系統講義名稱」及「一次一個分頁，各自匯入」方案。沿用原分支及 e924ac0 基準，保留前段使用者人工回報。共同需求 D12 記錄 SpecKit 使用者已確認、OpenSpec 組同步仍待確認，未更動既有共同決策。

### 實作與資料安全

- 選表頁預設 source 模式，可切 custom 並輸入 1–100 個字元；前後空白移除、空白／超長／控制字元拒絕，驗證在 Google gateway 建構／讀取前完成。沒有 JavaScript 仍可提交選擇，由後端驗證。
- notes_preview_names／notes_catalog_names 只保存教師顯示 metadata，來源表仍保留原 Google 分頁名稱，CatalogDTO／UUID／來源 sheetId／答案位置／語意指紋不改。每個版本保留自訂名稱，新版本可另取名稱；沿用模式使用最近讀取的來源名稱快取。
- 命名選擇保存在 server preview，確認請求不可改名；來源變動的新 preview 保留原選擇。清單、預覽與保存頁顯示有效講義名稱及原始來源分頁，保存頁來源連結仍指向原分頁。HTML 全程 escaping。
- DB 初始化只新增附屬表及缺漏的 source-mode 記錄（ON CONFLICT DO NOTHING），不清空或改寫既有 immutable catalog。重啟不覆蓋已保存 custom 名稱。
- 多分頁顯示於選單，每次只對所選 numeric sheetId 讀取／確認。同名講義不會合併來源，也不能將不同分頁／試算表寫成既有 import 的新版本。沒有新增多選批次功能，沒有任何 Google 重命名或寫入呼叫。

### 驗證

執行者 Codex，正式 .venv（Python 3.13.1）。先建立新整合測試，因既有 preview 沒有 source_title 而出現預期 KeyError；實作後通過。

| 指令 | 結果 |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -q` | **118 passed、98 subtests passed，29.41 秒，退出碼 0** |
| `node tests/notes-ui.test.cjs` | 名稱選項切換／required／disabled，以及既有活動交接與失敗恢復通過 |
| `node tests/activity-sync.test.cjs` | 通過 |
| `git diff --check` | 通過，僅既有換行格式提示 |

新增九個整合測試涵蓋 source 預設、custom trim／保存、來源變動／刷新、不同版本名稱、確認時不可改名、非法名稱、XSS、兩分頁獨立來源／題數／讀取次數、舊 DB 升級、重啟保留、跨來源更新拒絕，以及無 JS 的 HTML 表單。
遷移測試只操作 pytest 暫存 DB：移除新名稱表模擬舊版本，再重啟 app，確認原 DTO 完全相同、舊 ready preview 可繼續確認。未修改使用者的正式 DB 或雲端副本；正式 DB 會在使用者重啟服務時執行同一保留資料初始化。

Class 補 LectureDisplayName metadata；Component／Sequence 補一次一分頁與命名選擇保存。PlantUML CLI 重渲染三張 PNG，退出碼 0；新的命名畫面與圖意待組員人工審查。本輪未重試先前無法連線的瀏覽器工具，不宣稱已完成人工外觀驗收。
新增 T060–T062 三項已完成，總計 29／62（原核心 26／59）。完整勝組回填、操作恢復、跨模組與人工驗收待辦維持原狀態。
