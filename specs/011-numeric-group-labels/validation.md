# 011 驗證紀錄

2026-11-27（台北時間），Codex 核對 `codex/011-012-student-join` 的 HEAD 為 `e9a29c7`，SpecKit 功能為 `specs/011-numeric-group-labels`，且首版圖已記錄組員審查。Python 使用測試 fixture 的獨立暫存資料庫。

預期基線無失敗。實際 Node 72 項通過，相關 Python 57 項通過，兩者退出碼皆為 0。Python 範圍為加入資格、在線、課堂與教師結果、工作區、009 歷史及回填預覽和作業。

```powershell
node --test tests/*.test.cjs
python -m pytest tests/contract/test_classroom_memberships.py tests/contract/test_classroom_presence.py tests/contract/test_classroom_results.py tests/contract/test_workspace_routes.py tests/integration/test_classroom_history_009.py tests/integration/test_export_previews.py tests/integration/test_export_routes.py tests/integration/test_quiz_classroom_009.py -q -p no:cacheprovider
```

基線對應實作前的版本。011 程式實作及真人驗收尚未執行。

## 實作後自動驗證

2026-11-27（台北時間），Codex 在 e9a29c7 基底的 011 本機工作樹執行驗證。預期組號欄位、現行課堂、結果及回填迴歸全部通過。

- Node 全部 74 項通過。包含新增的本地組號驗證與伺服器欄位錯誤案例。
- Python 課堂加入相關測試檔及回填預覽、回填路由共 114 項通過。使用隔離的暫存資料庫。
- 另執行課堂結果與課堂回填整合 4 項通過，覆蓋進度與結果標籤、HTML 回填預覽與報告、原勝組 ID 和回填資料保留。
- 以一位教師及至少兩組學生操作的人工驗收尚未執行，T014 保持待辦。圖表對照已紀錄，合併前的 Converge、人工證據及組員審查合併檢查 T015 保持待辦。

## 真人驗收交接

原操作者已啟動本機測試版，但教師登入在跳轉 Google 之前顯示 `GOOGLE_NOT_CONFIGURED`。OAuth Web client JSON 路徑的檔案檢查回傳 `False`。使用者決定由已有 Google 設定的組員接手，欄位、師生流程與真實回填尚未回報通過。
