# Implementation Plan: 時間顯示一致性

**Branch**: `codex/011-time-display`（本功能邏輯分支） | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: `specs/011-time-display/spec.md`；[Issue #20](https://github.com/Afra0704/se2026-group20-speckit/issues/20)。基底 PR #14 merge `e9a29c7`。

**工作區說明**：本輪開始時另一對話已將共享 checkout 切至 `codex/012-result-writeback`，feature.json 指向012。本輪不切分支、不修改該指標；setup-plan 以程序限定 SPECIFY_FEATURE_DIRECTORY=011、SPECIFY_FEATURE=codex/011-time-display、SPECIFY_FEATURE_NO_PERSIST=1 執行，回傳正確011路徑。只改011文件／圖，不替012提交。真正實作／提交前應在011獨立 checkout／worktree整理，避免共用工作目錄互相切分支。

## Summary

以已審閱的三張概念圖為藍圖，在原讀取／驗權之後加入純時間 presenter：有明確偏移量者保持同一瞬間，已知 SQLite UTC 舊值明確附 UTC，其他不明 naive 不猜測；統一以固定 UTC+08:00、24小時至分鐘顯示。教師活動歷史增加建立／開始／結束的明確標籤與顯示 metadata，notes 頁使用同一政策。

本輪選擇唯讀相容，不改 timestamp writer、不做遷移、不新增表、不重新結算。保留 raw API 欄位、嚴格 CatalogDTO／snapshot、授權、排名及既有回填行為。原小時差尚未重現；設計修復可證明的主機時區依賴風險，不宣稱已找到原畫面的唯一根因。

## Technical Context

**Language/Version**: 沿用 Python `>=3.13,<3.14`、少量原生 JavaScript。

**Primary Dependencies**: 沿用 Flask 3.1、Jinja 3.1 及既有 Google 用戶端；時間使用標準庫 datetime、timezone、timedelta、re、dataclasses，不新增 tzdata／dateutil。

**Storage**: 沿用 SQLite 與既有 raw 欄位；無 schema、索引、migration 或資料修復寫入。DisplayTime 為請求內暫存值。

**Testing**: pytest 的來源／狀態矩陣、Flask 暫存 DB／合成 Google fixture、Node 既有 DOM 測試；POSIX 隔離子程序及可用瀏覽器隔離 context 做實際時區矩陣。Windows 不以只設 TZ 當作跨時區證據。

**Target Platform**: 原 Windows 本機 Flask 與桌面／窄視窗瀏覽器；受控 POSIX 測試環境提供不同執行時區證據，非改部署平台。

**Project Type**: 既有單一 Python Web application，不另建服務或前端框架。

**Performance Goals**: 每欄常數時間純運算，不新增 DB 查詢／網路請求，沿用既有輪詢與清單讀取；不改本機2秒活動更新及010的5秒在線目標，不虛構本輪效能量測。

**Constraints**: 資料及Google授權保留；禁止 naive 依主機解讀、禁止雙重加8小時；壞值不能造成500；不改截止、accept_seq、結果版本、lease、授權／presence期限。不得覆蓋 #16／#17 或012的並行修改。

**Scale/Scope**: 現有教師活動清單及 notes 匯入確認、回填預覽／報告／逐格回讀；提供 #19 共用介面。課程／課堂原時間只在既有或後續已確認畫面需要時使用；不擴充學生結果欄位、時區偏好或結算時間。

## Constitution Check

*Phase 0 前及 Phase 1 後各核對一次。PASS 代表本階段設計符合，不等於產品或外部驗收通過。*

| 原則 | Phase 0 前 | Phase 1 後與證據 |
| --- | --- | --- |
| I 決策追溯／雙組 | PASS：Issue20與本次指定固定台北已記錄；原共同需求的待確認不改成已確認 | PASS：不改使用者結果可見範圍或受理規則，2026-11-27使用者回報OpenSpec已確認時間呈現政策，並指定到分鐘；姓名／獨立紀錄待補，不冒認具名確認 |
| II 圖優先 | PASS：原三圖CLI成功；2026-11-27使用者回報同學已審，姓名／獨立紀錄未提供 | PASS：原權限→唯讀來源→解讀→呈現責任不變，只更新圖標題審閱狀態並重渲染；技術mapping見下表 |
| III 動態匯入與回填 | PASS：不讀寫Sheet格位或改答案 | PASS：原預覽、RAW、覆寫與恢復契約保持；時間view不進冪等／來源指紋 |
| IV 機敏及角色 | PASS：只在原驗權後呈現 | PASS：不新增匿名時間路由，不記raw資料／token日誌；學生DTO不擴充 |
| V AI與人工 | PASS：僅規劃，不冒稱執行測試 | PASS：quickstart列教師＋兩組學生及異常、受控／真環境證據；未做不勾 |
| VI 文件一致 | PASS：spec／來源盤點／圖已有對應 | PASS：research／data-model／兩份contracts／quickstart齊備；tasks、analyze、implement、converge與PR仍未執行 |

無需憲章例外。舊憲章／README歷史進度與共同需求應依後續已確認紀錄理解；本輪不藉時間功能改寫其他迭代的驗收或決策。

## Project Structure

### Documentation (this feature)

```text
specs/011-time-display/
├── spec.md
├── source-inventory.md
├── diagram-review.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── time-display.md
│   └── teacher-time-metadata.md
└── quickstart.md
diagrams/011-time-display-{component,class,sequence}.{puml,png}
```

tasks.md 由後續 speckit-tasks 產生，本輪不提前拆任務或勾實作。

### Source Code (repository root; 預計修改，尚未建立)

```text
src/guided_notes/
├── time_display.py                 # 新：純解讀、固定呈現、DisplayTime
├── time_views.py                   # 新：來源／事件／生命週期的唯讀adapter
├── activities/classroom_routes.py  # 原history驗權後加time_display，內部讀phase_version
├── notes/routes.py                 # 原notes_time安全橋接及HTML view model
├── notes/templates/notes/
│   ├── import.html
│   ├── export_form.html
│   ├── export_preview.html
│   └── report.html
├── static/classroom.js             # 原activityList呈現三事件，不再顯示未標籤raw時間
└── templates/workspace/classroom.html # 時區表頭／區塊提示（依既有DOM最小調整）
tests/
├── unit/test_time_display.py
├── unit/test_time_views.py
├── contract/test_time_display_contract.py
├── integration/test_time_display_routes.py
├── integration/test_time_display_preservation.py
├── integration/test_time_display_process_tz.py
└── classroom-time-display.test.cjs
```

**Structure Decision**：保留單一app factory；核心純函式與有來源知識的adapter分開。renderer不查DB／Google，adapter不寫資料；不把格式化規則散落到SQL、JS及模板。

## Phase 0 — Research decisions

[research.md](research.md) 已完成 R1～R7：官方 naive／aware 行為、固定UTC+8與ZoneInfo取捨、SQLite來源、解析白名單、顯示sidecar相容、直接結束證據及Windows／POSIX測試界線。技術選擇沒有未解 NEEDS CLARIFICATION。真實問題定位與可用測試環境仍是待執行證據，不能記成已通過。

## Phase 1 — Design from diagrams

| 圖中責任 | 落實位置 | 不能跨越的界線 |
| --- | --- | --- |
| Access＋Read | 既有owned_classroom／require_teacher及history；notes原owned row／report | 先驗權，無新增繞過路徑 |
| Meaning | time_views.py指定來源／事件，time_display.py嚴格解析 | 不從字串外觀推定任意舊時區；不改raw |
| Display | 同一DisplayTime＋notes_time橋接；JS只顯示server text | 不再依瀏覽器時區轉一次、不重排 |
| Records＋Identity | 原schema／writer／quiz結果原樣使用 | 不新增表、不更新時刻、不重算／變勝組 |
| Sequence異常分支 | status結果與明確文字；純函式捕捉格式／溢位 | 不用現在時間補值，不讓單格使頁面失敗 |

1. **核心**：實作 [time-display](contracts/time-display.md)；任何來源政策只由伺服器adapter選。有效時刻先aware UTC，再固定+08:00，輸出文字不進位。
2. **活動**：history SELECT內部補讀phase_version，已驗權原row外加 [teacher metadata](contracts/teacher-time-metadata.md)。直接關閉由既有版本與已知生命週期證明；只有CLOSED/null不足。保留raw欄位與原ORDER BY，為新欄位加契約回歸。
3. **notes**：既有filter仍可呼叫，使用同presenter；實際事件的label、狀態與 verified_at 的未驗證提示由adapter處理。HTML可加view model，既有JSON preview/report不動。
4. **前端**：activityList的每筆明示建立／開始／結束、區塊台北時區。用textContent；未知metadata版本提示尚未提供，不退回本地Date猜測。保留原歷史請求generation、selection、版本保護與結果按鈕。
5. **資料相容**：無資料更新，無遷移／重新授權。回退程式不需DB回退；既有歷史時刻不變。若實作發現未知舊來源，提示unknown並追加證據，不逕自改raw。

## Validation strategy and traceability

| 群組 | 涵蓋需求 | 預計驗證 |
| --- | --- | --- |
| V01 同一瞬間 | FR001／002／005／008，SC001 | Z、正負offset、+08:00及可信SQL UTC一致；分鐘截取與跨日／月／年 |
| V02 壞值／缺證據 | FR006／007／012，SC003 | date-only、型別、空值、壞日期、超長、溢位、不明naive不500；狀態明確 |
| V03 事件生命週期 | FR003／013／014 | PREPARING、LIVE、直接結束、已開始後缺開始紀錄、關課一併結束及重複關閉 |
| V04 接線與角色 | FR004／011，SC001／005 | 教師metadata、notes HTML、原raw JSON及嚴格DTO不變；匿名／第二教師／跨堂／關課學生仍拒絕 |
| V05 保留資料 | FR009／010／014，SC004 | 暫存007型DB升級／初始化前後精確比對raw timestamps、資格、講義、有效提交、排序／勝組、result_version與snapshot |
| V06 執行環境 | FR001／005／008，SC002 | Windows來源矩陣＋真POSIX三時區子程序；受控瀏覽器不同timezone；mock不冒稱真環境 |
| V07 人工 | SC005 | 原偏差頁定位、教師實際事件區間、兩組結果範圍與預覽／回讀；時區差與時計不同步分開 |

實作後先跑新增核心／contract／HTML／Node，再相關history／writeback／Google／權限回歸；通過後依當時影響決定完整套件回歸。命令及證據記錄見 [quickstart](quickstart.md)。本plan沒有執行上述測試。

## 接線與進入 tasks 前待辦

- 使用者已回報原概念三圖審閱；本次只更新狀態，沒有改角色、責任或分支。若之後契約釐清改圖意，再修圖、CLI重渲染並交同學複核。
- 與 #19／012 確認 presenter簽名、DisplayTime欄位、phase證據與 notes/routes.py／模板修改範圍；目前僅提案，不聲稱已獲另一對話同意。
- #16／#17 分工及規則保持，不改其feature pointer或檔案。各自應用獨立worktree，避免同checkout互切分支及誤提交。
- 確認可執行POSIX時區矩陣與受控瀏覽器的環境；沒有環境時任務可產生但驗收保持未完成。
- OpenSpec時間呈現政策已依2026-11-27使用者回報記為確認；確認者姓名與獨立紀錄仍待補。後續變更共同政策時，先確認並同步共同需求、規格及任務。
- 下一步只到 speckit-tasks，再 analyze；本輪不直接建立tasks或實作。

## Complexity Tracking

沒有憲章例外。兩個小型純讀取模組及一個教師顯示sidecar足以處理；不新增服務、資料庫、時區套件、排程或第二份結果模型。

## 2026-11-27 實作接續

使用者授權以最新 master 實作。已 fetch origin/master，獨立 worktree 位於 `D:/os_final/tmp/011-time-display-implementation`，分支 `codex/011-time-display-implementation`，基底完整 SHA `80510a6bbf6310bf4634052a7a56066f8f1e8baf`（PR #22 合併）。使用 origin/master 建立 worktree 取得等同最新 pull 的內容；沒有對 dirty 的012共享checkout執行pull或切分支。原始規格基底 e9a29c7 保留為歷史。master另有011-numeric-group-labels，本功能仍以完整目錄011-time-display辨識，不改動同學規格。

本對話使用者已同意「011先完成共用時間函式與教師歷史／notes時間接線，012後續沿用並保留名稱／回填入口」。此為T002檔案責任與順序的使用者確認，不冒稱012作者另提供具名審查；本worktree不含012未提交實作。新增可選 `tests/time-display-browser.cjs`，使用現有Chromium及Node WebSocket建立隔離瀏覽器context，不新增產品或測試套件相依。
