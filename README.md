# se2026-group20-speckit
軟體工程期末專題｜SpecKit 課堂搶答系統

第 20 大組的 SpecKit 小組專案，以 AI 代理及 SpecKit 流程開發 Guided Notes 課堂搶答系統。老師匯入 Google Sheets 講義、開啟與結束搶答、查看結果，並將勝組答案回填原講義。學生依組別提交答案，在活動結束後查看結果。

## 目前進度

截至 2026-11-25，002 共用骨架已透過 PR #4 合併。001 可由教師網頁讀取雲端 Google Sheets、選表、預覽單題／題組、保存不可變版本並供活動使用；確認回填、回讀報告及恢復也已接線並通過替代來源測試。兩份真實雲端副本已完成匯入驗證，尚未實際寫回；正式結算 provider、完整跨模組與人工驗收仍待完成。憲章 v1.0.0 已通過組員審查，Q2／Q3 共同決策維持已確認狀態。

選擇分頁時可「沿用工作表名稱」或「自訂講義名稱」（1–100 個字元），名稱顯示在講義清單、預覽與保存頁，並保留原始來源分頁資訊。多分頁一次選一張、各自匯入，不自動合併。自訂文字只存本系統，不更改 Google Sheets；此教師顯示擴充已由本對話使用者確認，OpenSpec 同步仍待確認。

教師頁的「活動回填預覽」可比較已結算勝組答案與原值，逐項同意覆寫後確認。每題組一次 RAW 批次寫入，只有回讀一致才標成功；未知／部分失敗須從報告先回讀再建立恢復預覽，保留原勝組。結果模組未完成結算時仍會提示等待，不會產生假勝組。操作與限制見 [quickstart](specs/001-guided-notes/quickstart.md)。

PR #6 合流已將 001 與 004 的真實課程授權、課程講義清單／版本、課堂加入及活動切換接上，並修正教師斷線後按鈕無法恢復的問題。004 規格記錄課堂 D12–D16 的雙組確認；講義顯示名稱另編 D17，保留原待同步狀態。004 使用新的課堂開發資料庫，舊 DB 不清空。正式 003 與真人／真實來源驗收仍待完成，啟動方式及限制見 [合流驗證](docs/pr6-integration-validation.md)。

| 項目 | 狀態 |
| --- | --- |
| SpecKit | Specify CLI 1.2.1，Codex 整合，PowerShell 腳本 |
| 憲章 | [憲章 v1.0.0](.specify/memory/constitution.md) 已通過組員審查（使用者回報） |
| 共同需求 | [共同需求與待確認決策](docs/shared-requirements.md)，待 OpenSpec 組確認建議項目 |
| 功能規格與圖表 | [001 規格](specs/001-guided-notes/spec.md)、[計畫](specs/001-guided-notes/plan.md)、三類圖及 PNG 已產出，待設計互審 |
| 可操作流程 | 教師登入 → 講義匯入 → 工作表 → 預覽 → 確認版本 → 建立活動 |
| 尚未交付 | 勝組回填作業／恢復、完整 003 結算接線及兩位組員人工驗收 |

## 005：建立活動後的學生預覽

005 已完成自動測試範圍的實作，教師加兩組學生的人工驗收仍待完成。老師建立活動後，學生即可看到活動名稱、題號、小題與作答欄；準備中不可填答，按「開啟搶答」後才可輸入／提交。同堂一次只能有一個準備中或搶答中的活動，必須先結束再建立下一個。準備中也能直接結束，正常結束保留歷史。

本次採專用空白開發 DB `instance/classroom-005.sqlite3`，不遷移舊測試資料。005 起步時建立空白 DB；首次需初始化教師並依輸出 ID 綁定 Google profile，再建立課程與匯入講義。若本機已完成這些設定請沿用，不要重建或清空。沒有刪除舊 DB、OAuth 憑證或來源 Sheets。啟動及驗收見 [005 quickstart](specs/005-preview-before-start/quickstart.md)，檢查結果見 [005 validation](specs/005-preview-before-start/validation.md)。正式 003 的受理／排名／結算限制依原交接，不因本次預覽修補視為已完成。

## 006：學生閱讀完整題目

已補齊從保存講義版本到活動快照、學生畫面的全文傳遞。每個小題顯示自己的文字、標號與作答欄，保留換行與長文字；題組仍整組提交。建立後可讀，開始後才可填答，準備中可直接結束，同堂單活動限制沿用 005。

教師匯入預覽及保存頁可核對全文。既有講義版本若已保存完整文字，可直接建立新活動；舊活動沒有全文快照時會提示選完整版本建立新活動，真正缺字的講義才須重新匯入。來源改字或重新匯入不會改動已建立活動。

內建示範清單、示範受理及其啟動設定已移除；正式服務不可用會明確回報錯誤。測試替代資料僅存在 tests/。課程 Demo 影片要求保留。003 尚未接入時仍會顯示 QUIZ_UNAVAILABLE／待結算，不能當作排名已完成。

啟動與人工情境見 [006 quickstart](specs/006-student-question-text/quickstart.md)，自動證據及未完成項見 [006 validation](specs/006-student-question-text/validation.md)。啟動前須停止舊後端，再從目前工作樹啟動；只重整網頁不會載入新 Python 程式。新增快照表不清空既有 DB，也不替舊活動補字。教師與兩組學生的人工閱讀、5 秒同步及排版驗收仍待執行。

## 007：身分首頁與 Google 教師登入

已完成自動驗證範圍的實作。首頁選「我是老師／我是學生」；老師用 Google 登入，學生維持課堂碼與組別。教師課程依 Google 穩定身分隔離，取消或失敗不清掉原身分，登出撤銷此瀏覽器的教師資格並保留學生資格。

講義需另外按「連接我的 Google Sheets」，且須與登入教師為同一 Google 帳號。授權密文綁定教師與新 DB，Web 不再使用原 Desktop token／全域教師 profile。Drive 選檔仍留下一輪。新版本請用 `instance/classroom-007.sqlite3`、新的 **Web application OAuth client** 及 repo 外的持久 Fernet key；不刪舊 DB、Desktop 憑證或雲端講義。

目前啟動步驟以 [007 CMD 指南](specs/007-google-teacher-login/quickstart.md)為準；005/006 的帳密啟動方式屬歷史版本，正式入口已停用密碼登入。真人 Google、同學互審、OpenSpec D20 同步及教師加兩組學生驗收仍待完成；自動證據見 [007 validation](specs/007-google-teacher-login/validation.md)。正式 003 限制保持。

## 008：教師課程工作區（計畫完成，未實作）

依使用者新需求建立分層教師首頁／課程卡片／課程左側導覽。講義管理按「＋匯入講義」才選雲端 Google Sheets 或貼連結，實際操作才引導必要授權；已有有效授權不反覆登入。講義可從清單移除且保留既有活動／回填與雲端原檔；使用者已撤回刪課堂提案，課堂不可刪除。

使用者已回報圖意核對完畢並允許plan；[008 計畫](specs/008-teacher-course-workspace/plan.md)、研究／資料模型／四份契約／[設定驗收指南](specs/008-teacher-course-workspace/quickstart.md)及新版三圖已產生，尚未改產品介面、實作雲端選檔或刪講義。計畫採專用窄Picker token及講義清單移除，原007資料保留。本次技術修圖／介面互審、具名分工及D21 OpenSpec同步仍待補；下一階段tasks、analyze再implement，原人工任務不代勾。

## 兩小組協調（協作規則）

SpecKit 小組兩人共用本 repo。OpenSpec 小組另建 repo，兩小組依共同需求實作一致的使用者功能。請 OpenSpec 組建立 repo、互邀協作者，並將連結提供給大組。確認後在共同需求文件補上 repo 連結、確認日期與確認者。

每次改變功能或使用者可見行為，先共同討論，更新共同需求及兩邊規格，再實作並互相驗收。

## 建議分工

下列 A、B 為暫定角色，請兩人確認後替換為姓名或 GitHub 帳號。

| 角色 | 主責 | 互審與人工驗收 |
| --- | --- | --- |
| A | 001 Guided Notes 匯入與回填，後續 CSV 匯出 | 審查 B 的活動階段、同時提交與截止邊界 |
| B | 002 身分與活動階段、003 搶答與結果 | 使用第二份講義驗收 A 的動態辨識及回填 |
| 雙方 | 共用資料介面、整合、Demo、交件與 AI 紀錄 | 互審 PR，交叉執行人工驗收 |

先一起定義題目識別、題組識別、活動階段與提交結果資料，再分頭開發。加分功能以兩小組共同確認的範圍為準。

## 環境與取得專案

準備 Git、Python 3.13、uv，以及 Codex 代理環境。圖表使用 Java 與 PlantUML CLI（本機驗證為 Java 24、PlantUML 1.2026.10），Component／Class 採 Smetana。

新組員在自己的工作目錄執行以下 PowerShell 指令。

```powershell
git clone https://github.com/Afra0704/se2026-group20-speckit.git
Set-Location se2026-group20-speckit
git config user.name "你的名字"
git config user.email "你的 GitHub 電子郵件"
uv tool install specify-cli==1.2.1
specify version
Get-ChildItem .agents/skills -Directory | Select-Object Name
```

安裝完成後若找不到 `specify`，執行 `uv tool update-shell` 並重新開啟 PowerShell。已安裝其他版本的組員先對齊團隊版本。clone 會取得已提交的 SpecKit 技能、範本與腳本。

001 採 Python 3.13、Flask、Jinja、少量原生 JavaScript、SQLite 與官方 Google 用戶端。共用環境已整合；目前 CMD 啟動方式見 [007 指南](specs/007-google-teacher-login/quickstart.md)。Google 教師不執行 init-teacher；Web client 與加密 key 維持在 repo 外，Desktop CLI 仍可獨立使用。

## SpecKit 開發流程

憲章已依專題附錄建立並通過組員審查（使用者回報）。後續修訂可在 Codex 對話執行 `$speckit-constitution`。每個子功能各自保留 spec、plan、tasks，依序執行以下技能。

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

這些技能在代理對話中執行。specify 階段需先在根目錄 `diagrams/` 建立 Component、Class、Sequence 三類 PlantUML 圖，並以 CLI 產生同目錄 PNG。使用功能編號作為圖檔前綴，避免彼此覆寫。plan 依圖表規劃，implement 後核對程式碼與圖表的一致性。Converge 找出缺漏後，持續補齊並驗證。

圖表渲染可依專題附錄執行，JAR 位置依本機安裝調整。

```powershell
java -jar plantuml.jar "./diagrams/*.puml"
```

每次切換功能，核對 `.specify/feature.json` 指向要開發的目錄。此檔是每台電腦的本機狀態，SpecKit 自帶的 `.specify/.gitignore` 已排除它。新 clone 需依目前功能設定本機指向，並讓代理核對；切換 Git 分支後也要再次檢查。

## GitHub 協作

每項工作先開 Issue，寫清楚需求編號、負責人與驗收條件。每人使用自己的帳號提交及互審。以下是開始新工作時的流程，若 SpecKit 已建立功能分支，使用該分支即可。

```powershell
git switch master
git pull --ff-only
git switch -c 001-guided-notes
```

每位組員在自己的功能分支按階段提交，以規格與圖表、實作、驗證等可追溯的工作作為 commit 邊界。每條功能分支累積完成後，再集中開一個 PR 至 `master`，由另一位組員互審。口頭審查也要在對應文件或 PR 留下審查方式、範圍與結果。送出前檢查 diff、相關規格及圖表、驗證證據與機敏資料。

```powershell
git status
git diff
git add .
git diff --cached
git commit -m "docs: define guided notes import requirements"
git push -u origin HEAD
```

在 GitHub 建立目標為 `master` 的 PR，依範本填寫證據，請另一位組員提出具體回饋並核准後合併。合併後回本機更新 master，再開始下一項工作。若合併衝突或 pull 失敗，先保留目前修改並檢查原因。

初始化與起步協作文件由 `chore/project-setup` 分支提交。憲章與對應 README 更新使用 `docs/project-constitution` 分支，審查重點為治理原則、圖表流程、驗收要求與待確認決策的處理方式。

## 驗證與交件

核心驗收須含老師與至少兩組學生、活動階段同步、同時提交、重送、截止邊界、結束前資訊隔離，以及另一份 Guided Notes 的匯入與回填。每個功能保留 AI 執行的驗證結果與組員人工驗收紀錄。結果欄位只能填實際執行結果。

專題基本評分為文件 30%、程式碼 25%、Demo 20%、組別評量表 15%。GitHub 協作、SpecKit 子功能拆分、額外與創意功能皆為加分方向。提交前核對文件、程式碼與影片一致，確認助教可存取 repo、影片及所需操作說明。

每小組錄製一支 5 分鐘內的 YouTube Demo，包含教師與至少兩組學生的完整流程。同步整理系統簡述、repo 與影片連結、經機敏資料檢查的 AI 對話紀錄、實作方法、心得與分工表。

繳交期限為 **2026-11-30 00:00（Asia/Taipei）**，建議 **11/29 白天**完成表單提交。逾期補交至 12/05 00:00，每晚一天扣 10 分，天數無條件進位。表單成功提交才算繳交完成。

## 資料與憑證

金鑰、OAuth token、密碼及真實學生資料放在本機受控位置。使用環境變數或被忽略的本機設定載入憑證，範例設定只能填佔位值。提交 PR 或 AI 對話紀錄前檢查機敏內容。本機資料庫、依賴快取及執行日誌不提交。

## 需求依據

共同需求依課程提供的《期末專題說明》與《SpecKit 教學》整理。課程更新或兩組確認後，請更新 [共同需求與變更紀錄](docs/shared-requirements.md)。Spec Kit 操作可參考 [官方文件](https://github.com/github/spec-kit)。

## 目前的設計整合分支

`integration/001-002-design` 合併 001 與 codex/002-identity-activity-phases，統一目錄及介面。
[001 計畫](specs/001-guided-notes/plan.md) 的離線核心已實作，完整應用接線仍待完成；[002 計畫](specs/002-identity-activity-phases/plan.md) 的共用骨架由同學負責。
共同採 src/guided_notes、Python 3.13、import_id／import_version、主題號作提交單位，且結算完成才可回填。
設計整合已透過 PR #3 合入 master；001 實作分支為 `codex/001-guided-notes-implementation`。
共用骨架由 002 先建立，001 接 notes Blueprint。先核對實際狀態與未提交變更，再更新分支。

以下為歷史離線階段紀錄；目前可啟動的功能與最新實測狀態以上方進度及 [實作驗證紀錄](specs/001-guided-notes/validation.md) 為準。

已新增純資料契約檢查與可注入官方 client 的 Sheets gateway；授權準備請見 [Google Sheets 設定](docs/google-sheets-setup.md)，同學的接線入口見 [介面交接](specs/001-guided-notes/contracts/interfaces.md#2026-11-23-離線實作交接尚未接線)。

共用 Python 環境建立前，可先用本機 Python 執行無額外依賴的辨識測試：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests/unit -p test_recognition.py -v
```

本輪全部離線測試（標準庫 unittest，之後也可由 pytest 收集）：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/contract -v
python -m unittest discover -s tests/integration -v
```

integration 目前僅有離線元件交接測試，尚無 HTTP／登入／DB 的整合驗證。

2026-11-24 更新：已接入 PR #4 的共用骨架，正式 `pyproject.toml`／`uv.lock` 包含 Google 套件，`.venv` 已建立；目前合併後共 89 項測試與 98 子案例通過（含 002 的 HTTP／登入／DB 邊界）。001 的網頁匯入及持久化仍未接入。
可用 `.venv\Scripts\python.exe -m pytest tests/unit tests/contract tests/integration -q` 執行合併後全部測試。
新增獨立唯讀診斷 `notes.cli inspect-sheet`，正式環境用法見 docs/google-sheets-setup.md。

2026-11-23 續作已完成可獨立測試的匯入候選 UUID／版本、來源指紋與重綁、回填預覽／覆寫確認、回讀與恢復判定，以及獨立 Google OAuth CLI。新命令與 CMD 寫法見 [授權說明](docs/google-sheets-setup.md)。完整網頁、持久化與活動結果接線仍待 002／003。

第一個離線核心進度 commit：`05186ed`。本機 commit 不代表已推上 GitHub；新圖與後續核心仍需組員審查。

## 008 教師工作區（2026-11-26）

沿用007 Google教師登入與資料庫。教師登入後由「進入我的課程」→課程卡片→課程工作區，左側分講義與課堂；進入指定課堂才看加入碼、已加入組別及活動控制。學生仍免Google，沿用原課堂加入。

講義管理按「＋匯入講義」選貼連結或Google雲端；兩入口共用單分頁、命名、全文預覽與確認。讀取逾時可明確重試，修改分頁／名稱先失效舊預覽。刪除講義僅移除清單與新活動選項，既有活動／回填歷史與雲端原檔保留；課堂、課程沒有刪除功能。

貼連結使用原Sheets授權；雲端選檔另需同project專用Picker Web client、受限制API key與project number。沒有Picker設定時可繼續管理課程及貼連結；不把原後端Sheets token交給瀏覽器。設定、CMD啟動與人工矩陣見 [008操作說明](specs/008-teacher-course-workspace/quickstart.md)，實際證據見 [008驗證紀錄](specs/008-teacher-course-workspace/validation.md)。真Google Picker、兩教師與兩組學生人工驗收、具名互審／D21仍待完成；受控測試不代表真雲端通過。

啟動前先在私人位置備份原DB與key；保持原007環境設定，不清空DB或重建key。關掉舊服務後，CMD於repo執行 `.venv\Scripts\python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000`，開啟 `http://127.0.0.1:5000/teacher`。啟動會以可重跑附加schema保留原資料；新增測試只用暫存DB。
