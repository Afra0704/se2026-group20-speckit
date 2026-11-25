# Research: Guided Notes 匯入與回填

研究日期為 2026-11-23，對應 [plan.md](plan.md)。本輪依 speckit-plan 進行兩個唯讀研究子任務，
分別查核 Sheets／OAuth 及 Python 技術棧，主代理整合並實際解析相依套件。

## 證據分級

| 分類 | 本輪證據 |
| --- | --- |
| 截圖觀察 | 使用者提供兩份範本，作答表頭跨欄、答案格合併、題組主題號跨列、子題標號 (1)、(2) |
| 官方文件已查核 | Sheets GridData／merges、RAW、batch、quota、OAuth loopback、Flask／SQLite及依賴支援 |
| 本機已驗證 | Specify 指向 001；uv 0.13.1；宿主 Python 3.14.7；Java 24.0.1、PlantUML 1.2026.10 三類圖成功渲染；Python 3.13 Windows 依賴解析成功 |
| 設計選擇 | Python 3.13、Flask 單體、Desktop OAuth、numeric sheetId data-filter 寫入、每題組一 request、SQLite source lease |
| 待實測 | Python 3.13 環境安裝及 import smoke、兩份完整 Sheets GridData／merges、真實權限與回填、失敗恢復與效能 |

## R1 Python 與套件基準

**Decision** 採 Python 3.13.x、Flask 3.1、Jinja2 3.1、SQLite 標準庫、官方 Google client，Flask-WTF 統一 CSRF、pytest 驗證。

**Rationale** 符合本機單體需求、無需另建前端編譯服務，Google 用戶端集中處理授權及請求。Flask 支援 Python 3.9 以上，所選 Google 與 pytest 當前版本的 metadata 支援 3.13。Python sqlite3 來自標準庫。

**Alternatives considered** Python 3.14 是宿主已安裝版本，但以 3.13 作為團隊基準更便於對齊現有 Specify runtime。前後端分離會增加建置與部署交接成本，當前互動以表單、預覽與狀態輪詢即可完成。

已執行以下純解析驗證，退出碼 0，解析 40 個套件。輸入和完整結果放於被忽略的 `tmp/plan-research/`，解析不等於安裝或整合測試通過。

```powershell
uv pip compile D:/os_final/tmp/plan-research/requirements.in --python-version 3.13 --python-platform x86_64-pc-windows-msvc --cache-dir D:/os_final/tmp/uv-cache --output-file D:/os_final/tmp/plan-research/resolved.txt
```

| 直接使用的依賴 | 本輪解析版本 | 實作初始範圍 |
| --- | --- | --- |
| Flask | 3.1.3 | >=3.1.3,<3.2 |
| Jinja2（Flask 帶入） | 3.1.6 | >=3.1.6,<3.2 |
| Flask-WTF | 1.3.0 | >=1.3,<2 |
| google-api-python-client | 2.202.0 | >=2.202,<3 |
| google-auth | 2.63.1 | >=2.63.1,<3 |
| google-auth-oauthlib | 1.5.0 | >=1.5,<2 |
| google-auth-httplib2（Google client 帶入） | 0.4.4 | >=0.4.4,<1 |
| pytest | 9.2.0 | >=9.2,<10 |

實作建立 pyproject.toml、uv.lock 並提交，團隊使用 uv sync --locked。native 相依套件的 wheel 及實際 import 仍須在指定環境驗證。來源為 [Flask installation](https://flask.palletsprojects.com/en/stable/installation/)、[Flask metadata](https://pypi.org/project/Flask/)、[Flask-WTF](https://pypi.org/project/Flask-WTF/)、[Jinja2](https://pypi.org/project/Jinja2/)、[Google client](https://pypi.org/project/google-api-python-client/)、[google-auth](https://pypi.org/project/google-auth/)、[OAuth library](https://pypi.org/project/google-auth-oauthlib/)、[pytest](https://pypi.org/project/pytest/)、[uv sync](https://docs.astral.sh/uv/concepts/projects/sync/)。

## R2 合併範圍與辨識

**Decision** 用 spreadsheets.get 指定 sheets.properties、sheets.merges 及 GridData 的 rowData／cellData（含 userEnteredValue、formattedValue、userEnteredFormat、起始索引），保存 numeric sheetId。

**Rationale** 數值矩陣不能識別跨列題號與空白格的差別。GridRange 使用零起算、左閉右開，先將每個合併範圍正規化為 anchor 與 span，再依格式契約找主題號、小題及答案格。欄位遮罩須顯式列出 data；若指定 fields，不能只依 includeGridData 期待回傳值。

**Alternatives considered** values.get 或 CSV 只作值矩陣，缺少 merge 資訊，不足以支援這兩份截圖。手工逐格指定答案位置會失去動態版型能力。來源為 [spreadsheets.get](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/get)、[Sheet merges](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/sheets#Sheet)、[GridRange](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/other#GridRange)。

## R3 寫入錨點與單次請求原子性

**Decision** 用 values.batchUpdateByDataFilter，單格 gridRange 指定 numeric sheetId 與答案左上角錨點，valueInputOption=RAW、值一律字串；每個主題號的待寫答案放同一請求。

**Rationale** 以 numeric sheetId 避免工作表改名使 A1 sheet title 失效。RAW 保留等號與前導零的文字，僅寫錨點不更動格式與 merge。單一有效請求原子套用，已知無效請求不會只寫一半；逾時仍需回讀確認是否已完成。

**Alternatives considered** values.batchUpdate 搭重新取得的 A1 名稱也可行，但須處理引號跳脫及改名競態。updateCells 配 stringValue 亦可，但本功能採單一路徑方便驗收。來源為 [DataFilter write](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdateByDataFilter)、[RAW](https://developers.google.com/workspace/sheets/api/reference/rest/v4/ValueInputOption)、[batch guide](https://developers.google.com/workspace/sheets/api/guides/batch)。

## R4 外部編輯、quota 與重試

**Decision** 預覽記錄來源語意、座標與值，寫前重檢、寫後回讀；本 app 用 source lease 防止同源並行。讀取有限退避，寫入遇不確定結果先回讀。

**Rationale** Sheets batch 的原子性不涵蓋先前讀取，也無法鎖住外部協作者。回讀只證明當下觀察到的狀態，必須如實記錄 unknown/conflict。部分完成來自多次 request 或前次成功格，不假設單一無效 batch 部分套用。配額應以批次與適度重試控制，避免每格發請求。

**Alternatives considered** 對寫入直接套自動 retries 可能在來源改動後覆蓋內容。自動回滾可能覆蓋協作者後來的修改。來源為 [collaboration behavior](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate)、[usage limits](https://developers.google.com/workspace/sheets/api/limits)。

## R5 本機授權與角色

**Decision** 教師以 Desktop OAuth 的 loopback CLI 預先登入，scope 使用 spreadsheets 讀寫權限；後端 token 留 repo 外。Flask 的 teacher session 及 Google 授權分開驗證。

**Rationale** 老師貼自己可編輯的講義 URL 與帳號授權模式一致，loopback 適用 Windows。External／Testing 狀態的 Sheets refresh token 可能在七天後到期，需 invalid_grant 恢復流程，錄影前實際確認或重授權。

**Alternatives considered** Service Account 需每份 Sheet 分享給服務帳戶並管理金鑰。drive.file scope 需搭適當檔案選取／授權流程，不能假設貼任何 URL 即有權限。來源為 [Python quickstart](https://developers.google.com/workspace/sheets/api/quickstart/python)、[Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app)、[token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)、[service accounts](https://developers.google.com/identity/protocols/oauth2/service-account)。

## R6 SQLite 與瀏覽器操作

**Decision** sqlite3 使用每 request 連線、顯式短交易與唯一約束；app 的寫入 lease 在網路呼叫前取得並提交。Flask-WTF 驗證修改請求的 CSRF，teacher ownership 在後端檢查，Jinja 自動 escaping。

**Rationale** SQLite 無法和 Google 形成同一交易，作業紀錄及回讀用於恢復。Python 3.13 的 autocommit 模式須明確選定，顯式 BEGIN IMMEDIATE 使用 autocommit=True 配 SQL COMMIT／ROLLBACK，不和自動 BEGIN 混用。Cookie 只放身分參照，本機 HTTP Cookie 配置需可實際送出。

**Alternatives considered** 長時間持有寫交易等待 Google 會阻塞其他操作。每個模組各自建立登入與資料庫連線會使權限和交易規則難以一致。來源為 [Flask SQLite](https://flask.palletsprojects.com/en/stable/tutorial/database/)、[Python sqlite3](https://docs.python.org/3.13/library/sqlite3.html)、[SQLite transactions](https://www.sqlite.org/lang_transaction.html)、[Flask security](https://flask.palletsprojects.com/en/stable/web-security/)、[Flask-WTF CSRF](https://flask-wtf.readthedocs.io/en/1.2.x/csrf/)。

## 待實測事項的處理

### 2026-11-23 gateway 實作補充

列工作表仍採 spreadsheets.get 的 properties fields；實際讀取改採官方 `spreadsheets.getByDataFilter`，以 `gridRange.sheetId` 選來源，並顯式指定 GridData／merges fields。這避免先查名稱再用 A1 讀取期間，工作表改名造成定位失效；不改辨識契約。
讀取最多三次，只對 429／500／502／503／504 退避；寫入 execute(num_retries=0)。client factory 採 httplib2 30 秒 timeout，AuthorizedHttp 關閉自動 refresh 重播；憑證刷新須在作業開始前明確完成。
官方 API 與 Python 呼叫參數已查核，現階段僅通過替代 service／依賴測試，實際 SDK import smoke 與網路行為待共享鎖定環境驗證。
來源：[getByDataFilter](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/getByDataFilter)、[HttpRequest.execute](https://googleapis.github.io/google-api-python-client/docs/epy/googleapiclient.http.HttpRequest-class.html)、[AuthorizedHttp](https://googleapis.dev/python/google-auth-httplib2/latest/google_auth_httplib2.html)。

上述技術選擇已定義，沒有懸而未決的技術方案。實作前段需讀取真正 Sheet 副本、建立 Python 3.13 環境與授權；
若完整 merge 結構超出 format.md 的明確支援範圍，回報實際反例、更新規格與圖表，再依已確認行為修正設計。
另一位組員須審查共用 Flask shell、teacher context、catalog／snapshot 格式，屬介面交接及驗證工作。
