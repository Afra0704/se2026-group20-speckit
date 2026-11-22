# se2026-group20-speckit
軟體工程期末專題｜SpecKit 課堂搶答系統

第 20 大組的 SpecKit 小組專案，以 AI 代理及 SpecKit 流程開發 Guided Notes 課堂搶答系統。老師匯入 Google Sheets 講義、開啟與結束搶答、查看結果，並將勝組答案回填原講義。學生依組別提交答案，在活動結束後查看結果。

## 目前進度

截至 2026-11-23，已完成 GitHub repo 連結、SpecKit 初始化與起步協作文件。應用程式、正式憲章、功能規格及設計圖尚待建立，尚無可啟動的系統或應用程式測試。

| 項目 | 狀態 |
| --- | --- |
| SpecKit | Specify CLI 1.2.1，Codex 整合，PowerShell 腳本 |
| 憲章 | `.specify/memory/constitution.md` 目前為初始化範本 |
| 共同需求 | [共同需求與待確認決策](docs/shared-requirements.md)，待 OpenSpec 組確認建議項目 |
| 功能規格與圖表 | 尚待依子功能建立 |
| 技術棧與分工 | 下列內容為建議，待組員確認 |

## 兩小組協調

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

準備 Git、Python 3.11 以上、uv，以及 Codex 代理環境。圖表流程另需 Java、PlantUML JAR，以及所選圖表渲染方式需要的 Graphviz。Java 與圖表工具的可用版本待實際渲染後記錄。

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

Python、Flask、Jinja、少量原生 JavaScript 與 SQLite 是目前建議技術棧，尚待 plan 階段定案。應用程式的安裝、啟動及測試指令將在實作後依實測結果補上。

## SpecKit 開發流程

先在 Codex 對話執行 `$speckit-constitution`，依專題附錄建立正式憲章。每個子功能各自保留 spec、plan、tasks，依序執行以下技能。

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
git switch main
git pull --ff-only
git switch -c 001-guided-notes
```

一個 PR 聚焦一個可驗收的工作。送出前檢查 diff、更新相關規格與圖表，執行適合本次變更的驗證。提交前確認工作目錄沒有機敏資料。

```powershell
git status
git diff
git add .
git diff --cached
git commit -m "docs: define guided notes import requirements"
git push -u origin HEAD
```

在 GitHub 建立目標為 `main` 的 PR，依範本填寫證據，請另一位組員提出具體回饋並核准後合併。合併後回本機更新 main，再開始下一項工作。若合併衝突或 pull 失敗，先保留目前修改並檢查原因。

第一個 PR 使用目前的 `chore/project-setup` 分支，提交初始化檔及這次協作文件。Review 重點為共同需求的分類、暫定分工、版本與忽略規則。後續正式憲章可獨立開 PR 審查。

## 驗證與交件

核心驗收須含老師與至少兩組學生、活動階段同步、同時提交、重送、截止邊界、結束前資訊隔離，以及另一份 Guided Notes 的匯入與回填。每個功能保留 AI 執行的驗證結果與組員人工驗收紀錄。結果欄位只能填實際執行結果。

專題基本評分為文件 30%、程式碼 25%、Demo 20%、組別評量表 15%。GitHub 協作、SpecKit 子功能拆分、額外與創意功能皆為加分方向。提交前核對文件、程式碼與影片一致，確認助教可存取 repo、影片及所需操作說明。

每小組錄製一支 5 分鐘內的 YouTube Demo，包含教師與至少兩組學生的完整流程。同步整理系統簡述、repo 與影片連結、經機敏資料檢查的 AI 對話紀錄、實作方法、心得與分工表。

繳交期限為 **2026-11-30 00:00（Asia/Taipei）**，建議 **11/29 白天**完成表單提交。逾期補交至 12/05 00:00，每晚一天扣 10 分，天數無條件進位。表單成功提交才算繳交完成。

## 資料與憑證

金鑰、OAuth token、密碼及真實學生資料放在本機受控位置。使用環境變數或被忽略的本機設定載入憑證，範例設定只能填佔位值。提交 PR 或 AI 對話紀錄前檢查機敏內容。本機資料庫、依賴快取及執行日誌不提交。

## 需求依據

共同需求依課程提供的《期末專題說明》與《SpecKit 教學》整理。課程更新或兩組確認後，請更新 [共同需求與變更紀錄](docs/shared-requirements.md)。Spec Kit 操作可參考 [官方文件](https://github.com/github/spec-kit)。
