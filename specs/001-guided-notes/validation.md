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
