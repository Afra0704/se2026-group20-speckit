# 011 時間顯示一致性：圖表與 Specify 紀錄

日期：2026-11-27（Asia/Taipei）；執行者：Codex。

## 基底與分工

- GitHub 確認 PR #14 已合併，merge 與查詢當時 master 均為 `e9a29c71caf2dd30fc72997fdd29441a35be4ae7`。
- 本機以 `git fetch origin master`、`git switch -c codex/011-time-display origin/master` 建立規格分支，沒有改動本機 master 或覆蓋原未追蹤檔案。
- 依使用者回報並獲授權，GitHub #16／#17 指派 itsusername15，#20 指派 Afra0704，三份 Issue 追加來源與分工留言；不是 OpenSpec 已確認新需求的證據。

## SpecKit 執行

- 已讀本機 `speckit-specify/SKILL.md`、專題憲章、README、共同需求與 Issue #20。
- `.specify/extensions.yml` 在前後檢查均不存在，無 before_specify／after_specify hook 需派送。
- init-options 使用 `feature_numbering=sequential`，現有001～010，故建立 `specs/011-time-display`。Git 分支與功能目錄獨立。
- 使用 `.specify/scripts/powershell/resolve-template.ps1 spec-template -Json` 取得有效範本，來源解析為 `.specify/templates/spec-template.md`，先建立範本內容再填入規格；未繞過 preset 解析。
- 本機 `.specify/feature.json` 更新為 `specs/011-time-display`，此檔依現有規則忽略，不應提交。原指標備份至 ignored `tmp/feature-before-011.json`。
- 規格品質清單16/16通過，沒有未解的 NEEDS CLARIFICATION 標記。固定台北時間仍是明列合理預設，不冒認為使用者／雙組已另行確認。

## CLI 渲染

預設 `java.exe` 啟動器未產出圖檔，已中斷該次命令；改用本機 JDK 明確路徑後成功，未下載新工具。

```powershell
& 'C:/Program Files/Java/jdk-24/bin/java.exe' '-Djava.awt.headless=true' -jar 'D:/os_final/tmp/tools/plantuml-1.2026.10.jar' -charset UTF-8 -failfast2 -tpng 'diagrams/011-time-display-*.puml'
```

首次明確路徑及技術對圖後重渲染均 exit 0。Component／Class 採 Smetana；同目錄三份 PNG 檢查簽章、IHDR、所有區塊 CRC、IEND、來源／產物時間順序均通過。三圖已開圖檢視，沒有錯誤頁。

| 圖 | 來源 | PNG | 最終尺寸 |
| --- | --- | --- | --- |
| Component | [puml](../../diagrams/011-time-display-component.puml) | [PNG](../../diagrams/011-time-display-component.png) | 1746 × 335 |
| Class | [puml](../../diagrams/011-time-display-class.puml) | [PNG](../../diagrams/011-time-display-class.png) | 547 × 705 |
| Sequence | [puml](../../diagrams/011-time-display-sequence.puml) | [PNG](../../diagrams/011-time-display-sequence.png) | 1216 × 1019 |

## Codex 技術圖意核對

- Component：原權限→原紀錄唯讀→事件及來源判讀→一致呈現→角色原可見畫面，無事件寫入、重新結算或重新授權箭頭。
- Class：原事件、階段、來源證據、解讀狀態與顯示結果分離，與既有結果關聯保持；是概念模型，不等於新增資料表。
- Sequence：有權限才取資料；明確時區、可信舊 UTC、未發生／缺值、損壞／不明各有分支。技術核對時補上原階段及「未開始即結束」，使缺值／異常同樣經呈現政策輸出，與另兩圖一致，已重新渲染。
- 原結算沒有獨立時間，三圖均不補造；原順位、勝組及版本保持，對應 FR-009～013。

## 待完成與本輪界線

組員審圖尚未執行，審查者姓名／獨立紀錄未提供；OpenSpec 新一輪同步未回報。請核對「固定台北、至秒」「事件標籤」「可信舊 UTC／不明提示」「不重算或改寫歷史」；依憲章 II，組員看過圖意後再進 plan。

本輪未實作、未建立 plan／tasks、未執行產品功能測試或人工驗收、未讀寫操作者 DB／授權／真 Sheets，沒有 commit 或 push。沒有修改產品原始碼、README 或既有共同需求決策；本輪假設及待同步事項記在 spec，不回填成已確認決策。

## 2026-11-27 使用者審圖回報與 Plan

使用者明確回報「同學已審圖」，接著呼叫speckit-plan並允許規劃。記錄為原三張概念圖已由組員核對；審查者姓名與獨立紀錄未提供，OpenSpec同步仍未回報。使用者本次plan指令明確指定固定Asia/Taipei、24小時及至秒，spec已同步最新狀態。上方「待審圖／未建立plan」為Specify當時歷史。

本輪沿用原圖責任及時序分支，僅更新標題審閱狀態，沒有把plan技術契約冒認為組員已複核。使用上方JDK24命令重渲染exit0；三張最終尺寸仍為1746×335、547×705、1216×1019。簽章、全區塊CRC、IEND及來源時間順序通過。無新增技術圖意差異；若後續介面協調改變責任／流程，仍需修圖並再次核對。

plan、research、data-model、兩份contracts及quickstart已完成，原則I～VI在研究前及設計後皆依本階段檢查；未執行產品測試／人工驗收。規格品質16/16，所有15個本地文件連結檢查通過，範本及NEEDS CLARIFICATION標記無遺留。這些是文件與圖產物檢查，不是程式實作驗證。

### 共享 checkout 的保護

Plan開始時實際分支為codex/012-result-writeback，feature.json指向specs/012-result-writeback，另有012未提交圖與文件。本輪沒有切分支、覆寫指標或修改012／#16／#17檔案。setup-plan在單一命令程序使用：

```powershell
$env:SPECIFY_FEATURE_DIRECTORY = 'D:/os_final/specs/011-time-display'
$env:SPECIFY_FEATURE_NO_PERSIST = '1'
$env:SPECIFY_FEATURE = 'codex/011-time-display'
& 'D:/os_final/.specify/scripts/powershell/setup-plan.ps1' -Json
```

解析回FEATURE_SPEC／IMPL_PLAN均為011正確路徑，BRANCH為本次指定的邏輯功能分支，不是實際checkout切換證據。最終feature.json仍指012。進入實作／提交時須安排011獨立checkout，不能將011文件誤提交到012分支。

前後檢查extensions.yml仍不存在，無before_plan／after_plan hook需派送。本輪沒有commit、push、產品原始碼修改、DB／憑證或真Google操作；未建立tasks.md。#19接線責任與測試環境待辦見plan及contracts，不虛構另一對話已同意。

## 2026-11-27 分析後決策更新

使用者回報 OpenSpec 已確認時間呈現規則，並指定顯示到分鐘；姓名與獨立紀錄未提供。C1 的政策確認缺口已有使用者回報依據。三圖僅更新呈現精度文字（至分鐘、不進位），權限、元件責任、資料關聯與時序分支不變；先前審圖紀錄保留，不冒稱同學已複核本次文字。原始時間／instant_utc 精度不變。

本次以既有 JDK24／PlantUML CLI 指令重新渲染三圖，exit 0；三份 PNG 簽章及所有區塊 CRC 檢查通過。文件檢查確認 49 項任務仍未勾選，輸入解析及 instant_utc 保留秒／小數秒，只有畫面 text 到分鐘。未實作或執行產品測試，未操作 DB／授權，未切換分支／功能指標，未 commit／push。

## 2026-11-27 圖對碼（實作後）

| 圖責任／分支 | 實作對應 | 結果 |
| --- | --- | --- |
| Access→Read | 原history owned_classroom／require_teacher；notes原owned row／report | 原驗權保留，未新增路由 |
| 原紀錄唯讀 | history同一SELECT只加phase_version；對外raw欄位與順序不改 | 無schema、writer、結算或Google呼叫差異 |
| Source／Meaning | time_views.activity_time_display、notes_time、readback_time | 明確來源政策與生命週期；無證據保守回退 |
| Observation／Policy／View | time_display.present_time與不可變DisplayTime／NormalizedObservation | aware UTC→固定台北、分鐘截取；原instant_utc精度保留 |
| 異常分支 | present_time型別／格式／長度／溢位fallback | 不用現在時間補值；缺／壞值不500 |
| TeacherView | classroom.js activityList、notes context及四張HTML模板 | textContent／Jinja escaping，事件標籤清楚 |
| StudentView／Identity | 未擴充學生DTO／結果snapshot，保留原組號與勝組 | 整份暫存DB／Google密文保留回歸及原測試覆蓋 |

無新增元件責任、角色或時序分支，沿用最近CLI產生的三張PNG；本輪圖對碼沒有再改圖，不虛構新增同學審閱。已知原圖由使用者回報同學審閱；分鐘文字改動及CLI結果見上方紀錄。真正人工操作／原偏差頁定位不由這份技術mapping取代。
