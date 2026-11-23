# Implementation Plan: Guided Notes 匯入與回填

**Branch**: `001-guided-notes` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-guided-notes/spec.md`，涵蓋表頭與合併範圍辨識、單題／題組、預覽、文字回填及回讀恢復。

## Summary

採單一 Flask 本機服務、Jinja 頁面與少量 JavaScript，使用 Google 官方用戶端讀取儲存格及合併範圍。
每個主題號形成一個提交單位，題組保留有序小題識別。SQLite 保存不可變匯入版本、來源對應、預覽與回填紀錄。
回填只接收伺服器取得的已結束活動快照，每題組一個批次寫入請求，寫後回讀，未知結果先查明再恢復。

Q2、Q3 已於 2026-11-23 由使用者回報與 OpenSpec 組確認，確認者姓名尚未提供。
D03、D06 與 D09 活動重連採 002 分支已回報確認內容；D01、D02 排名細節、D04 自填組別與 D08 依共同需求保持待確認。
本功能只依相鄰模組提供的權限、已結束狀態與唯一勝組驗證，不代替它們決定提交次數或排序方式。

## Technical Context

**Language/Version**: 設計基準為 CPython 3.13.x、Windows x64。宿主 `python` 實測為 3.14.7，實作時用 uv 選定 3.13 建立專案環境。

**Primary Dependencies**: Flask 3.1、Jinja2 3.1、Flask-WTF 1.x、google-api-python-client 2.x、google-auth 2.x、google-auth-oauthlib 1.x、google-auth-httplib2 0.x。相容解析快照及選擇理由見 [research.md](research.md)。

**Storage**: Python 標準庫 sqlite3，單一本機資料庫 `instance/app.sqlite3`；Google 憑證與 token 放 repo 外，路徑由環境變數指定。

**Testing**: pytest、Flask test client、可注入的 Sheets gateway 與相鄰模組介面。真實 Sheets 副本由組員人工驗收。

**Target Platform**: Windows 本機，伺服器綁定 `127.0.0.1`，教師及至少兩組學生以獨立瀏覽器工作階段模擬。

**Project Type**: 單一 Python 網頁應用程式，001 為一個 Blueprint 及其領域服務，002／003 共用 app factory 與資料庫生命週期。

**Performance Goals**: 以規格 SC-001–SC-006 的正確性為交付門檻；規劃使用 100 個主題號、每題至多 10 個作答項目的合成資料作設計容量案例，這是測試目標，尚無效能實測承諾。Sheets 掃描依非空資料及合併範圍界定，較大資料分區讀取；批次寫入以題組為單位，避免每格一次網路請求。

**Constraints**: 圖表優先、來源座標動態取得、作答標號及合併保留、Google 寫入結果不得假報成功。外部編輯與本機交易無法形成跨系統原子交易，限制及處理見下文。

**Scale/Scope**: 單機單進程、單一教師 Google 帳號設定、每次匯入一張工作表。帳號登入及活動排序由相鄰功能實作；CSV 與講評留待其他功能。語意明確的更大資料可支援，容量目標不作任意拒收規則。

## Constitution Check

*規劃前與 Phase 1 設計後各做一次核對。下表是設計檢查，人工驗收與應用程式實作尚未完成。*

| 原則 | 規劃前檢查 | Phase 1 設計後檢查及證據 |
| --- | --- | --- |
| I 雙組協調 | Q1 已選定，Q2／Q3 使用者回報已共同確認 | 共同需求狀態已更新；其餘決策按整合後共同需求；目錄及清單／題組／結算契約已統一 |
| II 圖表優先 | 三份 .puml 及 PNG 已存在並成功渲染，AI 已檢視 | 模組映射、資料模型與時序一致；另補儲存及鎖定組件並重渲染，組員圖意審查留在本次設計 PR |
| III 動態辨識與回填 | spec FR-002、FR-013 支援合併範圍 | format contract 定義精確規則，測試移動欄列；Google gateway 僅寫答案錨點 |
| IV 憑證與可見範圍 | 所有操作需教師權限 | session 共用 adapter、CSRF、source ownership、repo 外 token；來源位置不流向學生端 |
| V AI 與人工驗證 | 規格有正常與失敗情境 | quickstart 映射單題、題組、競態與失敗驗證，執行狀態如實標示 |
| VI 文件一致 | 需求編號可追溯 | plan、模型、契約、圖表、驗收情境已核對；tasks/analyze/implement/converge 接續執行 |

本輪為設計草案。使用者回報同學已查看 001 圖表，並已同意四項整合介面；具體圖意結論與姓名仍待補。依憲章補齊審查紀錄並重新核對計畫後再實作，
實作完成後仍須依憲章逐項驗證。憲章 v1.0.0 內 D01–D10「待確認」文字屬初始狀態快照，
本次以共同需求最新逐項確認紀錄追溯；後續憲章維護可將該段改為引用決策表，避免狀態重複。

## Project Structure

### Documentation (this feature)

```text
specs/001-guided-notes/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── render-report.md
├── checklists/requirements.md
└── contracts/
    ├── format.md
    ├── interfaces.md
    └── examples.json
```

`tasks.md` 由下一階段 `$speckit-tasks` 產生。以下原始碼樹為實作時的目標配置，本輪僅產生設計文件。

### Source Code (repository root)

```text
pyproject.toml
uv.lock
src/guided_notes/
├── __init__.py              # app factory，兩人共同對齊後由一人建立
├── db.py                    # 每 request 連線與短交易
├── auth.py                  # 002 提供 require_teacher 與身分／權限
├── activities/              # 002／003，讀取 catalog、提供 ended snapshot
└── notes/
    ├── routes.py            # 教師 HTTP 與頁面、CSRF
    ├── models.py            # 對應概念類別、驗證 DTO
    ├── recognition.py       # 純解析，GridData + merges → catalog candidates
    ├── import_service.py    # 匯入預覽、確認、不可變版本
    ├── export_service.py    # 結果驗證、預覽、重檢、回填及恢復
    ├── repository.py        # 版本、預覽、報告、來源租約
    ├── sheets_gateway.py    # 唯一 Google API 邊界
    ├── cli.py               # authorize-sheets
    ├── templates/notes/     # import、preview、report 頁面
    └── static/notes.js      # 選表與確認，不持有憑證
tests/
├── unit/                  # 辨識、快照驗證、狀態與恢復
├── integration/           # Flask 權限、SQLite claim、gateway 受控失敗
├── contract/              # 固定 examples 與 002／003 契約
└── fixtures/              # 合成 Sheets 回應，涵蓋 merges
```

**Structure Decision**: 同一 app factory 及資料庫，Google 依賴集中在 gateway。
JSON 資料交換經領域驗證函式，無需額外服務或訊息系統。001 與 002／003 使用 [interfaces.md](contracts/interfaces.md) 的函式邊界，避免跨模組直接查寫各自資料表。

## Phase 0 Research

已完成 [research.md](research.md) 中的套件、授權、合併讀取、原子性、重試、儲存與權限決策。
2026-11-23 已用 uv 0.13.1 為 Python 3.13／Windows x64 成功解析 40 個套件。
依賴尚未安裝到應用環境，實際匯入 smoke test、Google 登入與讀寫列為實作驗證。
技術不確定性已有明確設計選擇；範本完整資料與帳號設定屬待實測項目。

## Phase 1 Design

### 圖表與模組映射

| 圖中組件／類別 | 設計落點 | 主要需求 |
| --- | --- | --- |
| Teacher Workspace、Teacher Authorization | notes/routes.py、002 auth adapter、Jinja | FR-001、FR-008、FR-012 |
| Import and Recognition | recognition.py、import_service.py | FR-002–FR-005、FR-013–FR-014 |
| Confirmed Catalog and Source Bindings | models.py、repository.py、SQLite | FR-005、FR-006 |
| Export Preview, Write-back and Read-back Recovery | export_service.py、逐項狀態 | FR-007–FR-011、FR-015 |
| Source Access | sheets_gateway.py、官方 Google client | FR-010、FR-012–FR-013 |
| MainQuestion → AnswerItem → Blank → SourceBinding | data-model 的主題號、小題、答案錨點 | FR-013–FR-014 |
| Activity、Result Module | trusted provider 的已結束且不可變快照 | FR-006–FR-007 |
| Operation Repository and Source Lease | repository.py、條件更新、唯一約束 | FR-011、FR-015 |

### 匯入資料流

教師通過授權後貼標準 Sheets URL，僅抽取 spreadsheetId 及可選 gid，不對任意 URL 發請求。
Google gateway 先列工作表，以 numeric sheetId 識別。讀取選表的 GridData、merges、實際值、公式及格式資訊。
辨識依 [format.md](contracts/format.md) 產生候選及定位錯誤，UI 展示題數、小題數、對應範圍。
確認匯入時重新讀取相關來源；預覽後變動則重建預覽。成功後建立不可變 catalog 版本與伺服器端 bindings，
只將無來源位置的 catalog DTO 交活動模組。新版本不修改舊活動。

### 回填資料流與安全恢復

1. 從 server-side provider 依 activity_id 取得 ended snapshot，驗證 teacher ownership、活動已結束且結算完成、catalog 版本、完整主題號集合、唯一勝組及完整小題答案。瀏覽器不能提交勝組快照來取代 provider。
2. 重讀來源，依主題號／小題識別匹配，題目內容與成員須與原 catalog 相符。只有座標變動可重建 bindings。題意、主題號或小題集合改變回報 SOURCE_STRUCTURE_CHANGED，要求重新匯入並由活動端明確核對版本。
3. 預覽保存原值、目標、答案與結構／內容指紋、結果版本，呈現覆寫差異。無勝組記 skipped。
4. 確認以短 SQLite 交易取得來源 write lease，綁定 teacher、source、preview 及 idempotency key，立即提交交易。再重檢授權、ended state、結果版本與來源，失效時不寫入並回傳新預覽要求。
5. 同一題組所有待寫答案，以單次 values.batchUpdateByDataFilter、numeric sheetId 的單格 GridRange、RAW 字串寫入。單題亦相同。一個題組不可拆成多個小題請求。
6. 每個成功、逾時或不確定請求都安排回讀，以 userEnteredValue.stringValue 與預定文字核對。成功寫入後 read-back 失敗仍為 unknown。已知無效請求為 failed，尚未送出的單位為 not_processed。
7. 重試先回讀原 operation 的目標，保持原 catalog 及 result_version。相同字串為 verified；原值未變可預覽確認後補寫；第三種內容為 conflict，需明確確認覆寫。無勝組仍 skipped。
8. 題組所有應寫小題 verified 才完成；整體所有應寫項目 verified 且其餘 skipped 才完成。Google 失敗不回滾已成功的其他題組，教師可查看逐項報告。

### 本機一致性與外部編輯限制

SQLite 使用 `autocommit=True`、顯式 `BEGIN IMMEDIATE`／SQL COMMIT／ROLLBACK、foreign_keys=ON 及有限 busy_timeout。
本機授權與狀態更新是短交易，網路等待不持有寫鎖。唯一 idempotency key 及 `(spreadsheet_id, sheet_id)` 來源租約防止本 app 同時回填。
租約有 owner token、到期時間與條件續期；網路 timeout 小於租約期限。執行者失去租約後停止後續寫入。
單機單進程，重啟後將未完成 writing operation 轉 recovering，回讀前次結果後才重新寫；不依過期租約直接重送。

Google 單一有效 batch request 原子套用，同次無效請求不會只寫半個題組。
部分完成主要來自多題組多次 request、已存在的完成格，或逾時後無法立即查證。
讀取、比對、寫入並非 Sheets 的條件式原子操作，外部編輯可能插在重檢與寫入間。
本機 lease 只序列化本 app；回讀證明的是回讀當下。畫面提示回填期間暫停編輯來源，
偵測到衝突停止並重新確認，不宣稱能排除所有外部競態，也不自動回滾而覆蓋他人新內容。

### 授權與錯誤處理

採教師預先執行 Desktop OAuth CLI，scope `https://www.googleapis.com/auth/spreadsheets`。
授權 loopback port 與應用 server 分開，Google token 放 repo 外，以教師設定識別對應；目前只支援本機單教師帳號。
Flask session 只存教師身分參照，token 留在 server；所有 teacher route 經 require_teacher、source ownership 與 CSRF。
Cookie HttpOnly、SameSite=Lax，本機 HTTP 不強制 Secure cookie；Jinja 保留 escaping。
來源 403、授權失效、讀取失敗、格式歧義及結果版本衝突分開回報，細節見契約。
讀取遇 429／暫時性 5xx 可有限指數退避加 jitter，寫入 timeout／5xx 先回讀並再次檢查，權限及格式錯誤不盲重試。

### 驗證與交接

驗證清單及可執行入口見 [quickstart.md](quickstart.md)。單元測試用合成 GridData 與 merges，
整合測試用受控 gateway、實際 SQLite 暫存檔與 Flask test client；真實 Sheets 副本逐格人工核對。
以 [examples.json](contracts/examples.json) 作兩位組員共同的契約樣本，對齊 app factory、auth adapter、DTO、錯誤 envelope 及 result provider。
001 的回填只能在 002／003 接上可信 snapshot 後走完整活動；離線測試可注入 provider，不開放學生或瀏覽器注入勝組。

## Complexity Tracking

本輪設計沒有需豁免的憲章違反。保留單體程式與標準庫 SQLite；source lease、不可變快照及逐項狀態用於跨系統失敗恢復，具有 FR-005、FR-011、FR-015 的明確依據。
