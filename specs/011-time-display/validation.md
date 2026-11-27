# 011 時間顯示一致性：實作與驗證紀錄

日期：2026-11-27（Asia/Taipei）；執行者：Codex。以下為未提交工作樹的實際結果，不是人工驗收或真實Google證據。

## 基底、隔離與協作（T001～T004）

- master更新至 `80510a6bbf6310bf4634052a7a56066f8f1e8baf`，包含PR #22 numeric-group-labels。fetch後從origin/master建立獨立worktree，沒有對原dirty checkout執行pull。
- worktree：`D:/os_final/tmp/011-time-display-implementation`；分支：`codex/011-time-display-implementation`。原 `D:/os_final` 的012分支、feature.json及未提交內容保留，沒有stash／reset／清資料。
- 實作基底與規格最初e9a29c7不同；兩份011功能目錄依完整名稱區分。未修改011-numeric-group-labels或012文件。
- T002來源：本對話使用者同意「011先完成時間接線，012後續沿用」。函式與檔案責任見contracts/teacher-time-metadata.md；未冒稱012作者具名另行確認。
- requirements.md：16／16勾選，未修改檢核標記。ignore涵蓋Python cache、.venv、tmp、DB與憑證；無Docker／ESLint／Prettier／Terraform／npm發布配置需要新增ignore。
- 本輪未開啟日常DB、未連真Google、未讀取私有token；只用pytest臨時DB、合成帳號及受控Google provider。

## 證據分類

1. 原使用者回報的小時差：具體頁面／數值仍未知，**未重現原自然案例**。
2. 已核對程式事實：SQLite CURRENT_TIMESTAMP writer為已知UTC來源；notes.now()帶offset；原notes formatter對naive依主機解讀、壞值可能拋例外。
3. 設計政策：固定台北UTC+08:00，24小時制，text到分鐘不進位；原始秒／微秒及instant_utc精度保留。OpenSpec確認依使用者回報，具名紀錄待補。
4. 受控自動回歸：下表實際執行，不能當作真人或真Sheets操作。

## 測試前失敗及修正

- 先新增核心／adapter／contract回歸：3份模組收集失敗，原因為time_display／time_views尚不存在；實作後54項通過。
- HTTP／HTML與Node回歸在接線前失敗：history缺time_display，notes壞值使頁面出錯或不符安全提示；Node仍顯示raw時間。接線後全部通過。
- 初版測試誤假設關課state必回409；實際既有契約是200安全終態、不含activity，results才409。修正新測試符合原契約，沒有放寬或更改產品權限。
- 暫存preservation fixture最初缺Google schema；改為在測試setup初始化合成schema。published_quiz最小fixture未建可選命名metadata，原init-db會補入；改在比較基準前用未修改initializer補齊，之後精確dump比對通過。沒有為測試修改產品schema／initializer。

## 實際自動驗證

所有Python命令在本worktree以 `PYTHONPATH=<worktree>/src`、原 `D:/os_final/.venv/Scripts/python.exe` 執行；不因原venv的editable位置誤用舊src。

| 執行 | 實際結果 | 適用證據 |
| --- | --- | --- |
| 修改產品前 `python -m pytest tests -q --tb=short` | 508 passed、98 subtests passed；91.67s | 最新master基準，不沿用PR14次數 |
| 核心三檔 `test_time_display.py`、`test_time_views.py`、`test_time_display_contract.py` | 54 passed | 同瞬間、分鐘截取、原微秒、缺值／壞值／未知、生命週期、DTO形狀 |
| 最終產品修改後 `python -m pytest tests -q --tb=short` | **575 passed、1 skipped、98 subtests passed**；93.65s | 完整Python回歸 |
| preservation補強首位勝組與原答案斷言後定向重驗 | 2 passed；1.03s | 原有受理序列仍決定勝組、原字串保留；沒有再改產品程式 |
| `node --test tests/*.test.cjs` | **77 passed、0 failed、0 skipped** | 實際activityList、晚到保護、既有學生與匯入回歸 |
| `node tests/time-display-browser.cjs` | **Chrome/158.0.8127.37：三context通過** | 真瀏覽器時區證據，非伺服器TZ矩陣 |
| `git diff --check` | exit 0 | 追蹤檔空白檢查；新檔另作基本格式核對 |

### 真瀏覽器證據（T026）

工具：現有Chrome headless、Node v22.12.0及WebSocket/CDP；新建暫存profile與每次獨立browserContext，無既有cookies／真人登入／Google請求。fixture由實際Python activity_time_display產生，頁面執行原classroom.js的activityList。

UTC、Asia/Taipei、America/New_York三個context各以Intl回讀實際zone，結果皆為：

`建立：2026-11-27 00:03 · 開始：未開始即結束 · 結束：2026-11-27 00:04`

來源包含前日UTC16時及秒59，跨日正確且不進位；含HTML標籤的名稱透過textContent呈現，DOM沒有產生b元素。首次受限環境啟動Chrome失敗；授權隔離headless啟動後三context成功，不把首次失敗記通過。

### Windows／POSIX界線（T025）

本機Windows沒有time.tzset。`wsl --list --quiet`回報尚無可用WSL／Linux，未安裝或更動系統時區。`test_time_display_process_tz.py`已建立真正POSIX子程序矩陣，Windows執行結果為skip；**T025與SC-002伺服器部分仍未完成**。不能拿Chrome三context或手設TZ抵作。

## 保留與角色證據（T028～T031）

- 建立隔離課堂、兩組學生、有效提交及正式已公布結算；客戶端帶相反時計聲明，勝組仍為原先受理組，答案原字串含空白／換行保持。
- 完整DB dump在教師顯示／刷新、init-db、重新create_app及沿用原grant後精確相同，包括raw timestamps、catalog、快照、結果版本、accept_seq、lease／expires及合成密文。只在初始化前為最小fixture補齊原既有可選metadata。
- 另用真正加密路徑的受控Google fixture建立Sheets連接，顯示與init-db後密文／身分／授權狀態精確保留。這不是私人Google授權測試。
- 原匿名／第二教師／學生讀教師history仍被拒絕；學生state沒有time_display，關課後只回原終態且results拒絕。
- 預覽與回填報告原JSON精確保持；HTML讀取沒有新增Sheets read/write，沒有改schema、writer、結算provider、授權／presence TTL或網路預算。

## 需求與完成界線

| 檢核 | 結果 |
| --- | --- |
| FR-001～014 | 已有實作及受控回歸；原自然偏差不宣稱已定位 |
| SC-001／003 | 受控樣本通過 |
| SC-002 | 真Chrome完成；真POSIX server矩陣待環境，不勾整體通過 |
| SC-004 | 臨時DB／合成Google與正式結算保留回歸通過；私人資料未操作 |
| SC-005 | 真人教師與兩組學生未執行，保持未完成 |
| V01～V05 | 受控回歸通過；見上述測試檔及圖對碼 |
| V06 | Windows＋Chrome完成，POSIX未完成 |
| V07 | 尚待真人驗收 |

## 人工 M01～M06（全部未執行）

- M01：找原偏差頁／值；找不到仍記未重現，不假造8小時根因。
- M02：教師及兩組學生一般建立／開始／提交／結束，核對已同步時計的分鐘範圍。
- M03：準備中直接結束，核對開始欄提示及實際結束分鐘。
- M04：刷新／重連／同名歷史／關課，時間固定且學生仍禁讀。
- M05：確認、預覽、更新及回讀各自事件；只讀既有報告即可，不必寫真Sheets。
- M06：原順位、勝組、版本及答案保持。

實作完成不等於人工或整體交付完成；不得提前關閉Issue #20。當前可交付供審查與驗收，完整合併／結案仍需必要證據與同學review。

## 本機分段提交與完成狀態

依使用者先前「每完成一段可測試功能就commit」的持續偏好，核心已分段提交為 `aecb22e`。後續教師接線與驗證文件另成一個commit；本輪不push、不建立PR、不合併或關Issue。完整測試執行於80510a6加本輪dirty內容，之後只增加勝組斷言／文件，勝組補強已定向重驗2項通過。最終SHA以git log核對，不在此寫入自我參照的commit值。

收斂已追加T050／T051；T047保留未完成，等待必要驗證補齊後重驗收斂。M01～M06、真POSIX及相關checkpoint維持未勾，不能宣稱所有任務完成。

最終stage檢查發現新增preservation及兩份unit測試檔EOF多一空行（未追蹤時的逐行檢查未涵蓋EOF規則）；已移除並重新核對整個功能相對master的diff，產品邏輯與測試內容未改。功能提交為aecb22e及772af09，隨後僅格式／此紀錄另存。
