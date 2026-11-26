# Issue #10 驗證紀錄

2026-11-26（Asia/Taipei），Codex 核對 GitHub PR #11 已合併，遠端 master 與本機 codex/010-acceptance-experience 皆為 edb42c3fc6c3b6d36bf8401efd44145c6826b06b，且包含 ea5efbb。SpecKit feature 指向 specs/010-acceptance-experience，T001 完成。

基線 Node 命令為 node --test tests/*.test.cjs，預期全部通過，實際 47 項通過、0 失敗，退出碼 0。T002 的 Python 基線仍待在合併版重跑；先前 PR #11 的 Python 審查結果對應較早的 4982053。Issue #10 尚未實作或人工驗收。

## 自動驗證與實作證據

2026-11-26（Asia/Taipei），Codex 在 edb42c3 基底先執行 `uv run --locked --python 3.13 python -m pytest tests/unit tests/contract tests/integration -q -p no:cacheprovider`。預期無基線回歸，實際 475 項通過、98 子測試通過。

實作後 Node 完整套件 53 項通過，含原生／後端欄位錯誤與重送、關課不被結果查詢卡住、自動結果、同堂歷史選取及晚到回應。Python 匯入、在線、結果、教師工作區、009 歷史、資料庫升級及故障回滾相關檔案共 37 項通過；涵蓋真實路由與測試 Sheets gateway。在線測試以伺服器時鐘覆蓋多頁去重、重複加入、逾時歸零與重連、未授權讀取及不同課堂隔離。

T007 真實 Sheets、T012 真人兩組活動及 T018 三瀏覽器真人在線延遲待執行。瀏覽器休眠或凍結會停止心跳，須以實機記錄背景頁行為。T019 需在取得人工證據後完成交付核對。

## PR #12 審查修正（2026-11-27）

審查發現讀取失敗後後端已進入 failed，前端仍留在原讀取頁；再次按讀取會得到 FLOW_STEP_CONFLICT。新增前端測試先重現權限／暫時錯誤後沒有切換的問題，再修正為查詢伺服器流程狀態，確認 failed 後自動重新載入，呈現既有紅字與 retry 入口。若狀態查詢也失敗，保留原操作錯誤並恢復按鈕，不自動重送讀取。

Node 全套 56 項通過；匯入路由、OAuth 與工作區失敗流程的 Python 回歸 22 項通過。涵蓋失敗後使用 retry 端點成功回到選分頁，以及狀態查詢失敗時仍可操作。審查原 PR head 868e340 時，完整 Python 回歸為 478 passed、98 subtests passed；本次前端修正後以上述相關範圍重驗。真實 Sheets 與真人在線延遲驗收仍保持待辦。
