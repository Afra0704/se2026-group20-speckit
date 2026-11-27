# Issue #19 實作驗證紀錄

日期：2026-11-27（Asia/Taipei）；執行者：Codex。

## 本輪狀態

接續 implement 時已找到本機 #20 實作，技術相依已解除，US1–US3 已完成本機接線。C1-A–C 雙組確認保持有效。下文 T003 缺口為前次歷史，以本節及文末接續紀錄為最新狀態；真人及真 Sheets 均未驗收。

## 基底與工作區（T001）

- 起點 `e9a29c71caf2dd30fc72997fdd29441a35be4ae7`，分支 `codex/012-result-writeback`；feature pointer 保持 `specs/012-result-writeback`。
- GitHub API 核對 PR #22（Issue #16）已合併，head `86c59bfcd4aa2ee7e40e7984d0ae14df0daa4293`；fetch 後以 `git merge --ff-only origin/master` 快轉至 `80510a6bbf6310bf4634052a7a56066f8f1e8baf`。
- 共用文件暫存後恢復，發生內容衝突；保留上游 #16 與本機 #19／#20 的全部紀錄，移除衝突標記並解除未合併狀態。文件維持未暫存，未把其他功能內容提交。保留 `codex-012-preserve-shared-requirements` stash 作額外備份，沒有刪除。
- 原 011 時間規劃、012 規劃／圖表及其他未追蹤檔保留。未操作操作者資料庫、OAuth key 或 Sheets，未 push、未建立新的 commit 或代發 GitHub 留言。
- `.gitignore` 已涵蓋 Python venv／cache／egg-info、前端依賴／build、環境設定、憑證、DB／instance、tmp／logs；本功能不引入 Docker／Terraform／套件發布工具，不新增無關 ignore 檔。
- requirements checklist 唯讀檢查：16 項全部通過、0 未勾選；未修改清單。`.specify/extensions.yml` 不存在，before_implement／after_implement 無 hook。

## #16 實際契約（T002）

- 共用模組：`src/guided_notes/activities/classroom_membership.py`。
- `group_number(value)`：依共同 trim 字元處理輸入，接受 `[1-9][0-9]{0,2}`，回傳 canonical 字串；無效值 HTTP 400 INVALID_GROUP_NUMBER。
- `group_label(name)`：canonical 數字字串回「第 N 組」；非 canonical 舊值原樣回傳。#19 不猜舊文字，不以 ID 推組號；對新正式課堂的不可格式化勝組須在 #19 resolver 明確報資料錯誤，不能把 passthrough 當合法數字組標籤。
- 組號仍存在 `classroom_groups.name`，組別身分仍是原 `classroom_groups.id`＋classroom_id；沒有新增 group_number 欄位。正式結算使用字串型 winner_group_id，須由原堂映射實際記錄。
- PR22 已提供 `notes.routes.export_group_labels(preview)` 的原堂 HTML 標籤投影，#19 後續應沿用 formatter 並集中補原堂校驗／JSON／報告容錯，不複製 formatter 或只為標籤另改快照。

## 實際測試

命令：`.venv/Scripts/python.exe -m pytest tests/contract/test_classroom_memberships.py tests/integration/test_classroom_notes_integration.py -q`

結果：**10 passed in 3.96s**，exit 0；使用測試本身的受控／臨時資料。範圍為已整合 #16 的組號加入與課堂回填相容，不代表 #19 新功能通過，也不代表真人／真 Google 驗收。

## T003 相依缺口與接續條件

- 本機 `specs/011-time-display/contracts/time-display.md` 已有共用介面提案 `present_time(raw_value, *, event_kind, source_policy='unverified', occurrence='unknown') -> DisplayTime`。
- 最新政策：台北 UTC+08:00、YYYY-MM-DD HH:mm、截取不進位，原始秒／小數秒保持；政策已確認。
- 本輪查核 `src/guided_notes/time_display.py` 不存在，遠端 PR 清單尚無 #20 可整合提交；當時 011 本機只有規劃產物。因此尚無可呼叫的實作／合流 SHA，T003 不可勾選。
- 不以原 `notes.routes.taipei_time` 充當 #20 helper：其 naive 依 host 解讀、缺壞值防護正是 #20 要處理的範圍。也不為 #19 建第二套時間核心。
- 接續需要 #20 提供可引用的共用模組實作／提交（或既有本機實作的明確位置）。取得後完成 T003，依序核對 T004，才開始 Foundation 及三故事。
- 本次未執行 #19 完整回歸、真人教師加兩組或兩份真 Sheets；T003–T046 保持未完成。

## 接續實作：相依、測試與範圍

- 發現另一個本機 worktree `tmp/011-time-display-implementation` 已有時間實作，將 #19 分支快轉至其提交 `4199675`；依賴核心 `aecb22e`、教師接線 `772af09`。沒有修改該 worktree 或其任務／人工勾選。
- 本機未追蹤的 011 規劃與六張圖先移至 `tmp/012-before-time-integration` 保留，再取得已提交新版；共同需求衝突保留上游與本機紀錄，文件回到未暫存狀態。額外保留 `codex-012-before-time-integration` stash，不刪任何備份。
- 實際共用 API：`time_display.present_time`、`time_views.activity_time_display`、`notes_time`／`readback_time`。欄位事件分開、台北至分鐘、原始精度與原 writer 保持。
- 新增 context unit 測試先因模組不存在失敗；實作後連同時間核心 **62 passed**。新增入口整合三案先缺 activity_context／全無勝組提示而失敗，接線後 **3 passed**。前端表單兩案先失敗，接線後通過。
- 正式課堂／既有回填／授權等定向回歸：**74 passed、5 subtests passed**；正式課堂歷史與 restart／恢復定向回歸：**29 passed**。最後新增分鐘／group ID 與組號分離契約及 unit：**15 passed**。以上批次有重疊，不相加當總數。
- 完整 Node：**82 passed，0 failed**（`tmp/012-node-final.txt`）。完整 Python 最終結果待下方補記；前輪已指出四個問題並逐項修正：動態課堂狀態的新增投影測試預期、同來源寫後舊預覽需明確更新、測試假身分缺重連 helper、虛構活動重連返回不應反射未驗權表單。
- 沿用原 snapshot、result_version、順位、來源辨識與寫入器；新增的標籤／context 僅在教師 DTO。壞 mapping 的歷史頁回 200 並顯錯誤，原操作狀態保持，確認／恢復禁止新寫入。測試驗過 Google 呼叫前拒絕、來源讀完後保存前重驗、原操作冪等可讀及重啟後固定勝組恢復。
- JSON／HTML 的 context 包含原課程／課堂／活動、講義版本／來源、原事件與原結果返回 URL。全無勝組 UI 不顯確認表單；低階全 skip 相容確認保持零寫入。
- Q01–Q12 自動對應範圍已測，不代替真人；Q13 的兩份真 Sheets 格值／合併／格式仍未實際操作。沒有操作真 DB、憑證、Sheets 或對外發訊息。

## 最終自動結果與交付待辦

- 完整 Python：**607 passed、1 skipped、98 subtests passed，128.84s**，exit 0；命令 `.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -q --tb=short`，輸出 `tmp/012-python-final.txt`。唯一 skip 為 #20 的真 POSIX tzset 矩陣，Windows 不冒稱跨時區程序驗證通過。
- 完整 Node：**82 passed、0 failed**，exit 0；將 tests/*.test.cjs 的 FullName 陣列傳給 `node --test`，輸出 `tmp/012-node-final.txt`。
- 完整回歸後額外補充同名活動／重用同講義版本 1／2：`tests/integration/test_export_context_history.py::test_same_title_reused_lecture_keeps_each_fixed_version_and_answers` **1 passed**；未改產品程式，不把額外單案冒稱為完整 608 項。
- 核心本機提交：`49b8a70`。教師入口／模板／回填接線與其測試及文件另作下一個本機提交；確切提交以 git log 為準，不寫自我參照 SHA。
- 已完成 T001–T042；T045 的技術檢核將三項交付證據追加為 T047–T049，詳見 convergence.md。T046 僅準備本機提交與 pr-draft.md，不代表已發 PR 或同學已核准。
- 真人 T043／T047、真 Sheets T044／T048、技術互審 T049 未完成。原 #20 的 POSIX／人工限制仍保留，不因本輪整合更改其任務狀態。
