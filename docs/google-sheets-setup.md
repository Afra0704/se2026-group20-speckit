# Google Sheets 授權準備與本機設定

本文件對應 001 T005。2026-11-23 已完成準備說明及離線測試，**尚未操作任何實際 Google 帳號或來源**。
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

## 等共用骨架完成後的步驟（目前尚不能當成已可用指令）

1. 002 先建立共用 `pyproject.toml`／`uv.lock`、Flask app、教師登入與 DB。套件範圍依 001 research.md，包含 Google 官方 client 與 OAuth libraries。
2. 001 接入 `authorize-sheets` CLI：檢查兩條路徑解析後均在 repo 外、檔案不同，使用本機 loopback 取得同意並安全保存 token。正常 HTTP 請求不得彈出 Google 登入視窗。
3. 明確在網路作業開始前載入／更新憑證，再將 credentials 傳入 `build_google_service()`，交給 `SheetsGateway`。token 失效或 `invalid_grant` 時，提示教師重新執行 CLI，不直接印出 Google 原始錯誤。
4. 註冊 Flask CLI 後才可執行 quickstart 中的 `authorize-sheets` 命令。目前 **尚未提供此 CLI、憑證載入或 token 寫檔**。
5. 分別測試讀取副本、回填副本、可讀不可寫與撤銷授權。以回讀 `userEnteredValue.stringValue` 確認文字；HTTP 成功回應本身不算回填完成。

## 當前可用與待處理

| 項目 | 狀態 |
| --- | --- |
| URL／gid 驗證、列工作表、numeric sheetId 讀取 | 已完成 mock 測試 |
| 同一主題號 RAW 單次批次與原始值回讀 | 已完成 mock 測試，尚未接確認／lease／作業流程 |
| 官方 client factory 的 timeout／錯誤保護 | 已完成替代依賴測試；真實依賴安裝 smoke 待 002 |
| Google Cloud、測試帳號、client JSON、OAuth 同意 | 教師待設定／待實測 |
| 真實講義辨識、權限與回填 | 未執行 |

來源：[numeric sheetId 讀取](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/getByDataFilter)、[DataFilter 批次寫入](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdateByDataFilter)、[配額與退避](https://developers.google.com/workspace/sheets/api/limits)。
