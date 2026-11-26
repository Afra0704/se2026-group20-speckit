# 007 設定與驗收指南

**007 已完成自動驗證範圍的實作，真人 Google 往返與兩組學生驗收尚未執行。** 使用 007 新 DB；保留 005/006 的程式與原人工任務狀態。實測結果見 [validation.md](validation.md)。本輪沒有操作 Cloud 或讀取個人憑證，下面的 Web client／key 設定需要操作者準備。

## 1. Google Cloud 準備

可沿用原 My First Project，但另建一個 **OAuth client ID → Web application**。不要覆蓋原 Desktop client.json/token.json，不把 installed JSON 改欄名充當 Web client。官方說明：[Web server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server)。

1. 確認該專案已啟用 Google Sheets API；這輪不需新增 Drive API／API key／Picker。
2. Google Auth Platform 設定應用名稱、支援信箱及開發者聯絡方式；依帳號選可用 audience。本機外部測試用 Testing，加入兩位實際測試教師的 Google 帳號。
3. 登入要求 openid/email/profile；老師連接講義時才要求 `https://www.googleapis.com/auth/spreadsheets`，於 Data Access／consent 設定相應權限。[Sheets scope](https://developers.google.com/workspace/sheets/api/scopes)。
4. Web client 精確登錄 Authorized redirect URI：

   ```text
   http://127.0.0.1:5000/auth/google/callback
   ```

5. 本案用 server redirect，不靠 Google JS popup，因此不需為本方案額外設定 JS origins。整個本機測試固定使用 127.0.0.1；本版設定驗證只接受上列 127.0.0.1 callback；localhost 或其他埠暫不支援，不要混用。
6. 下載新的 Web client JSON，建議存為 `C:\Users\user\guided-notes-private\web-client.json`。內容是機敏資料，不貼到對話、不提交。

Google Testing app 加入 Sheets 等非純登入 scope 時，refresh token 可能有 7 日期限；驗收前確認需要時重連。不要把純 openid/email/profile 的例外套到 Sheets 授權。[Google expiration](https://developers.google.com/identity/protocols/oauth2#expiration)。公開發布所需的敏感 scope 驗證另依 Google 規範處理，不在本輪本機驗收範圍。

## 2. 本機私有設定（由操作者準備）

在新的 CMD 設定：

```bat
cd /d D:\os_final
uv sync --locked
set "PYTHONPATH="
set "GUIDED_NOTES_CLASSROOM_MODE=1"
set "GUIDED_NOTES_DATABASE=D:\os_final\instance\classroom-007.sqlite3"
set "GUIDED_NOTES_PUBLIC_ORIGIN=http://127.0.0.1:5000"
set "GUIDED_NOTES_GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/google/callback"
set "GUIDED_NOTES_GOOGLE_WEB_CLIENT_SECRETS=C:\Users\user\guided-notes-private\web-client.json"
set "GUIDED_NOTES_GOOGLE_TOKEN_KEY_FILE=C:\Users\user\guided-notes-private\web-token.key"
set "GUIDED_NOTES_HTTPS=0"
set "FLASK_DEBUG=0"
```

另外設定穩定的本機 `GUIDED_NOTES_SECRET_KEY`，沿用原本的私有隨機值即可；不要使用範例佔位值，也不要把值貼到回報。若本機尚未設定，可在 CMD 用以下方式只設定此視窗，不印出值：

```bat
for /f "delims=" %S in ('.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"') do @set "GUIDED_NOTES_SECRET_KEY=%S"
```

這個隨機值只存在目前 CMD；關閉視窗後重設會讓舊登入 cookie 失效，不影響 DB 中的課程或另存的 Fernet key。若已有穩定私有設定，不要覆換。正式 Google 模式是預設，不需設定 password 或示範旗標。

**只有第一次且 keyfile 不存在時**，可用以下指令產生私有加密 key；`xb` 防止覆蓋舊 key，不會印出內容：

```bat
.venv\Scripts\python.exe -c "from pathlib import Path; from cryptography.fernet import Fernet; p=Path(r'C:\Users\user\guided-notes-private\web-token.key'); p.parent.mkdir(parents=True, exist_ok=True); p.open('xb').write(Fernet.generate_key())"
```

若已存在就沿用；限制該私有目錄存取。這把 key 與 Flask SECRET_KEY 不同，遺失不能解密既存講義授權，不能自動重建掩蓋錯誤。

舊 NOTES_GOOGLE_* Desktop profile 可保留給獨立 CLI；007 Web 不得使用它當 fallback。Web client、keyfile 及 DB 請勿放入 Git。本次使用新的 007 DB，005 DB、憑證及線上講義保持原樣，不需要刪除舊檔。

## 3. 啟動

先在舊服務 CMD 按 Ctrl+C，再從目前工作樹啟動。不要重跑 init-teacher 建密碼教師：

```bat
.venv\Scripts\python.exe -m flask --app guided_notes:create_app init-db
.venv\Scripts\python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

初次使用 classroom-007.sqlite3 為空白；之後重跑 init-db 要保留本版資料及 instance UUID，不能每次清空。若誤選舊業務 DB，007 應拒絕啟動並提示改路徑，不自動遷移／刪檔。啟動時不開 debug，callback access log 需先具備 query 脫敏。

## 4. 真人驗收

老師 A/B 用不同瀏覽器 profile，學生甲/乙另用兩個獨立工作階段。測試先用講義副本，記錄日期、操作者、工作樹版本、預期／實際與去機敏證據。

| 操作 | 預期 |
| --- | --- |
| 開首頁 | 只有老師／學生入口。 |
| 學生選學生 | 課堂碼＋組別，不需要 Google。 |
| 老師 A 首次 Google 登入 | 新教師空白課程，沒有本系統密碼步驟。 |
| A 建課程、登出、再次登入 | 回同一教師，課程仍在。 |
| B 登入及直接開 A 連結 | B 有自己的空間，A 的資源被拒。 |
| 取消登入、返回、重試 | 清楚提示，原有效教師不被清掉。 |
| 同 browser 兩分頁先後登入 | 最後啟動流程有效，舊 callback 不覆蓋目前身分。 |
| 登入進行中先登出 | 回來的舊結果失效，不能重新授權。 |
| 教師登出但同 browser 有學生資格 | 教師需重新登入，學生加入／恢復仍有效。 |
| A 登入但未接 Sheets | 可管課程，講義操作提示連接。 |
| A 點連接卻選 B 的 Google | 拒絕錯帳號，不切換教師、不覆蓋 A 原連接。 |
| A 本人同意 Sheets | 可貼本人可存取連結、選分頁、預覽、確認保存。 |
| 授權失效／來源未共用 | 分別提示重連／來源權限，不誤稱登入失敗。 |
| 刷新暫時逾時 | 顯示可稍後重試，原連接不被誤標失效，也不自動重送回填。 |
| 建立活動，兩組加入／看題／開始／準備中結束 | 005/006 全文、單活動、整組提交、階段限制保留。 |

初輪真實 Google Sheets 先驗讀取及匯入；實際寫回副本仍需依原回填驗收記錄，不把 OAuth 登入成功視為回填成功。正式 003 未接入時仍可能 QUIZ_UNAVAILABLE／待結算，不能以假受理掩蓋。

## 5. 自動驗證

另開 CMD，fixture 使用臨時 DB，不讀個人私有檔；避免手動設定影響 fixture：

```bat
cd /d D:\os_final
set "GUIDED_NOTES_CLASSROOM_MODE="
set "GUIDED_NOTES_DATABASE="
set "GUIDED_NOTES_GOOGLE_WEB_CLIENT_SECRETS="
set "GUIDED_NOTES_GOOGLE_TOKEN_KEY_FILE="
.venv\Scripts\python.exe -m pytest tests -q
node --test tests/identity-ui.test.cjs tests/student-question-text.test.cjs tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs tests/activity-sync.test.cjs tests/notes-ui.test.cjs
```

必測兩教師唯一身分、錯 aud/iss/nonce/exp/簽章、state／browser／重放／並行、登出後晚到 cookie、停用、資料隔離、舊全域 profile 不讀、錯 key／密文搬移／不同 instance/client、refresh 缺漏／失效／scope 部分同意、refresh/reconnect CAS、callback 日誌無 code/state/token，以及原 DTO/context／回填回歸。

I1/I2 回歸另包含 `tests/unit/test_google_transport.py`：使用真正 AuthorizedHttp 搭受控 HTTP／時間與 spy，快照取得後過期時 HTTP=0、refresh=0；收到真實 401 時僅一次 HTTP、不刷新重送；寫入送出前失效歸類未送出，已成功或未知單元不 replay。refresh 以假時鐘驗 20 秒結果接受期限、30 秒 lease、token POST 最多一次、必要憑證 GET 最多一次、超時只釋放自己 lease、晚到結果不覆蓋新 connect。這些不需操作真實 token，也不以真網路等待來測時間邊界。

自動測試已實際執行，命令與計數見 validation.md；不把受控測試當作真人 Google 結果。Google Cloud／真實 OAuth、實際瀏覽器及自動替代端分開記錄。詳細介面見 [登入契約](contracts/authentication.md)、[Sheets 契約](contracts/sheets-authorization.md)及[資料模型](data-model.md)。
