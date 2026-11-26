# 009 規格與圖意核對

日期：2026-11-26。狀態：使用者回報同學已審圖；修訂版與介面待重新核對；Q1～Q3 使用者決策已記錄，不進入 plan／tasks／實作。

**最新狀態**：plan／tasks／分析均已產出；使用者回報「C1 C2皆已確認」，D22雙組行為與新版圖意依此記為已確認，姓名／獨立連結未提供。下方前階段待確認文字保留歷史，最新以本註記及末節為準。003具體介面／分工依T003核對，尚未實作。

## 來源與工作範圍

- 已讀 `.specify/memory/constitution.md`、`README.md`、`docs/shared-requirements.md`、002／004 課堂及學生恢復契約、007 教師登出保留學生資格契約，以及 008 validation 的「使用者確認：一次性課堂碼釋放與重用（2026-11-26）」。唯讀比對現有 classroom_membership／classroom_access／classroom_routes，沒有修改產品程式。
- 起始分支 `codex/008-teacher-course-workspace`，HEAD `2d4f421`；保留一個原有未追蹤檔，未開啟或覆寫。既有功能目錄最高 008，003 是同學工作，沒有補建或覆寫。
- `.specify/init-options.json` 使用 `feature_numbering: sequential`，因此建立 `specs/009-release-classroom-codes`。本機 `feature.json` 更新指向 009，受原忽略規則排除。
- 本機沒有 `.specify/extensions.yml`，before／after specify 均無 hook。透過既有 `resolve-template.ps1 spec-template -Json` 解析有效範本，保留範本章節順序。
- 建立並切換 `codex/009-release-classroom-codes`，基底為上述 HEAD；Git 寫入曾因沙箱拒絕，經工具核准後成功。未 commit、push、合併或改 PR。PR #7 維持使用者提供的 Draft 待複審狀態，沒有宣稱已查證遠端即時狀態。
- 使用者確認本輪需求，不等於另一位組員或 OpenSpec 已確認。沒有更改 008 任何人工／互審項目，也沒有清 DB、使用 Google 憑證或更換 key。

## 三圖核對重點

| 圖 | PNG | 請核對的圖意 | 規格對應 |
| --- | --- | --- | --- |
| [Component](../../diagrams/009-component.puml) | [預覽](../../diagrams/009-component.png) | 新加入只查有效碼；恢復只用原證明；003／001 使用原活動身份；責任框不代表新增服務決案。 | FR-002～012 |
| [Class](../../diagrams/009-class.puml) | [預覽](../../diagrams/009-class.png) | 碼對應可釋放，課堂 ID、原組別、活動與結果不轉移；歷史配碼是概念而非資料表定案。 | FR-001～011 |
| [Sequence](../../diagrams/009-sequence.puml) | [預覽](../../diagrams/009-sequence.png) | 關課與釋放對外一致；重送不碰新堂；舊恢復／新加入分流；已解析舊堂的請求不得轉投新堂。 | US1～4、R1～R8 |

三圖屬 specify 概念藍圖，交易機制、欄位結構與介面實作尚未定案。活動結束與課堂結束不同；碼只在課堂結束釋放。此處未引入新的順位、去重或結算規則。

## 需與 003／課堂同學對齊的契約（尚未送出或取得確認）

| 契約 | 本輪要求／需核對事項 | 既有依據 |
| --- | --- | --- |
| 正式受理 | 固定原 activity_id；在相同確認範圍重新驗課堂仍開放、當前活動搶答中、組別屬本堂、題目固定版本。不能依碼重找新堂；確認關課前後依既有 D02。 | 004 contracts「003 受理」、002「驗證受理」；FR-009、012／R8 |
| 關課與結算 | 一併結束 PREPARING／LIVE 活動；重複關課不重結算。CLOSED 與已結算分離，不為釋放碼等待假結果或丟棄待結算資料。 | D14、002 get_ended_snapshot；FR-004、006、011 |
| 加入／恢復 | 輸入碼＋組別取得固定 classroom_id／group_id；proof／grant 固定原紀錄，僅課堂仍開放可恢復內容；整堂結束即停止學生內容權限。需核對碼索引／有效對應變更與失效判定；無對應文案指定為「查無此課堂」，機器代碼／狀態尚待後續契約決定。 | 004「學生加入與同步／歷史結果（本輪已修訂）」、D09／D16；FR-003、007、008 |
| 結果視角 | 直接查指定活動驗原堂原組及課堂仍開放；整堂結束後後端拒絕學生結果。活動結束但課堂仍開放時 D06 不變。 | 002「驗證結果視角／D06」、004 歷史；FR-009～011 |
| 001 回填依賴 | activity_id、import_id／version、result_version 及固定勝組不隨碼改配；RESULT_NOT_READY 不變，未知寫入仍先回讀，不因碼重用再送。 | 002→001 快照／D11、008 歷史保留；FR-010、011 |
| 並發與重送 | R1～R8 須核對兩方邊界與錯誤回應；結束 A 僅釋放屬 A 的有效占用，不按碼值刪 B 對應；舊請求／回應不得重綁範圍。 | FR-006、012、013 |

## 使用者決策紀錄

### Q1：碼格式（已確認，FR-014）

2026-11-26 使用者回報「碼格式和回收方式已確認」，依前述建議採現有格式。唯讀核對 `src/guided_notes/activities/classroom_routes.py` 的 `make_room_code()`／加入路由，以及 `src/guided_notes/http.py` 的 `string()`：產生兩個 A–Z 大寫字母加三個 0–9 數字，共 5 碼；輸入去首尾空白、轉大寫，保留中間空白，原始輸入最多 32 字元且須為非空白文字。沒有把既有 32 字元輸入門檻誤寫成產碼長度。

驗收例：有效 AB123 可由 ab123 或首尾含空白的相同碼加入；AB 123 不視為 AB123，無對應則「查無此課堂」。空白、非文字及超長沿用輸入錯誤。

### Q2：釋放後再分配（已確認，FR-015）

依前述建議：成功關課時釋放有效占用，立即進全域可分配範圍，無冷卻期；系統自動選碼，不提供教師人工指定，不保證下一堂同碼。可跨教師及課程重用；仍有效碼不可回收。重複結束 A 不得釋放 B 的同碼對應，競態 R1～R8 仍須符合規格。

### Q3：學生登入與結束頁（已由使用者回答）

2026-11-26 使用者確認：

- 只比照老師獨立登入頁與操作流程，學生仍輸入課堂碼＋組別，不新增 Google 學生登入。
- 加入成功後進課堂內容，不在上方持續顯示登入提示／加入表單。
- 整堂結束後學生不能看題目或歷史結果；顯示「課堂已結束」及「加入其他課堂」，按下才回獨立加入頁。
- 教師歷史與回填依賴保留。活動已結束但課堂仍開放時，學生結果仍依 D06；與原「關課後可恢復學生歷史」不同，須與 003 及 OpenSpec 同步。
- 教師歷史碼的具體標示尚未決定；留待後續設計。Q1／Q2 已依後續使用者回報記錄。

本次修訂在前次「同學已審圖」之後，舊審圖紀錄保留，不能視為新版已審。

## 渲染及驗證

依憲章使用既有 CLI 渲染根目錄全部 24 份 `.puml`，實際指令：

```powershell
& 'C:/Program Files/Java/jdk-24/bin/java.exe' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar 'D:/os_final/diagrams/*.puml'
```

- 退出碼 0，009 三份 PNG 皆產生於 `diagrams/`，既有已追蹤圖檔沒有 Git 差異。
- 以 Python 標準庫讀 PNG IHDR：Component 2080×564、Class 1193×804、Sequence 1276×2308。
- Codex 已逐張開啟 PNG 核對：中文、關係、分支及註記可讀，無裁切或 PlantUML 錯誤頁。Component 橫向較寬，適合開原圖縮放查看。
- AI 文件核對已覆蓋唯一性、回收安全範圍、R1～R8、重送、恢復隔離、手動加入、權限與固定歷史。品質檢核仍保留三項未通過：未清除釐清標記、全部要求無歧義、全部要求具完整驗收條件。
- 最終 `git diff --check` 通過；另外以 Python 標準庫檢查 009 新建六份文字檔的行尾空白與 Markdown 本機連結目標，無問題，初稿釐清標記為 3 個；本次 Q3 已答，剩 Q1／Q2 共 2 個。檔案範圍僅新增 009 文件／圖與共同需求 D22；本機忽略的 feature 指向已切 009，原未追蹤檔保留。
- 沒有執行產品測試；渲染與 AI 文件核對不代表功能已實作或組員驗收。

## 人工核對狀態

- [x] 同學已審閱本輪三圖（2026-11-26 使用者回報「同學已審圖」）。審查者姓名、具體結論／修正意見及獨立紀錄連結未提供；不推定為全部圖意通過或介面契約已確認。
- [x] 使用者回報C1／C2皆已確認，記錄本輪規格行為及新版三圖確認（2026-11-26記錄日；姓名／獨立證據未提供）。
- [x] Q3 學生登入方式與結束頁行為已回答並同步規格／圖表。
- [x] Q1～Q2 使用者回報確認，依前述方案補實際格式／再分配規則並同步圖表。
- [x] 使用者回報C2已確認：關課後停止學生存取與獨立加入頁的新版圖意已核對，來源為使用者回報。
- [ ] 另一位組員具名核對課堂／003 介面。
- [x] 使用者回報C1已確認：本輪D16→D22行為已雙組同步；2026-11-26為記錄日，實際確認日期／確認者姓名與獨立連結未提供。

本輪終點是規格／圖意核對；即使核對完成，也不自動進入 plan。

### 本次需求修訂的驗證

修訂三份 puml 後重新執行上述全目錄 CLI，退出碼 0；新版 Component 2161×600、Class 1208×823、Sequence 1263×2408。Codex 逐張檢視新版 PNG，中文、關課拒絕分支與獨立加入流程可讀，無裁切或錯誤頁。前述尺寸為初稿紀錄，以本段新版尺寸為準。`git diff --check` 通過，既有已追蹤圖無差異。沒有執行產品測試。前次同學審圖不代表本次修訂已審，003 及跨組同步仍待完成。

### Q1／Q2 確認後更新

規格無剩餘 NEEDS CLARIFICATION 標記；品質清單重新核對，僅指文件品質，不代表產品實作或人工驗收。更新三圖中的碼格式及立即全域分配註記，以上述全目錄 CLI 重新渲染，退出碼 0；最新 Component 2161×600、Class 1208×823、Sequence 1263×2426。Codex 逐張檢視，格式／回收註記清楚，無裁切或錯誤頁。本機連結與行尾空白檢查、零釐清標記檢查及 `git diff --check` 通過，既有已追蹤圖無差異。本輪仍不進入 plan，003 介面與 OpenSpec 確認維持待辦。

## Plan 設計核對與渲染（2026-11-26）

依使用者「可以進入plan」及本機 speckit-plan 呼叫產出 [plan](plan.md)、[research](research.md)、[data-model](data-model.md)、三份 contracts 及 [quickstart](quickstart.md)。setup-plan -Json 回傳正確009目錄，解析BRANCH省略codex/，另以Git核對實際分支。before／after hooks檢查皆無extensions.yml。

本次技術註記：Code為OPEN投影＋部分唯一索引，保留歷史code及非破壞表重建；各寫入操作BEGIN IMMEDIATE；重複關課200且不改版本／時間；學生獨立頁及固定URL；原grant查closed state只回200最小提示，原proof恢復closed回409，不授內容權限。以上落點對應plan追溯表及三份契約。

CLI沿用本檔前述全目錄命令。首次Sequence新增訊息的換行未跳脫而語法失敗（line64，exit1），已修正成PlantUML訊息內換行。最終全24份puml重渲染exit0；最新Component2215×635、Class1246×904、Sequence1454×2443，Codex逐張檢視中文字、約束與分支可讀，無裁切或錯誤頁，既有已追蹤圖無差異。

文件檢查：009十份Markdown及三份puml共13份文字的本機連結／行尾空白通過；四份主要新文件無範本佔位、無未解技術釐清標記；git diff --check通過。沒有跑產品測試、啟動服務、存取真DB或憑證。研究代理只讀，沒有改檔。原未追蹤檔保留，未commit／push。

人工狀態仍為：修訂版三圖、具名課堂／003介面、OpenSpec D16／D22同步待補；不以Plan授權或AI檢視代勾。008原人工與互審待辦維持。

## A1／I1文件補正與渲染（2026-11-26）

使用者授權套用A1／I1。spec／plan／student-entry及quiz-history契約／quickstart／T035、T048、T052已統一後端新讀取拒絕、前端CLOSED後拒絕合法舊快照晚回，以及人工手動加入與受控同碼隔離分列的驗收方式。Sequence補充對應授權時點註記，互動分支與Component／Class責任未改。

實際CLI：`& 'C:/Program Files/Java/jdk-24/bin/java.exe' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar 'D:/os_final/diagrams/*.puml'`，全24圖重渲染退出碼0；新版Sequence1454×2477，Codex已開圖核對新增註記可讀、無裁切或錯誤頁。文件連結／行尾空白、57任務連號／14個[P]及git diff --check通過；沒有跑產品測試。

歷次分析與本輪定向修訂核對見[analysis.md](analysis.md)第2輪，未冒稱完整analyze重跑；新版人工審圖與跨組同步仍未代勾，D1本輪未修改。

## C1／C2確認與D1文字整理（2026-11-26記錄）

使用者明確回報「C1 C2皆已確認 D1照你的建議改」，據此記錄雙組行為及新版圖意已確認；確認者姓名／獨立連結及實際確認時間未提供。原歷史待確認紀錄保留，不再以相同缺口阻擋後續工作，也不把此回報擴張為T003具體函式／分工、產品測試或008舊待辦已完成。

D1只整理FR-016／018責任，沒有結構／互動變更，無須變更或重渲染圖表；沿用A1／I1最近一次exit0圖檔。新的完整分析報告保存於analysis.md第3輪。

## 009 本機實作對圖（2026-11-26）

執行／核對者Codex，版本為分支codex/009-release-classroom-codes、HEAD2d4f421加本輪工作樹；非同學新一輪互審。C1／C2先前使用者確認仍有效。本輪補bootstrap專用連線／FK界線、schema版本9及PR9已核對但未正式整合狀態，沒有變更已確認使用者行為。

| 圖表責任／關係 | 實作對應及結果 |
| --- | --- |
| Component Code／Close／Join | classroom_routes.py的insert_room／close、classroom_membership.py的join／identity_for／group_for；OPEN索引、先owner再冪等及固定原堂相符。 |
| Class Room／Group／Membership／Grant | classroom_schema.sql保留複合FK、歷史code，新增部分唯一及不可逆／歸屬trigger；不建碼池或移轉歷史資格。 |
| Class升級註記 | classroom_migration.py＋db.py私有bootstrap；未知表定義拒絕、已知依賴恢復、指紋／FK檢查、marker同commit；request連線不使用FK OFF。 |
| Sequence關課／分配／恢復 | close與join各於寫交易；CLOSED state最小200、recover409、結果409；兩個學生頁與CLOSED terminal／generation晚回防護相符。 |
| 003及001歷史 | 原gateway受控接口保留，正式PR9未合流；教師回填與原結果依賴不因學生禁讀而移除。圖中明示待正式整合，不宣稱完整交付。 |

實際命令：`& 'C:/Program Files/Java/jdk-24/bin/java.exe' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar 'D:/os_final/diagrams/*.puml'`，全24份puml成功重渲染，Java退出碼0。Codex逐張開啟009 PNG核對：Component2220×652、Class1300×922、Sequence1454×2477，中文字／箭頭／分支可讀，無錯誤頁或裁切。既有其他功能圖無新增語意修改。

T054的AI對圖與CLI已完成；組員最新技術圖複核及實際學生頁面排版由T052／T059保留，不能以本節代勾。
