# Google Sheets 授權準備與本機設定

> 2026-11-25：目前 Web 已改用 007 的教師 Google 登入與本人 Sheets 連接，請先依 [007 設定指南](../specs/007-google-teacher-login/quickstart.md)建立 **Web application client** 與 repo 外加密 key。原 Desktop client/token 不可混用，也不必刪除。以下 Desktop 步驟保留給獨立 CLI／歷史驗證，不能用來授權 007 Web。

本文件對應 001 T005／T019。2026-11-23 已完成獨立 OAuth helper／CLI、準備說明及模擬測試，**尚未操作任何實際 Google 帳號或來源**。
Google 授權是讓後端存取講義，與 002 的教師登入分開。

## 教師現在可以準備的項目

1. 用將來讀寫講義的 Google 帳號建立或選用 Google Cloud project，啟用 Google Sheets API。
2. 設定 Google Auth Platform 的應用資訊與使用對象。若專案為 External／Testing，把實際操作帳號加入測試使用者。
3. 建立 OAuth client，應用程式類型選 **Desktop app**。下載 client JSON；不要使用網頁應用的 client 取代。
4. 把 client JSON 放在 repository 外的私人目錄。token 路徑也必須在 repo 外；token 在後續教師執行本機授權後才產生，不要手工填寫 token。
5. 複製課程的單題與題組範本，確認操作帳號能編輯副本；再準備欄列移動、答案區變寬的另一份副本。程式目前尚未驗證真實內容，先不要在原範本測寫。

授權流程採 Desktop loopback，使用 `https://www.googleapis.com/auth/spreadsheets` scope，需同時讀寫。Google quickstart 的唯讀範例 scope 不能直接拿來執行回填。
依據：[官方 Python quickstart](https://developers.google.com/workspace/sheets/api/quickstart/python)、[Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app)。

## 環境變數

以下為路徑範例，請依實際私人目錄設定。設定路徑不代表已取得授權。

```powershell
$env:NOTES_GOOGLE_CLIENT_SECRETS = 'C:\your-private-folder\guided-notes\client.json'
$env:NOTES_GOOGLE_TOKEN = 'C:\your-private-folder\guided-notes\token.json'
Test-Path -LiteralPath $env:NOTES_GOOGLE_CLIENT_SECRETS
```

client JSON、token 內容不可放入程式、session cookie、截圖、PR、日誌或 AI 對話。`.gitignore` 已排除常見憑證檔名、`.env`、`secrets/`；不論檔名為何，都應維持在 repo 外。
本機資料庫與套件快取亦已排除。

## 不等共用骨架即可使用的獨立 CLI

`notes/cli.py` 已提供 `check-config` 與 `authorize-sheets`；不需 Flask 或 DB。`check-config` 只檢查路徑與 Desktop JSON，不連網、不寫 token、不開瀏覽器。

在 CMD 設定以下路徑（請先換成真實、repo 外的私人目錄）：

```bat
cd /d D:\os_final
set "PYTHONPATH=D:\os_final\src"
set "NOTES_GOOGLE_CLIENT_SECRETS=C:\your-private-folder\guided-notes\client.json"
set "NOTES_GOOGLE_TOKEN=C:\your-private-folder\guided-notes\token.json"
"C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe" -m guided_notes.notes.cli check-config
```

在本次開發機，官方套件已另裝至被忽略的 `tmp/sdk-smoke` 供相容性驗證。要實際授權，可明確執行以下命令；這會開 Google 同意畫面，完成後才寫 repo 外 token：

```bat
set "PYTHONPATH=D:\os_final\src;D:\os_final\tmp\sdk-smoke"
"C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe" -m guided_notes.notes.cli authorize-sheets
```

此暫存環境不是團隊的正式安裝方式；其他電腦應使用 002 建立的鎖定依賴。尚未使用真實帳號執行授權或讀寫，不能將設定成功視為 Sheets 驗收。
helper 一般模式只載入／更新既有 token，失效會回 GOOGLE_REAUTH_REQUIRED；只有明確 CLI 的 interactive 模式可開啟登入。新 token 以同目錄暫存檔再原子替換，保存失敗不覆寫舊 token；Windows 私人目錄存取權仍由使用者帳號／ACL 管理。

## 等共用骨架完成後的接線

1. 002 先建立共用 `pyproject.toml`／`uv.lock`、Flask app、教師登入與 DB。套件範圍依 001 research.md，包含 Google 官方 client 與 OAuth libraries。
2. 001 將已完成的 `authorize()` helper 註冊到 Flask `authorize-sheets` CLI：路徑解析、repo 外及不同檔案檢查、loopback 與原子保存已實作。正常 HTTP 請求不得彈出 Google 登入視窗。
3. 明確在網路作業開始前載入／更新憑證，再將 credentials 傳入 `build_google_service()`，交給 `SheetsGateway`。token 失效或 `invalid_grant` 時，提示教師重新執行 CLI，不直接印出 Google 原始錯誤。
4. 註冊 Flask CLI 後才可執行 quickstart 中的 `flask ... authorize-sheets` 命令。目前可用的是上方獨立 CLI；Flask 註冊尚未完成。
5. 分別測試讀取副本、回填副本、可讀不可寫與撤銷授權。以回讀 `userEnteredValue.stringValue` 確認文字；HTTP 成功回應本身不算回填完成。

## 當前可用與待處理

### 2026-11-24 正式環境與唯讀雲端驗證

PR #4 的共用骨架已整合，Google 套件已納入正式 pyproject／uv.lock，現在直接用 `.venv`，不再依賴 `tmp/sdk-smoke`。
使用者已完成 OAuth 授權。兩份副本已以 Google Sheets API 直接讀取並動態辨識：題組副本 4 題／6 格（兩題各兩小題及兩個單題），單題副本 6 題／6 格。
這是讀取及辨識驗證，沒有回填，也不代表完整人工驗收。

在 CMD 可重跑以下指令（將連結換成自己的副本；兩個憑證環境變數沿用前述私人路徑）：

```bat
cd /d D:\os_final
set "NOTES_GOOGLE_CLIENT_SECRETS=C:\Users\user\guided-notes-private\client.json"
set "NOTES_GOOGLE_TOKEN=C:\Users\user\guided-notes-private\token.json"
.venv\Scripts\python.exe -m guided_notes.notes.cli inspect-sheet --url "你的Google-Sheets連結"
```

連結需含 gid，或另加 `--sheet-id 數字`。指令僅讀取、輸出題號／題數／格數與零起算錨點，不輸出題目敘述、原答案或憑證，不執行寫入。API 受限或憑證失效時回安全錯誤代碼；不自動開啟登入。
上方「尚待共用骨架」等敘述是前輪階段記錄，現在仍待接入的是 001 的 Flask CLI 註冊、網頁匯入、DB 發布與回填作業。

| 項目 | 狀態 |
| --- | --- |
| URL／gid 驗證、列工作表、numeric sheetId 讀取 | 已完成 mock 測試 |
| 同一主題號 RAW 單次批次與原始值回讀 | 已完成 mock 測試，尚未接確認／lease／作業流程 |
| 官方 client factory 的 timeout／錯誤保護 | 已完成模擬測試與 Python 3.13 暫存 SDK 安裝／請求建構 smoke，未送出 API |
| repo 外路徑、token 載入／更新、Desktop CLI | 已完成模擬測試；真實帳號授權未執行 |
| Google Cloud、測試帳號、client JSON、OAuth 同意 | 教師待設定／待實測 |
| 真實講義辨識、權限與回填 | 未執行 |

來源：[numeric sheetId 讀取](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/getByDataFilter)、[DataFilter 批次寫入](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdateByDataFilter)、[配額與退避](https://developers.google.com/workspace/sheets/api/limits)。

## 008 選檔與連結入口

教師登入後進課程的「講義管理」，按「＋匯入講義」。貼上Sheets連結沿用007本人讀寫授權，只有明確讀取時才要求；雲端入口另使用專用Picker Web client的openid/email/profile/drive.file窄授權，原main client與持久key保持。

新增環境變數 `GUIDED_NOTES_GOOGLE_PICKER_CLIENT_SECRETS` 指向repo外的專用Web client JSON、`GUIDED_NOTES_PICKER_API_KEY` 為受網站／API限制的瀏覽器key、`GUIDED_NOTES_PICKER_APP_ID` 為同project number。main與Picker client必須不同；缺設定只停用雲端入口，不阻擋貼連結。完整Cloud準備及scope smoke見 `specs/008-teacher-course-workspace/quickstart.md`。本輪未操作真實Google Console，不貼或提交任何憑證。

選檔後單選一張工作表，沿用或自訂名稱，全文預覽確認後保存。要換分頁／名稱按「重新選擇／修改名稱」；要換檔或入口則取消並另開流程。120秒讀取claim到期後可明確重試，30分鐘流程到期需重新開始。講義移除不刪雲端原檔，歷史回填由活動講義歷史入口繼續依原規則進行。
