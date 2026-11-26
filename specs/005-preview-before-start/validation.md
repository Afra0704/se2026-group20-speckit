# 005 實作與驗證紀錄

日期：2026-11-25。執行者：Codex；人工驗收者姓名待補。起點 commit：812037a，功能分支 codex/005-preview-before-start，尚未 commit／push／建立或合併 PR。D18 是使用者已回報大家同意的行為補強，不要求重表決。

## 環境與資料範圍

- Python 3.13.1、Node v22.12.0；沿用現有 .venv 與套件，不新增依賴。checklists/requirements.md 16/16，僅讀取、未變更標記。
- 已新建 `instance/classroom-005.sqlite3` 並成功 init-db，為本次空白開發 DB；未建立教師，未複製既有活動／講義／token。init-db 測試確認重跑保留新資料。
- 舊 DB 未刪除；憑證檔未讀取，未呼叫真實 Sheets 或雲端寫入。所有自動業務測試使用臨時 DB 與受控 provider。
- .gitignore 已涵蓋 instance、SQLite、tmp、環境及憑證；未發現需新增 Docker／ESLint／Terraform 等配置的專案檔。

## 自動測試與修復

1. 新後端案例於修正前執行：2 failed，重現 current_activity_id 為空、第二次建立仍 201。修正後初批 10 passed；補上交易內故障回滾與跨課堂案例後，本檔 12 個案例通過，連同 memberships 共 13 passed。
2. 前端新增 5 個 Node 案例，與既有四個 JS 檔合跑共 9 個 Node test 通過，退出碼 0。涵蓋單題／題組、準備停用、同 id 開放、CLOSED、斷線與復線、清除舊答案、教師建立限制、準備中結束入口、finally、history 失敗與晚到狀態。
3. 首次完整 Python 回歸：219 passed、98 subtests passed、1 failed，79.90 秒。唯一失敗為 memberships 舊測試仍預建兩活動；改成逐次建立／開始／結束，並核對新增發布步驟後的 state_version。保留原組別、隔離與切換斷言，未放寬安全預期。
4. 修正後完整 Python 回歸：`.venv/Scripts/python.exe -m pytest tests -q --maxfail=2`，**222 passed、98 subtests passed，81.05 秒，退出碼 0**。JavaScript 五個檔案合跑 **9 tests passed，0 failed，退出碼 0**。PlantUML CLI 重渲染三圖退出碼 0，git diff --check 通過。結果依目前未提交工作樹，不冒稱為新 commit。

## 需求與證據

| 需求／成功條件 | 自動證據 | 人工狀態 |
| --- | --- | --- |
| FR-001/002、SC-001/002 | test_create_publishes_safe_preview_to_two_groups、Node 渲染／標號／名稱案例 | 兩組真實畫面與 5 秒計時未執行 |
| FR-003/004、SC-003/004 | test_submission_boundaries_and_close、Node 同 id PREPARING→LIVE→CLOSED | 真實開放與計時未執行 |
| FR-005/009、SC-005 | Node 復線／晚到狀態／finally、catalog 失敗及交易中故障回滾 | 真人刷新／復線未執行 |
| FR-006 | stale submission／close 邊界、非目前操作拒絕、DB CLOSED trigger | 真人換場／關課未執行 |
| FR-007 | 授權／CSRF、學生安全欄位白名單、跨課堂拒絕、名稱純文字 | 人工資料可見範圍未執行 |
| FR-008、SC-006 | 雙獨立教師客戶端／連線 barrier 建立、一 201 一 409、無殘筆；準備／LIVE 拒建；結束重建與 init-db 保留資料 | 空白開發 DB 首次設定與單活動人工驗收未執行 |

## 與同學的接線需求

- 課堂 state.activity 新增 title，題目／提交契約與 001 catalog 不變。
- 建立會發布 PREPARING 並增加 state_version；不能預建下一場，409 ACTIVITY_IN_PROGRESS 有中文提示。
- 目前 PREPARING 及 LIVE 均可 finish；結束不是結算完成，不自行產生勝組。
- 同堂不接受非目前活動 start／finish，關課會結束準備或搶答活動。
- 以 005 空白 DB 驗收；原本預建多場的測試須改依序操作。
- 正式 003 受理／排名／結算及真實雲端回填仍由原任務追蹤，本次不代做或代驗收。

## 待執行人工驗收

T033、T034 保持未完成。依 quickstart 由教師、甲組、乙組三個獨立瀏覽器執行，記錄姓名、日期、版本、預期／實際、計時及去機敏證據。沒有實做不得填通過。

### 首次人工回報與執行環境修正

2026-11-25 使用者回報：準備活動無法結束、學生看不到題目，並提供 Chrome 密碼外洩警示截圖。本次驗收記為失敗／待重驗，不勾人工任務。

唯讀查核確認 5000 埠仍為 10:22:26 啟動的舊 Python 程序；它的靜態 JS 已與新工作樹相同，但教師頁仍是舊快取模板。004 DB 有活動，005 DB 有一位教師但零活動。這說明前次操作仍落在舊執行環境，而非已啟用 005 後端。

已停止先前由 Codex 啟動的舊測試服務，重新以目前功能分支與 classroom-005.sqlite3 啟動 5000。HTTP 檢查教師模板及 JS 的 005 標記均存在，狀態 200。新 session key 使原登入失效，需老師重新登入、重新建立課程／匯入講義／建立課堂，學生重新加入新課堂。未刪 DB、未重設密碼、未讀憑證內容。產品流程仍需使用者重驗，不把 HTTP 檢查記為人工通過。

密碼警示來自 Chrome 密碼管理員，不是系統產生的錯誤。檢查目前建立與登入程式採 generate_password_hash/check_password_hash，登入回應不返回密碼；本次未發現這兩條路徑記錄明文密碼，但這不是全面安全稽核或未外洩證明。使用者應更換該組已被警示的密碼，測試密碼不與其他帳號共用；不得為消除警示而停用瀏覽器檢查。

## PR 草稿（僅準備，未送出）

標題：補齊建立活動後預覽與同堂單一未結束活動限制

內容：建立活動立即向同堂學生顯示固定版本題號與停用作答欄，開啟搶答後才可輸入／提交。以寫交易與 DB 防護拒絕第二個未結束活動，支援準備中直接結束，保留同堂分組與已結束歷史。沿用正式 003 接線限制；驗收使用空白開發 DB，不遷移舊測試資料。

審查重點：activity.title 契約、單活動與交易競態、準備中結束、前端 finally／斷線恢復、人工驗收未完成項及 003 邊界。自動測試結果依本頁最終數字填入；同學審查與人工結果待提供。

## 2026-11-26 跨功能人工驗收補充

本輪使用者逐步操作的真實Google／瀏覽器驗收，集中記錄於 `specs/008-teacher-course-workspace/validation.md` 的「真實 Google 操作進度」及後續第18–39步紀錄。已涵蓋兩教師隔離與權限恢復、教師登出保留學生、兩組學生全文／階段／同堂活動／恢復、單題移動欄列與建立／開始同步不到1秒、純文字／換行／Unicode及來源答案隔離、來源修改保持活動快照、重啟資料保留等相關子項。

證據為使用者回報；操作者姓名及瀏覽器版本未提供。依原聚合任務要求，未直接將整項人工任務勾選；仍需具名介面／圖意互審、未執行的子情境及正式003／回填整合。後續引用已取得證據，只補缺項，不要求重做已確認操作。
