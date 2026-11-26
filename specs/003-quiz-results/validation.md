# 003 實作驗證

**日期** 2026-11-26（Asia/Taipei） · **執行者** Codex · **版本** `codex/003-quiz-results` 工作樹，基底 PR #7 合併提交 `39d6275`。

## 準備與基底

- `.specify/feature.json` 指向 003。規格檢查表 11/11，無 implement hook。D01、D02、D08、D22 的確認與組員審圖依 [diagram-review.md](diagram-review.md) 所載回報。
- 用 `git archive` 隔離基底，使用已依 `uv.lock` 建置的 Python 3.13 環境執行 `python -m pytest tests -q --tb=short`，414 passed、98 subtests passed。基底 Node 測試 26 passed。工作樹沒有放入開發 DB 或憑證。

## 分段受控驗證

| 範圍 | 證據 |
| --- | --- |
| US1 受理及重試 | 新測試先在基底重現缺 schema、無正式 provider 和無重試 UI。已驗空白／不完整答案拒絕、原字串、同操作衝突、被取代的舊收據不復活、同分頁重整仍可手動重試、教師進度與學生投影隔離。 |
| US2 截止及結算 | 兩個工作階段受理與關閉的兩種交易先後、兩組並行、關課、名次與恢復均使用暫存 SQLite。驗證已發布版本保持原樣、故障回滾、重啟完成待辦、同堂 OPEN 新成員的歷史可見範圍及 CLOSED 的原瀏覽器恢復。 |
| US3 001 接線 | Google 教師模式的 HTTP 整合用受控 Sheets，實際走正式 003 提交與結算、嚴格 v1 快照驗證、原 001 預覽、確認、逐格寫入與讀回。涵蓋單題、題組、移位版型、無勝組略過、故障恢復與移除講義後的歷史版本。 |
| 啟動與圖表 | Google 教師模式、暫存 DB、正常 app factory 及 `init-db` 通過；本機 Flask 的首頁、學生入口及送答腳本均回 200。三圖對照見 [diagram-review.md](diagram-review.md)。 |

## 最終自動回歸

- `python -m pytest tests -q --tb=short`，427 passed、98 subtests passed，322.51 秒，退出碼 0。使用已依鎖定檔安裝的暫存環境及目前工作樹的 `src`。
- `node --test` 執行 `tests/*.test.cjs` 共 13 檔，29 passed、0 failed。包含重整後同次重試、逐小題結果及晚到回覆不覆蓋目前活動。
- 初次整合測試曾用只有部分欄位的舊替代清單，正式結算按既有嚴格驗證拒絕發布。改用 001 的完整契約範例及既有匯入流程重驗，全套通過。驗證器不變。
- `git diff --check` 通過。未在實際 Google Sheets、日常開發 DB 或私人憑證上操作。

## 尚待驗收

- T035，未操作真實 Google Sheets 副本，也未寫入團隊原始講義。
- T037，教師及兩組學生真人驗收、瀏覽器恢復操作與兩秒更新目標尚未實測。
- T040、T041，最終交付前收斂及組員 PR 互審。依約由成員使用 GitHub 帳號提交。

## PR #9 審查修正

2026-11-26，以兩個受控 Node 案例重現舊表單的 201 或 409 晚到時，會清掉新表單的待重試送答。修正後只清除識別與該回覆相符的操作。新送答若未收到回覆，仍能用原識別和原答案重試。完整 Node 測試 31 passed、0 failed，退出碼 0。此輪只變更前端及其測試，未重跑 Python 或執行真人／真實 Sheets 驗收。

## 最新提交重驗與合併前核對

2026-11-26，在 `ce2a470` 重新執行完整 Python 與 Node 回歸，427 Python、98 子測試、31 Node 通過，兩套退出碼皆為 0。三張 PNG 完整性和最新提交的 Git 差異檢查通過。

[Analyze／Converge 報告](analysis.md) 已產出。獨立使用暫存 DB 驗證準備中直接結束，課堂入口通過，相容入口回 409 且沒有結算。新增 T042 追蹤修正，T040 保留至重驗；真人、真實 Sheets 與 PR 複審待辦依原任務追蹤。

## T042 修正後重驗

2026-11-26，先以新回歸確認相容路由及結束按鈕會失敗。修正後，課堂與相容入口皆可直接結束準備中活動並正常結算。新回歸涵蓋相容入口的擁有權、無勝組、重複關閉及重開限制。相關 22 個 Python 測試通過；完整 pytest 為 428 passed、98 subtests passed，473.89 秒，退出碼 0。完整 Node 測試 31 passed、0 failed。T040 與 T042 完成，T035、T037、T041 保持未完成。
