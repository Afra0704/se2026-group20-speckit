# Google Sheets 授權準備與本機設定

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

| 項目 | 狀態 |
| --- | --- |
| URL／gid 驗證、列工作表、numeric sheetId 讀取 | 已完成 mock 測試 |
| 同一主題號 RAW 單次批次與原始值回讀 | 已完成 mock 測試，尚未接確認／lease／作業流程 |
| 官方 client factory 的 timeout／錯誤保護 | 已完成模擬測試與 Python 3.13 暫存 SDK 安裝／請求建構 smoke，未送出 API |
| repo 外路徑、token 載入／更新、Desktop CLI | 已完成模擬測試；真實帳號授權未執行 |
| Google Cloud、測試帳號、client JSON、OAuth 同意 | 教師待設定／待實測 |
| 真實講義辨識、權限與回填 | 未執行 |

來源：[numeric sheetId 讀取](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/getByDataFilter)、[DataFilter 批次寫入](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdateByDataFilter)、[配額與退避](https://developers.google.com/workspace/sheets/api/limits)。
