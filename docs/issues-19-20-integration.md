# Issue #19／#20 統一版本

日期：2026-11-27（Asia/Taipei）；執行者：Codex。

## 唯一執行入口與基底

- 工作目錄：`D:\os_final`。
- 整合分支：`codex/integrate-issues-19-20`。
- 本輪 fetch 後最新遠端 master：`80510a6bbf6310bf4634052a7a56066f8f1e8baf`，包含同學已合併的數字組號功能。
- 整合起點：`7c74ba1766ddfc0dea6806441bc293c24de3549d`。已以 Git ancestry 核對，此提交同時包含上述 master、#20 的 `4199675` 與 #19 的 `49b8a70`／`7c74ba1`；不重複 cherry-pick、不改寫既有提交。
- 原 `tmp/011-time-display-implementation` 保留為分段開發紀錄；本次驗收與後續開發統一使用主工作目錄，不再從該舊工作目錄啟動。
- `.specify/feature.json` 維持 `specs/012-result-writeback`；#20 規格仍以完整路徑 `specs/011-time-display` 辨識，避免與 master 上的 `011-numeric-group-labels` 混用。

## 已整合功能

1. #19：從目前／歷史活動結果預覽回填，保留原課程、課堂、活動、講義與結果版本；原堂勝組校驗及數字組號顯示，返回原結果選取。
2. #20：建立／開始／結束及 notes 相關事件統一台北時間、24 小時制、`YYYY-MM-DD HH:mm`；只截取、不進位，原秒／微秒及排序依據不改。
3. 沿用原覆寫、冪等、先回讀恢復與安全重新授權；沒有新增資料庫遷移或變更結果快照。

本次沒有重做產品實作。整理共同需求文件重複的 #20 政策紀錄，保留兩組確認及後續 #19 實作歷史；更新 README 與兩份 quickstart 的統一入口。

## 整合回歸

執行版本：上述 `7c74ba1` 的產品程式，加本輪文件及瀏覽器驗證腳本修改。測試使用原 `.venv`、明確 `PYTHONPATH=D:\os_final\src` 與隔離暫存 DB，不操作日常 DB、私有憑證或真 Sheets。

| 檢查 | 本輪實際結果 |
| --- | --- |
| `.venv\Scripts\python.exe -m pytest tests -q --tb=short` | **608 passed、1 skipped、98 subtests passed**；110.40s |
| `node --test tests/*.test.cjs` | **82 passed、0 failed** |
| `node tests/time-display-browser.cjs` | **Chrome/158.0.8127.37，UTC／Asia/Taipei／America/New_York 三個隔離 context 通過** |
| `git diff origin/master --check` | 通過 |
| master 及 #20 是否為整合版本祖先 | 兩項皆通過 |

Chrome 腳本首次因擷取的 activityList 已增加 #19 狀態、測試環境卻缺少 returnSelectionPending 而失敗；本輪補齊狀態並驗證返回原活動 a。重跑後三個時區皆保留活動 a，顯示建立 00:03／直接結束提示／結束 00:04，名稱以純文字呈現。沒有為此修改產品程式或放寬斷言。

唯一 Python skip 為 #20 的真 POSIX tzset 矩陣，Windows 不支援。真 Chrome 證據不抵作伺服器矩陣；原教師加兩組、真 Sheets 與同學互審待辦維持原紀錄，不因統一版本而代勾。

## 啟動本版本

先由操作者停止原本的 Flask 服務，再於原本已載入私人設定與測試 DB 設定的 CMD 執行：

```cmd
cd /d D:\os_final
set "PYTHONPATH=D:\os_final\src"
.venv\Scripts\python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

瀏覽器重新載入，確保取得新的 JavaScript。不要另用舊 011 worktree 的 src 或改用未載入原設定的終端；本次沒有刪除、重建或更換 DB／Google 授權。

## 提交界線

本輪將整合入口、文件整理與瀏覽器驗證修正建立本機 commit，保留 #19／#20 分段提交歷史；未 push、未發 PR、未合併回 master、未關閉 Issue。原無關的未追蹤檔保留，沒有加入提交。
