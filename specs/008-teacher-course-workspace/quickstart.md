# 008 設定與驗收指南（實作後使用）

**2026-11-26：008受控實作與自動驗證已完成（391 Python tests、98 subtests、24 Node tests）。真Google Picker、真人驗收與具名互審仍待完成。** 請停止舊服務、備份原DB與key，沿用007設定後重啟；不清空DB、不更換持久key。以下Google Cloud操作尚未實測，不能以自動測試代替。

## 1. 保存007環境

沿用 `D:/os_final/instance/classroom-007.sqlite3`、原教師／課程／講義、main Web client、Flask secret及Fernet key。實作前停止舊服務，再由操作者備份DB與repo外key至私人位置；本次計畫不備份、改寫或刪除檔案。不能套007的起步空白DB規則清掉本輪既有資料。

008啟動／init-db將新增附加表與索引，保留auth_instance UUID及原Google密文；重跑不重置。若schema失敗，應停止啟動、保留資料並依去機敏錯誤修復，不能改指向新空白DB掩蓋。

## 2. 後續Google Cloud準備

可沿用My First Project：

1. 保留原Sheets API，啟用Google Picker API與Google Drive API。
2. 新建**專用Picker Web application client**，與原main client不同但同project；不覆寫原web-client.json。
3. Picker client登錄callback `http://127.0.0.1:5000/auth/google/callback` 與JS origin `http://127.0.0.1:5000`。本方案code redirect沿用原callback，不改主教師登入。
4. 新JSON存repo外，例如 `C:/Users/user/guided-notes-private/picker-client.json`；原主JSON/key/token都保留，不貼內容。
5. 建受網站來源與API限制的API key，網站來源依官方樣例核對本機 `http://127.0.0.1:5000/*` 與Picker iframe `https://docs.google.com/*`；API限制只准Picker／Drive，不開任意網站萬用來源。
6. App ID使用同project的**project number**，不是project文字ID；client、key、App ID需同project。
7. 同意畫面與測試使用者加入兩教師；Picker請求openid/email/profile＋drive.file，主Sheets scope保留。應用實際請求Picker時明確false非增量，不能直接套原007 include_granted_scopes=true。

官方：[Picker sample](https://developers.google.com/workspace/drive/picker/guides/web-picker-sample)、[Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)、[GIS false參數](https://developers.google.com/identity/oauth2/web/reference/js-reference)。這些是未執行的準備事項，不等於Google已允許本機選檔。

## 3. 實作完成後CMD設定與啟動

以下設定已接線；真Google Picker與人工驗收仍待執行。main Web client、secret與持久key沿用007，不另產生、不更換。

```bat
cd /d D:\os_final
uv sync --locked
set "PYTHONPATH="
set "GUIDED_NOTES_CLASSROOM_MODE=1"
set "GUIDED_NOTES_DATABASE=D:\os_final\instance\classroom-007.sqlite3"
set "GUIDED_NOTES_PUBLIC_ORIGIN=http://127.0.0.1:5000"
set "GUIDED_NOTES_GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/google/callback"
set "GUIDED_NOTES_GOOGLE_PICKER_CLIENT_SECRETS=C:\Users\user\guided-notes-private\picker-client.json"
set "GUIDED_NOTES_PICKER_API_KEY=替換為受限制的API-key，不貼到回報"
set "GUIDED_NOTES_PICKER_APP_ID=替換為project-number"
set "GUIDED_NOTES_HTTPS=0"
set "FLASK_DEBUG=0"
```

`GUIDED_NOTES_GOOGLE_WEB_CLIENT_SECRETS`、`GUIDED_NOTES_GOOGLE_TOKEN_KEY_FILE`、穩定的`GUIDED_NOTES_SECRET_KEY`沿用原私有設定。新key名稱未設定只停用cloud入口，link匯入仍可用；純課程瀏覽不能503或自動Google授權。

實作及備份完成後，舊服務Ctrl+C，再用同一CMD：

```bat
.venv\Scripts\python.exe -m flask --app guided_notes:create_app init-db
.venv\Scripts\python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

不init-teacher，不刪DB／OAuth檔；005/006/007舊未完成任務不因008開啟而勾完成。

## 4. 最先做的真實scope smoke

先以已完成main Sheets broad授權的教師A，明確按cloud入口。記錄去機敏結果，不記token／code／sub：

- callback驗同人、專用client、nonce成功；後端確認實際scope只含四項allowlist。
- Picker能開啟，只顯示Google Sheets、單選、沒有上傳；已有有效cache再次匯入不重複Google授權。
- 換成教師B帳號授權被拒，A教師身分與原Sheets連接仍在。
- 專用token若帶broad或未知scope，回PICKER_SCOPE_UNSAFE，不交付、不降級；scope缺失亦拒絕。
- API key來源限制可運作，僅乾淨匯入HTML送跨站origin，callback仍no-referrer；不以取消網站限制解決錯誤。

Python Flow的false行為目前是協定推論，此步**未執行**；受控fake不是替代證據。若不能拿到窄token，修設計／設定後重驗，不能宣稱cloud完成或擴大allowlist。

## 5. 教師介面及兩入口

| 操作 | 預期 |
| --- | --- |
| A登入→教師首頁→我的課程 | 歡迎頁簡單；卡片只列A課程，不出現全部流程表單。 |
| 選課程→左側講義／課堂 | 橫幅與目前位置清楚，右側只顯示該區；refresh/back仍在正確課程。 |
| 瀏覽清單→按＋→Escape | 零Google授權，關選單後焦點回＋。 |
| 選link→輸入副本→讀取 | 必要時才要求Sheets授權；回來保留原課程與連結。 |
| 選cloud→選副本 | 必要時授Picker，選完必要時再授Sheets；兩者同人，不要求改教師帳號。 |
| 兩入口各選單題／題組／移動版型 | 同一個分頁選擇、命名、全文／題數／格數預覽及確認流程。 |
| 有授權再次匯入 | 不強制每次consent/select_account；到期或缺必要權限才引導。 |
| popupblocked／取消／無權限／斷網 | 原課程有可讀提示與重試／改link，不半存講義或清教師登入。 |
| 兩分頁同時匯入 | 不混course/source；OAuth舊流程被最後開始取代時明確重試。 |
| B開A課程／flow／講義URL | 後端拒絕，不回名稱、內容或token。 |

首次唯讀匯入用來源副本，確認雲端原內容不變。儲存版本不代表已成功回填。

## 6. 講義移除及課堂

建立未使用與已建活動的講義，先取消再確認移除；確認文字含名稱、所有版本、保留歷史與雲端原檔。驗所有一般清單／新活動選項／同來源更新候選都消失，直接一般舊URL410；跨教師404。重送不影響別份講義。

已建立活動仍可閱讀全文、開始／結束與查看結果；從活動歷史可讀原版本，原結果／回填報告／部分失敗恢復繼續依規則運作。重新匯入同來源明確新增，產生新import，不復活舊講義。Google原檔沒有刪除或非目標改寫。

課堂沒有刪除按鈕或API，只結束並保留歷史；課程也不提供刪除。

教師用Chrome一般視窗，甲組用Edge，乙組用Chrome無痕（不要兩個共用cookie的無痕視窗當兩組）；從首頁學生入口加入課堂。驗建立後5秒內全文、開始前不可填、題組整組、準備中結束、同堂只能一個未結束活動、換場／復線、教師登出不清學生資格。正式003未接入仍可能QUIZ_UNAVAILABLE／未結算，不是假排名。

## 7. 自動驗證（已實作；實際結果見validation.md）

在另一個CMD執行，fixture用暫存007資料而非操作者DB／憑證：

```bat
cd /d D:\os_final
set "GUIDED_NOTES_CLASSROOM_MODE="
set "GUIDED_NOTES_DATABASE="
set "GUIDED_NOTES_GOOGLE_WEB_CLIENT_SECRETS="
set "GUIDED_NOTES_GOOGLE_TOKEN_KEY_FILE="
set "GUIDED_NOTES_GOOGLE_PICKER_CLIENT_SECRETS="
set "GUIDED_NOTES_PICKER_API_KEY="
set "GUIDED_NOTES_PICKER_APP_ID="
.venv\Scripts\python.exe -m pytest tests -q
node --test tests/workspace-navigation.test.cjs tests/import-menu.test.cjs tests/import-confirm.test.cjs tests/picker-flow.test.cjs tests/identity-ui.test.cjs tests/student-question-text.test.cjs tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs tests/activity-sync.test.cjs tests/notes-ui.test.cjs
```

新增case至少包含：populated007初始化兩次／中途失敗rollback／密文及UUID保留、舊JSON路由、所有可見性入口、remove↔activity/version屏障競態、confirmed重送、同source新UUID、歷史unknown恢復、窄scope/client/profile／加密用途錯配、flow/grant/claim/ticket重放晚回、reconnect先完成後selection晚回、008 flow留存超過24小時後新login／authorize可清attempt不受FK阻擋、取消／expired preview從舊notes URL確認仍被拒、header／log無秘密。

人工另外記錄日期、姓名、版本／commit、瀏覽器、預期／實際、5秒計時及去機敏證據；1366×768與390×844、鍵盤／長名稱／焦點需真畫面核對。此計畫沒有執行上述新測試，不預填通過數字。

## 8. I1／U1 補充驗收（尚未執行）

- 受控時間／故障：119秒重試回FLOW_BUSY，120秒在原flow有效時可接手；兩重試只有一個成功。舊請求即使先回仍不能保存；flow先到30分鐘則拒絕。selection的ticket/cache到期時要求必要授權／重新選檔。
- 原分頁／名稱不改重送，取得同preview_id且沒有重讀。直接換sheet或名稱重送回FLOW_STEP_CONFLICT，不回舊預覽冒充新內容。
- 真人：按「重新選擇／修改名稱」，確認保留原表單輸入、舊預覽失效；改選／改名並明確建新預覽。舊choice_revision、原notes舊確認URL均不能出版，完成後無修改入口。
- 自動屏障驗revise↔confirm與雙retry，並比較confirm的existing_import_id；真人操作不能代替這些競態測試。各結果在implement後如實記錄，不預填通過。

## PR #7 修正後複審

- 同一匯入flow網址分別開A／B分頁，A保留舊預覽；B用「重新選擇／修改名稱」建立新預覽。回A按確認，應提示PREVIEW_STALE且沒有保存；B核對後明確確認才保存。不能用兩個不同flow代替這個情境。
- Picker晚到請求與初始化中斷以受控測試重現：`tests/unit/test_picker_authorization.py`、`tests/integration/test_google_schema_atomicity.py`。不要求人工修改真實DB或撤銷Google授權來造故障。
- 新的空白DB初始化失敗會回滾基礎／Google原子段，修正故障後可重試；既有007 DB不清空、不更換key。notes／workspace仍各自附加交易，不能宣稱整個app factory全原子。
- 圖意差異見007／008 Sequence，須由同學複審；本輪沒有代填其他人工／雙組確認任務。
