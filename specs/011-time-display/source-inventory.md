# 時間來源與顯示盤點

日期：2026-11-27；執行者 Codex；基底 `e9a29c7`。本輪僅唯讀檢查程式，未開啟操作者 DB、未寫入真 Sheets、未調整主機時區／時鐘、未執行產品實作測試。

## 證據分類

- **使用者回報**：搶答結束時間與電腦相差幾個小時，分鐘相同；具體頁面、數值與截圖未提供，未重現原案例。
- **已驗證事實**：下表直接核對基底程式／結構與呼叫位置。這是靜態盤點，不是活站觀察。
- **設計選擇／假設**：固定台北、顯示至秒、已知 UTC 舊紀錄的來源解讀，見 spec；未宣稱雙組已確認。
- **待實測**：真實問題畫面、不同執行時區、舊資料涵蓋率、直接結束／關課事件、完整教師與兩組學生驗收，留給 plan／tasks。

## 來源 → 傳遞 → 畫面

| 語意 | 已核對的來源 | 傳遞與現況 | 需規格化的界線 |
| --- | --- | --- | --- |
| 課程／課堂建立與關課 | `activities/schema.sql` 的 courses.created_at；`classroom_schema.sql` 的 classrooms.created_at／closed_at；建立預設與 close 使用 CURRENT_TIMESTAMP | classroom_routes.courses／classrooms 取得原值，工作區主要展示名稱／狀態；並非每欄都已有畫面 | 已知本產生流程為 UTC 無 offset 字串；不據此推定任意外來字串同樣可靠 |
| 活動建立 | classroom_activities.created_at，CURRENT_TIMESTAMP | `activities/classroom_routes.py` activities 清單原值傳遞；`static/classroom.js` loadActivities 直接拼 activity.created_at | 清單此處實際是建立時間，沒有明示時區，不能直接認定使用者看到的就是結束欄位 |
| 開始搶答 | classroom_routes.phase/start 更新 started_at=CURRENT_TIMESTAMP | 活動清單包含 started_at；歷史目前主要用 created_at | 若顯示開始欄位，需使用本值；未開始／直接結束的 null 需分辨 |
| 活動結束／關課一併結束 | phase/finish 或 close 更新 classroom_activities.closed_at=CURRENT_TIMESTAMP；後者另記 classrooms.closed_at | 同一活動清單包含 closed_at；重複 close 先返回，不應更新成目前時間 | 區分活動與課堂結束，現有防重複行為需回歸，不把格式修正當事件重寫 |
| 結算 | `quiz/schema.sql` 與 `quiz/settlement.py` 保存 snapshot、results、result_version，沒有獨立 settled_at | 師生結果由已公布快照提供，排序依 accept_seq | 不宣稱目前有結算時間；不新增假欄位、不重算結果；accept_seq 不轉成時間排行 |
| 匯入確認 | `notes/schema.sql` notes_catalogs.confirmed_at；repository 寫入使用 now() | notes/import.html 以 notes_time 顯示 | now() 來自 datetime.now(timezone.utc).isoformat()，含明確偏移 |
| 回填預覽 | notes_export_previews.created_at，repo.now() | export_form.html 與 export_preview.html 走 notes_time | 是本系統預覽建立時間，不是 Google 講義最後修改時間 |
| 回填作業建立／更新 | notes_write_operations.created_at／updated_at，writeback 使用 repo.now() | writeback.get_report 回 updated_at；report.html 標示更新時間並走 notes_time | 更新可因恢復而改變，不能稱為活動結束或原作業首次完成時間 |
| 逐格回讀核對 | notes_write_items.verified_at，_save_items 僅 verified 時寫 repo.now() | report.html 以 notes_time 顯示；空值目前顯示破折號 | 未驗證不能補現在時間；本輪統一缺值語意與呈現 |

## 共用格式化風險

`src/guided_notes/notes/routes.py` 的 taipei_time 目前直接執行 `datetime.fromisoformat(value).astimezone(UTC+08:00)`，輸出只到分鐘。輸入無 offset 時，其解讀依執行環境本地時區；輸入已含 offset 時則有明確時刻。函式沒有本身處理 null、空值、損壞值或來源未知的分支。模板有部分空值判斷，不能當所有來源都已防護。此為已核對的程式風險，未等同重現使用者的原畫面。

本輪不採「所有字串加八小時」。已知 UTC 無 offset 的來源須列明，其他不明來源顯示不可確認。標準輸出及傳輸相容策略留到 plan；spec 不預定技術棧改造。

## 範圍排除

OAuth／學生資格到期、寫入 lease、網路逾時、presence TTL 等使用 epoch 或計時預算，是安全／恢復／在線判斷，並非本輪畫面時間。不得因顯示修正改其數值。來源 Grid 格位、Sheet 格式及時間文字也不因本輪而改寫。

## 尚待驗證及跨 Issue 接線

1. 找出原偏差頁面，或在受控樣本確認受影響頁面；無法重現時如實保留。
2. plan 明定無 offset 原值的欄位來源清單、格式化失敗提示與傳遞相容性；不用清 DB 或換授權解決。
3. 以 UTC／台北／另一時區執行受控回歸，再人工核對原事件區間；不得改操作電腦時鐘以測試。
4. 與 #19 對齊事件標籤、共用呈現格式；#16／#17 只需避免將格式化字串拿來當加入資格、識別或排行依據。

## 2026-11-27 Phase 1 補充（仍為靜態盤點）

- 使用者在plan指令明確指定固定Asia/Taipei、24小時及至秒；不再只當未回覆的候選政策，但OpenSpec同步仍未回報。
- `activities/teacher.py` 的store_activity以PREPARING／phase_version=0建立，transition每次成功轉移加1。classroom start／finish與對應timestamp寫入在同一交易；原history SELECT未含phase_version，plan擬內部補讀作直接結束證據，不改counter或表。
- CLOSED／缺started_at本身不能證明「從未開始」。只有可信原流程且version1才採直接結束；缺證據或version≥2視為缺開始紀錄。這是對spec已要求區分狀態的技術落實，不新增生命週期。
- notes時間writer仍為帶offset的repo.now()；計畫不把任意naive notes字串擴張成可信SQL UTC。未查操作者歷史DB的值分布，不宣稱完成舊資料全面檢查。

## 2026-11-27 分析後決策更新

使用者回報 OpenSpec 已確認時間呈現規則，並指定畫面改為台北 YYYY-MM-DD HH:mm、24小時制、到分鐘截取不進位。原始秒／微秒、來源解析格式及結果排序保持。上方至秒／同步未回報為先前階段紀錄。確認者姓名與獨立紀錄未提供。

## 2026-11-27 實作核對

基底更新至 80510a6bbf6310bf4634052a7a56066f8f1e8baf；PR #22 numeric-group-labels已有notes group_labels，接線完整保留。已實作history讀取a.phase_version並在原驗權後投影；原created_at／started_at／closed_at與ORDER BY未改。notes不再直接對naive呼叫astimezone，而由offset_required規則安全顯示。純核心不讀現在時間／DB／Google，無schema或writer差異。Windows有tzset平台限制；wsl --list --quiet回報未安裝可用WSL，未為本輪安裝Linux。真Chrome三context已執行，不能抵作POSIX server矩陣。原使用者小時差仍未定位到特定頁面／舊值，不宣稱自然根因已重現。

## 2026-11-27 真人回查與跨環境補證據

使用者回報找到原偏差頁且目前時間已正常；未提供原頁名稱／原先數值／精確時差，不能宣稱Codex獨立重現八小時偏差。精確新操作時計與頁面21:19已依validation.md補齊。真Linux server三時區矩陣run46005787175已1passed、0skip；先前缺WSL／未重現為當時歷史，保留以利區分證據來源。
