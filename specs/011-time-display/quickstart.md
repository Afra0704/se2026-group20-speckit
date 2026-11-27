# 011 驗證操作指南（計畫，尚未執行）

本輪只規劃。下列新測試檔、presenter及metadata尚未實作；不可把命令或預期結果當成實際通過。本文件不包含實作程式、migration或完整測試碼。

## 1. 前置與工作區

以 PR14 合併基底 `e9a29c7` 與之後已確認的相關整合為準。開始前確認自己的011分支／獨立worktree與未提交文件，不在同一checkout切換而覆蓋012、#16或#17。保持原Google Web client、私有key、DB與環境；不清DB、不換key、不貼設定值。

需要執行011的SpecKit命令時，在該命令的程序設定 `SPECIFY_FEATURE_DIRECTORY` 為011絕對目錄、`SPECIFY_FEATURE=codex/011-time-display`、`SPECIFY_FEATURE_NO_PERSIST=1`，避免改另一對話的feature.json。實作／提交應在011自己的checkout完成。

## 2. 實作後自動驗證

以下為 PowerShell；從自己的repo根目錄執行，路徑依checkout調整。只使用臨時DB與合成帳號，測試不能沿用日常DATABASE設定。

```powershell
Set-Location D:\os_final
$env:PYTHONPATH = 'D:\os_final\src'
& 'D:\os_final\.venv\Scripts\python.exe' -m pytest tests/unit/test_time_display.py tests/unit/test_time_views.py tests/contract/test_time_display_contract.py tests/integration/test_time_display_routes.py tests/integration/test_time_display_preservation.py -q --tb=short
node --test tests/classroom-time-display.test.cjs
```

預期：契約樣本全部一致；無效值只顯示提示；原raw欄位、排名／勝組／版本及資格精確保留。相關既有 `test_workspace_history.py`、`test_export_routes.py`、`test_writeback_restart.py`、Google授權及009關課權限再依影響回歸。測試檔是否存在由implement完成後核對，不在plan建立空測試騙過收集。

## 3. 真跨時區與瀏覽器證據

在Windows可先跑來源與偏移參數化、防主機依賴測試。`time.tzset` 在Windows不支援，不能只改TZ環境變數就勾SC002。

在已有POSIX CI／隔離環境執行 `python -m pytest tests/integration/test_time_display_process_tz.py -q`：每個子程序分別設定UTC、Asia/Taipei及另一非台北時區並呼叫tzset，再用同一受控樣本核對。父程序、操作者系統設定不改。沒有此環境時記為未執行／平台不支援，不將skip當通過。

瀏覽器以可用的受控獨立context設定不同timezone，或已有不同時區環境，核對同樣顯示。不得修改操作電腦時鐘／時區來測試；不要求為本功能新增前端框架。記錄使用工具、版本、時區與實際結果。

## 4. 教師＋兩組學生人工驗收

沿用原已登入教師與測試課程，可使用既有可編輯講義副本。只有啟動既有服務／讀既有紀錄不需重新授權。若原服務尚在執行舊版本，先由操作者停止後在原載入私人設定的CMD啟動；不要另開未載設定的終端取代。

```cmd
cd /d D:\os_final
.venv\Scripts\python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

| 案例 | 操作 | 預期 |
| --- | --- | --- |
| M01 原偏差 | 找出原本顯示錯時的歷史／報告，記錄頁面與欄位 | 如未找到，記原問題未重現，不虛構差8小時 |
| M02 一般生命週期 | 教師建立活動、開始搶答；兩組同題提交；結束活動。觀察開始／結束按下前及收到成功回應後的電腦時間 | 建立／開始／結束各自有標籤，至分鐘，時區清楚。時計同步時，顯示分鐘落在操作前後時計各截取至分鐘的含端點範圍；跨分鐘時兩端皆可能有效，自動測試另核對原始事件時刻，不是按目前時間重畫 |
| M03 直接結束 | 新建另一活動，準備中直接結束 | 開始欄為未開始即結束；結束欄用實際事件時間，無勝組等原行為保持 |
| M04 歷史與重載 | 刷新、重連、選同名不同活動；結束課堂後教師查看歷史 | 原活動各自不混，時間不被重試刷新；學生仍禁讀關閉課堂 |
| M05 notes | 查看匯入確認、回填預覽、既有回填報告更新及回讀 | 正確事件用途、台北至分鐘；時間不被當作來源最近修改或結算時間 |
| M06 結果保留 | 比較原順位、勝組、原字串、講義／結果版本 | 完全相同；學生在課堂開放時仍僅原公布範圍 |

M05 檢查既有報告不需再次寫入Sheets；若要新回填／回讀，只用明確測試副本，沿用正常預覽與覆寫確認。本計畫不授權自動操作Google。壞值／時區不明採暫存fixture或隔離環境，不能改日常DB製造錯誤。

## 5. 記錄格式與完成界線

每項記日期（Asia/Taipei）、操作者、完整commit／dirty狀態、平台／瀏覽器、頁面／事件欄位、輸入或受控資料來源、預期／實際與證據類別。可記合成時間，不記憑證、raw OAuth、其他組秘密或私人來源內容。

將「已重現缺陷」「靜態風險」「設計選擇」「受控回歸」「真跨環境」「人工觀察」分開。時計不同步與時區錯誤分開定位，不能靠時區修正宣稱已校時。缺環境或未做案例保持未完成。實作後再做圖對碼、analyze／converge與PR互審，本文件本身不勾驗收。

## 2026-11-27 已實作版本與實際執行位置

本輪版本在獨立工作目錄 `D:\os_final\tmp\011-time-display-implementation`，共享 `D:\os_final` 仍是012，勿在原目錄啟動而誤測舊程式。原 `.venv` 可重用，不需重裝套件。

```powershell
Set-Location D:\os_final\tmp\011-time-display-implementation
$env:PYTHONPATH = "$PWD\src"
& D:\os_final\.venv\Scripts\python.exe -m pytest tests -q --tb=short
node --test tests/*.test.cjs
node tests/time-display-browser.cjs
```

最後一項使用新建暫存Chrome設定檔與UTC／台北／紐約context，只讀合成樣本及實際activityList函式，不連Google、不使用既有cookies；Chrome不在預設位置時設定TIME_DISPLAY_CHROME，Python不在原環境時設定TIME_DISPLAY_PYTHON。此可選腳本沒有新增套件依賴。

人工M01～M06仍未執行。要啟動此版本，先由操作者停止舊服務；沿用原載入私人設定的CMD，將工作目錄改成本worktree、PYTHONPATH改為本worktree的src，呼叫原 `.venv` Python。DATABASE必須明確使用操作者選定的測試DB，不能因工作目錄變更誤建空白DB或自動刪除原DB。此文件不提供猜測的私有DB或key路徑。

## 2026-11-27 統一版本入口

使用者要求#19／#20統一版本；目前請以 `D:/os_final` 的 `codex/integrate-issues-19-20` 為準，最新master基底80510a6，兩項功能均已包含。前文分段worktree／尚未接線說明為歷史，勿再用舊011 worktree驗收此整合版。統一啟動及實際回歸見[整合紀錄](../../docs/issues-19-20-integration.md)，原人工／POSIX／真Sheets狀態不因建立整合分支而代勾。
