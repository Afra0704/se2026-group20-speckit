# Quickstart Validation Guide

此指南對應 [plan.md](plan.md)、[format.md](contracts/format.md) 及 [interfaces.md](contracts/interfaces.md)。
目前只有規格與設計文件，應用程式、CLI、pyproject.toml、uv.lock 及測試尚未建立。
下列「實作後」命令是 implement 階段必須提供並驗證的入口，不能將本指南當成已執行成功的紀錄。

## 現在可執行的文件檢查

從 repo 根目錄執行以下 PowerShell。

```powershell
Get-Content .specify/feature.json
.specify/scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
python -m json.tool specs/001-guided-notes/contracts/examples.json > $null
git diff --check
```

預期指向 specs/001-guided-notes，JSON 可解析，無 whitespace error。
圖表工具已存在於本機暫存目錄時，可用 render-report 中記錄的完整 Java 命令重渲染。

## 實作前準備

1. 兩位 SpecKit 組員審查共用 app shell、teacher auth 與 provider 介面，對照 examples.json 的 question_id／item_id／版本。
2. 準備課程單題及題組範本的可編輯副本，另複製一份，移動欄列並調整題數／答案合併寬度。
3. 建立 Google Cloud project，啟用 Sheets API，設定 OAuth consent screen、測試使用者及 Desktop client，下載 client JSON 至 repo 外。
4. 保留兩組學生的模擬情境；登入及活動功能由 002／003 提供。001 離線測試使用受控 provider，真實完整流程須在模組整合後執行。

Google 設定依 [官方 quickstart](https://developers.google.com/workspace/sheets/api/quickstart/python)，Windows 採 Desktop loopback。
Google 授權不等同應用的教師登入。External／Testing token 到期時須重新授權，錄影前檢查。

## 實作後安裝及啟動

實作須建立 pyproject.toml，採 Python 3.13 與 research.md 的版本範圍產生 uv.lock，並提交。
既有鎖定檔的組員執行下列命令。若尚未安裝 3.13，可先使用 uv python install 3.13。

```powershell
uv python install 3.13
uv sync --locked --python 3.13
uv run --locked python -c "import flask, flask_wtf, googleapiclient.discovery, google.auth, google_auth_oauthlib, sqlite3; print('imports ok')"
```

環境變數的名稱及 app 設定對應列在以下範例；實作必須啟動時驗證路徑與必要設定。
替換為自己電腦上已放好的檔案位置。token 與 client JSON 保持在 repo 外。

```powershell
$env:NOTES_GOOGLE_CLIENT_SECRETS = 'C:/your-private-folder/credentials.json'
$env:NOTES_GOOGLE_TOKEN = 'C:/your-private-folder/token.json'
$env:NOTES_SECRET_KEY = (uv run --locked python -c "import secrets; print(secrets.token_hex(32))")
$env:NOTES_DB_PATH = 'D:/os_final/instance/app.sqlite3'
uv run --locked flask --app guided_notes:create_app init-db
uv run --locked flask --app guided_notes:create_app authorize-sheets
uv run --locked flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

init-db 只在新資料庫首次建立時執行，既有資料不可因此被清空，後續 schema 變動須保留已確認版本與作業資料。
authorize-sheets 啟動獨立 loopback 授權，請求 spreadsheets 讀寫 scope，token 寫指定本機路徑。
應用啟動後以 002 的入口登入教師，再開 /teacher/notes。
以上為目標命令，001 的 cli.py 只實作 Google 授權；登入介面由 002 提供。

## 實作後自動驗證

```powershell
uv run --locked pytest tests/unit tests/contract tests/integration
```

測試用合成資料與 gateway substitute，預設不得寫真實 Google Sheet，也不依賴憑證。
此測試入口由後續 tasks／implement 建立；結果需記錄實際版本、指令、通過／失敗數。

| 案例 | 測試層 | 預期與需求 |
| --- | --- | --- |
| 單題、兩小題題組與混合布局 | unit recognition | 主題號數、小題數、合併 span 正確，FR-002、FR-013–FR-014 |
| 移動欄列、表頭改位置、變更答案寬度 | unit recognition | 對應隨來源改變，禁止硬編碼，SC-001 |
| 缺表頭、重複主題號／子題號、答案跨題 | unit | 定位格式錯誤，不發布 catalog，FR-003 |
| examples.json 有效／無勝組／缺項／混勝組／重複／錯版 | contract | 有效資料接受，無勝組 skipped，其餘 RESULT_INVALID，FR-006–FR-007 |
| 學生直呼教師 route、未登入、錯 CSRF、其他教師資源 | Flask integration | 401／403／404，無來源洩漏或寫入，FR-012 |
| 同 preview 重送、同來源兩作業並行 | SQLite integration | 相同 key 同 operation，另一作業 SOURCE_BUSY，無重複寫入 |
| 寫前來源移動、題意改動、結果版更換 | integration | 舊預覽失效，位置變動可重建，語意／結果變動停止，FR-009 |
| 題組有效 batch、明確無效 batch | gateway integration | 同組一次請求、無效請求不模擬半組成功，FR-014 |
| 前一題組成功、下一題組失敗／逾時 | integration | 已完成保留，其餘 failed／unknown，FR-011、FR-015 |
| 寫入成功但回讀失敗，及重啟恢復 | integration | unknown，先回讀才恢復；同勝組，verified 格不重寫 |
| 第三種內容、原值、預定答案 | unit／integration | conflict／待確認後可寫／verified，三者分開 |
| = 開頭、前導零、中文換行 | gateway integration | RAW 字串保存，非 formula；精確回讀，FR-010 |

## 真實 Sheets 人工驗收

由 A、B 交叉執行，在自己的可編輯副本操作。以下全部尚未執行。

| 編號 | 操作 | 預期證據 |
| --- | --- | --- |
| M01 | 單題副本匯入，逐題核對 | 主題號數等於講義，答案合併格 anchor 正確 |
| M02 | 題組副本匯入，核對 1(1)、1(2)、後續單題 | 主題號是一個單位；子題標號獨立保存，不被當成答案格 |
| M03 | 教師及兩組學生完成題組搶答 | 未填完整無法提交，同組一次順位，同勝組完整答案 |
| M04 | 教師預覽確認回填，重新開 Sheet | 全部答案正確；標號、題目、公式、格式及 merge 不被意外修改 |
| M05 | 移動欄列、改表名／寬度及增加題目，用新匯入活動重跑 | 動態辨識，沒有固定座標。若改舊活動來源的題目集合，回填停止 |
| M06 | 預覽後改一個原值或插入列 | 舊預覽失效，新位置重新預覽；不同原值需明確覆寫確認 |
| M07 | 可讀不可寫副本，或撤銷授權 | 正確區分讀寫權限或重授權需求，不假報成功 |
| M08 | 一題組寫完後中斷後續請求，再恢復 | 已驗證答案保留，未知先回讀，原勝組不變 |
| M09 | 題組含 =SUM(1,2)、001、換行中文答案 | 來源為文字，標號未變；回讀與提交文字一致 |
| M10 | 一個主題號無人勝出 | no_winner 明確，原答案保留，報告 skipped |

外部同時編輯的競態另記錄觀察與限制。前檢查與寫入間若有外部變動，系統無跨系統鎖定保證；
請在驗收中安排外部編輯並確認能偵測的衝突如實呈現，不將無法永久鎖定來源誤列為已解決。

## 驗收紀錄格式與下一步

每個實際結果記錄日期、執行者、commit、Sheet 副本識別、前置條件、預期、實際、截圖／報告。
分享紀錄前檢查學生答案與帳號資訊，憑證及 token 不附於紀錄。

本輪已完成設計及文件驗證，應用與真實 Sheets 測試仍為待執行。
下一階段 `$speckit-tasks` 依上述邊界拆任務，再以 `$speckit-analyze` 檢查覆蓋與一致性。
