# 011 Phase 0：時間解讀與相容性研究

日期：2026-11-27；基底 `e9a29c7`。Codex 讀取原始碼並依 plan skill 派出唯讀研究代理核對官方文件；沒有執行產品測試、讀寫操作者 DB、真 Google、修改系統時鐘／時區。原偏差畫面仍未重現。

## R1 — 解讀時先取得可信時區

**Decision**：建立單一純函式，先依來源政策將原值解讀為 aware datetime，再轉固定 UTC+08:00，最後顯示到分鐘。禁止對 naive datetime 直接 astimezone，也不直接對字串加八小時。

**Rationale**：Python 的 naive astimezone 假定主機本地時區；aware astimezone 則維持同一瞬間。使用者回報的小時差與此風險相容，但不是原案例的根因證明。[Python 3.13 astimezone](https://docs.python.org/3.13/library/datetime.html#datetime.datetime.astimezone)

**Alternatives considered**：前端自行 Date 轉本地時區會受瀏覽器設定影響；SQL localtime 受主機環境影響；所有時間加八小時會把原 +08:00 再加一次。均不採。

## R2 — 固定政策使用標準庫，不新增時區資料依賴

**Decision**：使用 Python 3.13 `datetime.timezone(timedelta(hours=8), name='Asia/Taipei')` 表達本輪「固定台北 UTC+08:00」政策，使用者可見格式 `YYYY-MM-DD HH:mm`。保留原微秒，僅輸出時截取，不四捨五入。

**Rationale**：使用者已在 plan 指令指定固定政策；本輪不提供歷史台北日光節約規則或個人時區設定。標準庫可在 Windows 直接使用，不增加環境設定。[timezone](https://docs.python.org/3.13/library/datetime.html#timezone-objects)

**Alternatives considered**：ZoneInfo 適合 IANA 歷史規則；Windows 通常需要額外 tzdata，缺資料會報錯，而且歷史台北偏移未必永遠 +08:00。若未來改需求再採用，不在本輪引入。[ZoneInfo 資料來源](https://docs.python.org/3.13/library/zoneinfo.html#data-sources)

## R3 — 舊值只讀相容，不做資料遷移

**Decision**：明列來源政策：已盤點 SQLite CURRENT_TIMESTAMP 欄位的嚴格 `YYYY-MM-DD HH:MM:SS` 可補 UTC 語意；notes 的 repo.now() 來源要求明確 offset；未核對來源的 naive 值顯示「時區未確認」。原欄位、writer、schema、索引及清單順序不改。

**Rationale**：SQLite 官方定義 CURRENT_TIMESTAMP 是 UTC 的秒級字串。既有欄位的來源可證明；不能因此把所有無 offset 文字都當 UTC。既有 notes writer 已用 aware UTC，沒有必要批次改寫。[SQLite DEFAULT](https://www.sqlite.org/lang_createtable.html#the_default_clause)、[日期函式](https://www.sqlite.org/lang_datefunc.html)

**Alternatives considered**：批次改為帶 offset 需遷移、回退與資料判斷，會增加改錯舊值的風險；單改 datetime adapter 的全域行為可能影響其他 DB 讀寫。本輪不用。

## R4 — 解析成功不等於合法事件時間

**Decision**：解析前限制接受的完整日期時間格式；拒絕 date-only、週日期、純數字 epoch、布林值、含不支援的時區縮寫、無效日期、閏秒及過長文字。捕捉格式及轉換溢位，輸出安全狀態；未知 naive 的格式合法也不得猜測。具體規則見 [時間契約](contracts/time-display.md)。

**Rationale**：fromisoformat 也接受日期-only 等形式，直接使用可能補出假的午夜事件。支援實際 writer 的格式即可，避免寬鬆轉換無法追溯。[fromisoformat](https://docs.python.org/3.13/library/datetime.html#datetime.datetime.fromisoformat)

**Alternatives considered**：新增第三方寬鬆 parser 或使用 strptime 的主機預設時區均無必要。原精度與值不因顯示正規化而改寫。

## R5 — 新增教師顯示 metadata，不更改結果契約

**Decision**：教師活動清單原 raw time 欄位保留，外加 version=1 的 `time_display`；notes HTML 使用同一 presenter 的 view model，舊 `notes_time` filter 保留為安全相容橋接。001 CatalogDTO、003 snapshot/results 與學生回應不增時間欄位。#19 的回填脈絡以外層 metadata 取用 presenter，不重寫格式器。

**Rationale**：既有教師清單是私有導覽資料，增顯示欄位可保留舊使用端。把時間混入嚴格清單或不可變結果會改變快照及驗證，超出本輪。

**Alternatives considered**：直接取代 raw created_at 為格式化文字會破壞原欄位語意；前後端各寫一套 formatter 會重複政策。均不採。

## R6 — 未開始即結束需生命週期證據

**Decision**：只讀既有 phase_version 作為內部判讀輸入，不改 counter。已知本活動由 PREPARING/version0 建立且僅一次合法轉移為 CLOSED/version1、開始值缺失時，可呈現「未開始即結束」。CLOSED、缺開始值但 counter／來源無法證明時顯示「時間未記錄」。有不合法開始文字仍顯示無法辨識，不因版本1而掩蓋。

**Rationale**：store_activity 初始化為 PREPARING，transition 每次成功轉移加1，start／finish 與時間寫入共用交易；僅憑 started_at=null 不能區分直接結束與壞歷史。詳見來源盤點的 Phase 1 補充。

**Alternatives considered**：新增 direct_close 欄位需遷移，本輪不必；一律把 null 當從未開始會捏造事件。若實作時發現舊來源不能滿足證據，維持缺紀錄提示，不擴充推論。

## R7 — 跨執行時區測試分清平台證據

**Decision**：Windows 本機以來源／偏移／狀態矩陣及禁止主機時區依賴的回歸為主；真正執行時區矩陣在 POSIX 隔離子程序設定 TZ 並呼叫 tzset，或使用已有多時區執行環境。瀏覽器用獨立受控 context 模擬 timezone。所有測試不改操作者系統設定。

**Rationale**：time.tzset 是 Unix-only；Windows 只設 TZ 不能證明主機解讀已改變。mock 與真實子程序／瀏覽器證據須分開。[time.tzset](https://docs.python.org/3.13/library/time.html#time.tzset)

**Alternatives considered**：手動改 Windows 系統時區／時鐘會干擾登入及其他開發，不採；只有 mock 就宣稱 SC-002 完成亦不採。缺可用 POSIX／瀏覽器環境時保留對應未執行，不把環境待辦當設計歧義。

## 研究結論與剩餘證據

技術選擇已決定，無未解的設計 NEEDS CLARIFICATION。尚待產品實作、受控回歸、跨環境執行、原偏差頁定位及教師＋兩組學生人工驗收。官方資料及靜態風險不代替上述結果。
