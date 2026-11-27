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

## 2026-11-27 接手真人驗收完成（使用者回報）

執行者：本 Codex 對話使用者，未另提供姓名。版本：PR #22 `e4c3b00f427ac9f8306c1a1145c68e21d655473c` 的獨立副本。提供的啟動設定採 `instance/issue16-acceptance.sqlite3`、127.0.0.1:5000、既有 Web OAuth 與測試 Sheets 副本。使用者回覆「測試皆已完成」，僅提出同瀏覽器不能同時加入不同課堂；後續確認此為 Issue #17 的每分頁資格隔離範圍。以下依本對話案例記錄回報，不冒稱 Codex 直接觀測。

| 案例 | 操作與預期 | 實際結果 |
| --- | --- | --- |
| 1 | 0、01、全形１、1000、1.0、1e2、空白拒絕，組別欄紅字且保留輸入 | 使用者回報完成，未報異常 |
| 2 | 修正成 1 成功加入，提示清除，顯示第 1 組 | 使用者回報完成，未報異常 |
| 3 | 第二組以帶前後空白的 2 加入，顯示第 2 組 | 使用者回報完成，未報異常 |
| 4 | 999 成功加入，顯示第 999 組 | 使用者回報完成，未報異常 |
| 5 | 教師組別／在線名單顯示第 N 組與正確人數 | 使用者回報完成，未報異常 |
| 6 | 一位教師、兩組學生，第 1 組先送、第 2 組後送，進度正確 | 使用者回報完成，未報異常 |
| 7 | 結束活動後勝組第 1 組、順位正確，學生只見勝組與本組 | 使用者回報完成，未報異常 |
| 8 | 測試 Sheets 回填預覽／報告顯示第 1 組，寫入勝組答案且回讀一致 | 使用者回報完成，未報異常；未提供截圖或 Sheets 連結 |
| 9 | 重整與歷史保留組名、答案、順位及勝組對應 | 使用者回報完成，未報異常 |
| 10 | 不同課堂同號組別的人數、結果及回填獨立 | 資料隔離未報異常；同瀏覽器兩堂資格無法並存，列為 #17 既有待實作範圍 |
| 11 | 關閉 A 後學生顯示終態、教師仍可看歷史，B 正常 | 使用者回報完成，未報異常 |

## 本次 review 與交付補測

Codex 對上述產品版本完整回歸：Python 507 項、98 子測試通過（93.04 秒）；Node 74 項通過。Converge 發現 T009 缺少跨堂同號的回填直接測試，追加 T016 並補到 `tests/integration/test_classroom_notes_integration.py`：核對兩堂同號但不同 ID 的原勝組、兩份預覽／報告及關堂後教師歷史。該檔 3 項測試通過。產品程式未變更，人工結果仍對應原產品版本。

T014 已完成；T015 的規格收斂、圖表對照及審查見 [交付檢核](delivery-review.md)。本節取代前文當時「尚未驗收」的狀態，保留歷程不改寫原紀錄。
