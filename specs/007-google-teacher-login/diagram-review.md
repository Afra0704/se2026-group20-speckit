# 007 圖表與規格起點

2026-11-25（Asia/Taipei），Codex 依 speckit-specify 建立規格及三圖，尚未建立 plan/tasks 或修改產品。

使用者本次確認：先做身分首頁＋Google 登入，Drive 選檔下一輪；舊應用資料可刪。依此採新的空白開發 DB，不做舊教師綁定／遷移。這是規格決策，本次沒有實際刪除 DB、Google 憑證、雲端講義或來源答案。

## 三圖

- [Component](../../diagrams/007-component.png)：首頁分流、Google 身分、教師資格、課程權限及講義授權的責任。
- [Class](../../diagrams/007-class.png)：唯一教師對應、一次性登入嘗試、可撤銷教師資格、分開的學生與講義授權。
- [Sequence](../../diagrams/007-sequence.png)：學生直接加入；老師驗證、建帳／重登入、失敗拒絕、登出與講義授權核對。

CLI：

```powershell
& 'C:\Program Files\Java\jdk-24\bin\java.exe' '-Djava.awt.headless=true' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar -charset UTF-8 -tpng 'D:/os_final/diagrams/007-*.puml'
```

實際退出碼 0，三張 PNG 均產生。Codex 核對圖意與規格一致；**尚未收到同學審圖回報**，日期／姓名／結果待補，不能沿用 006 審查當作 007 已審。

## 現有程式觀察（唯讀）

- auth.py 的 TeacherContext／require_teacher 與教師登入資格可供後續 plan 評估沿用；目前教師登入仍是 username/password。
- 首頁目前直接顯示學生課堂頁，教師頁共用活動模板；尚無本輪身分首頁及 Google 教師登入。
- notes/google_authorization.py 是原本本機 Sheets 授權輔助；不代表已具備網頁教師身分登入。現有全域本機 Google profile 必須防止在重置後依數字 ID 誤認歸屬。
- 技術流程、Google 設定、套件與授權需求留待 plan 以官方文件查核，本文件不推論現有 Desktop client 可直接當網頁登入使用。

## 分工與待審內容

建議沿用 002 身分／活動邊界接首頁、登入／登出及教師資格，001 配合講義授權歸屬檢查。這是建議，並非本輪已由同學確認的分工；使用者已要求在此啟動本輪，後續共享檔由同學互審。

請核對：首頁老師／學生流程、第一次 Google 登入建立獨立教師、同一身分不重複建帳、教師資料隔離、教師登出不刪學生資格、Google 登入與 Sheets 授權分開、Drive 下一輪、空白 DB 不遷移。OpenSpec 本輪新增登入確認尚無紀錄，依 D20 保持待同步，不更改既有課堂決策。

目前 Git 仍是 codex/006-student-question-text，保留 005／006 全部未提交修改；未 commit/push、未切分支、未操作登入服務或雲端設定。.specify/feature.json 已指向 007，後續 plan/tasks 依此找功能。


## Plan 展開與本次確認紀錄（2026-11-25）

使用者明確表示「可以進入 plan」並再次要求執行；因此本次進行 Phase 0/1 設計。審圖者姓名與獨立紀錄未提供，不能改寫為「某同學已審圖通過」；原有確認狀態及 OpenSpec 待同步維持。

依三圖展開的技術差異：

- Component 新增 Google provider、server attempt/browser epoch、本人 Sheets connect/refresh、Fernet 與密文 DB；沿用課程及 notes 的 TeacherContext，不建第二套權限。
- Class 對應 auth_instance、google_identities、auth_browsers、google_oauth_attempts、google_sheets_credentials 與既有 teachers/grants；明示密文 owner 綁定、lease/revision、學生資格獨立。
- Sequence 明示開始、claim、外網、finalize 的短交易分隔；login 建／取教師、Sheets 同 sub 連接、登出撤 grant/epoch、refresh CAS。外網不持 write lock，晚到結果拒絕，已送出的 Google 寫入無法用 logout 撤回。

本次依上方 CLI 重新產生三張 PNG。首次因換行／class alias 語法失敗，修正圖檔後重跑退出碼 0；component 1320×723、class 907×670、sequence 1456×1825，均有有效 PNG。Codex 已查看 component 圖並核對文字及關係；其餘以 PlantUML CLI 與來源關係核對。此為 AI 核對，不代表同學已審新版技術圖。

尚待同學核對：Google provider 與原 grants 邊界、browser current pointer、同一 Web client 的雙 purpose、密文 key/instance 歸屬、test_password 僅 testing 及既有 notes fallback 移除。本輪具體分工／新增介面審查姓名與結果待補。

Phase 0 本機只檢查版本、metadata、函式簽名及 source，Google 功能依官方文件與兩研究代理唯讀結果；沒有讀 client/token/key，沒有 OAuth 往返或產品測試。產物見 plan.md、research.md、data-model.md、contracts/、quickstart.md；尚未產生 tasks。005/006 人工 checkbox 不變。extensions.yml 不存在，plan 前後 hooks 無需執行。


## Analyze I1/I2 修正（2026-11-25，使用者已授權）

- I1：新增記憶體 CredentialSnapshot，不帶 refresh token/client secret/handler；before_request 只核對資格與時效、apply，refresh 拒絕。維持 401 不刷新重送，狹窄區分送出前快照失效與已送出不確定狀態，不 replay 寫入。原 Gateway 對外介面、RAW／回讀／恢復保持。
- I2：refresh 的持久 lease 30 秒，monotonic 結果接受期限 20 秒；token POST 最多一次、必要憑證 GET 最多一次，無自動 retry/redirect，按剩餘預算限制 timeout。逾時只 CAS 釋放自己的 lease、不改憑證狀態／revision／密文；晚回結果不用，只有期限內明確 invalid_grant 才標失效。不假稱能硬中斷所有阻塞 I/O。
- 已同步 plan/data-model/Sheets contract/research/quickstart/tasks，對應 T037/T038/T044/T045/T047/T048/T051。仍為 61 項全未完成，不新增功能需求或改 Drive 範圍。
- Component 補不可刷新快照與 Sheets SDK/API 邊界；Class 明示快照不是新表；Sequence 補顯式刷新、budget/CAS/清理及送出前失效分支，並將講義操作放在登出之前。
- 執行原 CLI，退出碼 0，三張 PNG 成功重新產生；Codex 查看 class 圖核對關係。修圖仍未有同學再次審閱結果，不代填姓名／確認。
- 文件交叉檢查、相對連結、任務序號／標籤／路徑及 PNG 格式通過，005/006 未完成人工標記保留。沒有修改產品程式、建立／刪除 DB、讀真實憑證、執行新功能或真人測試，也沒有 commit/push。


## 007 實作後 AI 核對（2026-11-25）

- 實際分支 codex/007-google-teacher-login，保留 005/006 修改，未 commit/push。這是 Codex 實作核對，不是同學互審；姓名與獨立審查結果仍未知。
- Component：routes/service 對接 provider、crypto、sheets_service；沿用 require_teacher／TeacherContext、notes gateway 與學生課堂，傳輸只收不可刷新快照。
- Class：五張新表對應 schema.sql；原 teachers/grants 沿用。密文綁 purpose/owner/instance/client/generation/revision，terminal attempt secret_blob 清 NULL。快照是記憶體物件，不是新表。
- Sequence：start/claim/finalize 短交易，外網不持 write lock；last-start-wins、logout current pointer、Sheets 同 sub、30 秒 lease／20 秒 deadline 與 CAS、401 不 replay 均有自動證據。已送出的外部寫入仍無法藉登出撤回。
- 修圖僅將標題改為實作、補終態清除秘密；未改功能需求。CLI：`& 'C:/Program Files/Java/jdk-24/bin/java.exe' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar 'diagrams/007-*.puml'`，退出碼 0。
- PNG 格式與尺寸：component 1766×733、class 1090×723、sequence 2040×2691；Codex 已查看 class PNG，文字與關係可讀。其餘以 CLI／來源對照驗證。
- 本輪同學需核對 grants/current pointer、雙 purpose、密文歸屬、notes snapshot、fixtures 與新版三圖；D20／分工／具名互審保持待補。
