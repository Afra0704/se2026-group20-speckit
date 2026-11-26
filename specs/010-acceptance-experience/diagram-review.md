# Issue #10 圖表渲染與審查

2026-11-26（Asia/Taipei），Codex 於 `codex/010-acceptance-experience` 從 `7ae70542c26690193c2db4e97402d89dcd323c90` 開始 Specify。GitHub 指派事件顯示 Afra0704 於同日 19:56:15 指派給 itsusername15，查詢時無留言。相依 PR #9 在 19:51:31 獲核准，19:51:34 合併。複審紀錄保留 003 的 Sheets 與真人驗收待辦。

從專案根目錄執行下列命令，退出碼 0。

```powershell
$jar = 'C:/Users/User/AppData/Local/Temp/plantuml-speckit-003.jar'
& 'C:/Program Files/Java/jdk-21/bin/java.exe' '-Djava.awt.headless=true' -jar $jar -charset UTF-8 -failfast2 -tpng './diagrams/010-*.puml'
```

九張 PNG 皆核對同名來源、PNG 簽章、尺寸與檔案時間。

| 功能 | 組件圖 | 類別圖 | 時序圖 |
| --- | --- | --- | --- |
| A 匯入欄位 | [366 × 458](../../diagrams/010-import-component.png) | [238 × 303](../../diagrams/010-import-class.png) | [588 × 673](../../diagrams/010-import-sequence.png) |
| B 在線人數 | [535 × 525](../../diagrams/010-presence-component.png) | [296 × 466](../../diagrams/010-presence-class.png) | [534 × 719](../../diagrams/010-presence-sequence.png) |
| C 活動結果 | [362 × 458](../../diagrams/010-results-component.png) | [126 × 697](../../diagrams/010-results-class.png) | [539 × 802](../../diagrams/010-results-sequence.png) |

A 核對欄位修正、伺服器驗證及原匯入流程。B 繪出課堂及身分隔離、多分頁計數與逾時，規則仍待確認。C 核對既有結果投影、自動切換、歷史查閱及晚到回應處理。

2026-11-26，使用者在本對話回報同學已完成審核，依前一輪所指的組件圖、類別圖與時序圖記錄為組員圖意審查完成。審查者姓名及外部紀錄連結未提供。B 的共同規則待雙組確認。若釐清改變圖意，更新對應來源、重新渲染並提交組員複核。

使用者確認 C 的查詢分支釐清後，以上述 CLI 將輸入改為 `./diagrams/010-results-sequence.puml` 並重新渲染，退出碼 0。新版 PNG 簽章驗證通過，尺寸 575 × 852。此版區分結算中續查、無正式資料停止與讀取失敗重試，待組員複核變更的時序圖。

## PR #11 合併後重繪

2026-11-26，使用者回報同學已確認 PR #11。GitHub 顯示 PR 已合併，010 新基底為 `edb42c3`（含 `ea5efbb`）。依 009 更新 B 的固定課堂 ID 與 OPEN 授權，以及 C 的獨立狀態輪詢、OPEN 歷史結果、CLOSED 終止與教師歷史。原有圖意審查保留為歷史，更新處待組員複核。

沿用上方 CLI，輸入 `./diagrams/010-*.puml`，退出碼 0。九張圖均核對 PNG 簽章及生成時間。本輪 B 組件圖 588 × 525、時序圖 571 × 719，C 組件圖 447 × 478、類別圖 159 × 750、時序圖 622 × 1083。

### C 新版圖表複核完成

2026-11-26（Asia/Taipei），使用者在討論 C1 後回報組員已看過 C 的新版圖表，據此記錄 C 的圖意複核完成。組員姓名及外部審查連結未提供。B 的複核及在線統計雙組確認仍待完成。

### B 新版圖表複核完成

2026-11-26（Asia/Taipei），使用者回報 B 的新版圖表已經組員複核，且在線統計規則與驗收門檻已確認。確認者姓名及外部紀錄連結未提供。若接續設計改變圖意，須同步更新並重新渲染。

### 實作後圖表對照

A：欄位提示與授權／讀取錯誤分別落在 workspace lectures/import 模板、import-flow.js 與 workspace routes。B：固定課堂與頁面存活落在 classroom_presence、presence 路由與 student-room.js，教師以授權 groups 端點讀取已去重結果。C：學生結果與狀態輪詢分離，手動歷史優先與關課終止落在 student-room.js，教師結果區沿用 classroom.js 的原授權入口。交付複核仍待真人驗收證據。

B 定案後以相同的 PlantUML CLI 渲染 `./diagrams/010-presence-*.puml`，退出碼 0。三張 PNG 的簽章均檢查通過，時序圖補註 3 秒心跳與 25 秒逾時，組件責任與資料關係沿用已複核版本。
