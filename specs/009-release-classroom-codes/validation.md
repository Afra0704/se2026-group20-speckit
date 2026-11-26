# 009 實作與驗證紀錄

## 執行基線（2026-11-26，Asia/Taipei）

- 執行者：Codex；使用者呼叫本機speckit-implement，開始依tasks執行，並非新增commit／push或真DB操作授權。
- 實際分支：`codex/009-release-classroom-codes`；HEAD `2d4f421`。feature.json指向 `specs/009-release-classroom-codes`；prerequisites成功取得research／data-model／contracts／quickstart／tasks。
- 起始dirty：docs/shared-requirements.md；specs/008-teacher-course-workspace/validation.md（其他工作追加紀錄，保留）；009整個文件目錄及三份puml／PNG未追蹤；另有原本名稱含特殊字元的未追蹤檔，未讀取或修改。008任務及原人工／互審狀態不代勾。
- before_implement檢查無extensions.yml；無hook。checklists/requirements.md為16項、16已勾、0未勾，PASS；只讀檢查，沒有更改清單。
- 環境：既有Python3.13.1、Node v22.12.0；沿用pyproject／uv.lock與已安裝依賴，不升級套件。Git repo檢查成功；未發現Docker、ESLint、Prettier、Terraform、Helm或npm發佈配置，無須新增對應ignore。
- .gitignore已有Python cache／venv、node_modules／build、.env／私有JSON／key、instance／SQLite／log及工具tmp等關鍵規則，不需變更。未讀取環境變數內容、真DB、key／憑證或Google授權。
- 上輪analysis.md第3輪文件分析0未解問題；C1雙組行為與C2新版圖意已由使用者回報確認，不重新詢問同一需求。

## T001結果

執行基線及證據分類已建立，T001完成。其他產品測試、schema升級、頁面與正式003整合尚未執行；不將文件基線當作功能驗證。

## T003具體技術交接（核對中）

現有程式已唯讀核對，沒有修改：

| 邊界 | 本機現有契約／差異 | 後續009範圍 |
| --- | --- | --- |
| 受理 | quiz/submission_gateway.py在write_transaction內呼叫submission_context及ACCEPT_SUBMISSION(db,context,answers)，同一db；submission_context已核原堂／當前活動／LIVE。 | 保留共用交易及原activity_id，不改順位／結算演算法；OPEN guard的錯誤映射需一致。 |
| 學生結果 | quiz/results_gateway.py經classroom_membership.group_for；後者目前未檢OPEN，results_for也未包一致read transaction。 | group_for加入OPEN內容限制，state最小結束提示獨立驗身份；結果同read transaction驗權及DTO。涉及quiz共用接線需依分工確認。 |
| 結算與教師歷史 | GET_SETTLED_RESULTS／get_ended_snapshot保留teacher ownership及CLOSED／ready分離；沒有正式003provider完成證據。 | 不假造勝組、不把關課當已結算、不新增worker；正式provider驗收T051維持待做。 |
| 學生恢復 | classroom_membership.recover目前僅接受CLOSED且發read_only grant。 | 改成OPEN才可恢復，CLOSED409不更動session；原membership／proof歸屬保持。 |
| schema | classrooms.code目前表內永久UNIQUE；db.py已將core＋Google身份初始化放同交易。 | 保留既有原子性，受控非破壞重建，不清DB、不重設UUID／密文。 |

已提出T003具體交接狀態問題，等待使用者回答；這不是重問C1／C2。T003及T004尚未完成，在前置依賴解除前不修改共用程式或執行Phase2。

## 證據分類及產品狀態

| 類型 | 當前結果 |
| --- | --- |
| 文件／環境只讀核對 | 已完成上列基線及介面差異整理。 |
| 受控自動測試V01～V09 | 尚未執行。 |
| 正式003受理／排名／結算整合 | 尚未執行，不以現有gateway視為完成。 |
| 教師＋兩組學生人工驗收 | 尚未執行。 |
| 真Google／真實Sheets回填／未知恢復 | 尚未執行，本輪不自行操作。 |

禁止真DB遷移／清空、換Google key／授權、commit／push／合併PR；本紀錄不改變既有使用者限制。

## T003／T004前置完成

使用者回答可先檢查已上傳003 PR後再開始。已按其指示核對PR9 head31b0e23，隔離14測試通過（5.89秒、exit0），詳細接口／分工／已知差異見[pr9-review.md](pr9-review.md)。不自行合併PR或導入其演算法。新版結果讀取須避免try_pending巢狀寫交易，D22編號碰撞於整合記錄處理；009接續範圍已明確。T003按此具體檢查方式完成，T004先前0未解分析加上本輪接口重核成立，解除Phase2前置，不代表正式整合或人工驗收完成。

## 本機實作及受控證據（2026-11-26）

執行者Codex；分支及HEAD同基線，包含尚未提交的009程式／測試／文件。前文「尚未執行」均為對應時間點的歷史記錄，最新以下表為準。沒有使用操作者DB、真憑證或真Google網路寫入；測試DB由pytest tmp_path／既有fixture建立，CLI init-db只在測試app執行。

| 任務／驗收 | 實際證據與限制 |
| --- | --- |
| T005～T012／V01 | classroom-008.sql保留原表定義；schema與failures測試驗全列指紋、複合current_activity FK、依賴view／trigger、永久關閉／不可改碼、部分索引、重啟／init-db、雙初始化。未知欄位／額外CHECK／錯誤索引拒絕；copied／replaced／restored／verified故障完整還原。真實Google表結構的合成UUID／密文在升級及Google bootstrap失敗rollback後保持。FK恢復注入失敗停止啟動且關閉私有連線，乾淨重啟驗已commit版本；不虛稱commit後也rollback。 |
| T013～T021／V02、V03、V08 | management／memberships／code_lifecycle驗碼格式、strip＋upper、內部空白、原始32／80限制、空值／非文字、owner／confirm、12碰撞503、永久close與重送版本／時間不變；兩堂同碼不同ID、原學生只有原堂資格，明確新加入才取得新組ID。 |
| T022～T032／V05～V07 | recovery_009及results／close驗OPEN恢復204、CLOSED恢復409無Set-Cookie／新grant、有效proof也禁讀、跨堂／過期／偽造組別拒絕、CSRF／限流、cookie scope。closed state只有classroom_id／classroom_state／state_version。教師歷史及OPEN堂的活動結果保持。 |
| T024／V01、V07、V08 | history_009用實際001儲存結構＋WritableSheets替代來源建立兩組、固定講義、結果快照及unknown回填報告，再重建舊schema→升級→關課→跨教師同碼新堂，全部舊資料指紋保持，教師原報告相同且writes仍1次。另一例pending回填預覽RESULT_NOT_READY、零自動來源寫入。此為受控provider，並非正式003／真Sheets。 |
| T033～T039／V04 | code_races雙建立201＋503最多一OPEN；A重送與B建立使用Barrier，B仍唯一owner。join_races用Event持寫鎖，加入先固定A、關課先則後續加入403；transition故障關課rollback。submission_races驗callback使用同交易，accept先保留原activity／group，close先零callback；合法read snapshot先取得時可完成，close後新read409。 |
| T040～T049／V06、V09 | 頁面契約驗獨立/student與固定ID空shell、no-store、零SSR題目及Google學生登入。Node驗成功使用server ID、pending防連點、錯誤／限流／CSRF／斷線可重試且不背景重加、CLOSED terminal、generation／version／room晚回拒絕、結果選取跨正常poll保留、確認CLOSED後晚回結果零顯示、另一分頁改組清草稿不轉權。DOM不是真人排版／鍵盤／實測5秒證據。 |

### R1～R8的確認順序

| 案例 | 控制方法／結果 |
| --- | --- |
| R1 | 兩writer用Barrier同時建堂，固定同一測試候選，201／503；無雙有效碼及失敗空殼。 |
| R2 | join在寫鎖內固定A後Event暫停，close必須等它commit；學生201歸A，後讀最小CLOSED。 |
| R3 | A close commit後、B尚未建立時，新client JOIN_DENIED；循序窗口檢查，不冒稱並發。 |
| R4 | B同碼commit後明確新加入201歸B、新group_id；A既有資格403 B，原A仍CLOSED。 |
| R5 | 生產join於BEGIN IMMEDIATE後解析；R2／關課先兩個多連線測試證明無writer能在解析後插入關課／重配，無同請求轉投。沒有虛構拆開的預解析API。 |
| R6 | transition已更新後注入例外；整堂／活動及碼占用rollback，新加入仍A。 |
| R7 | A已CLOSED，重送close與B固定候選建立經Barrier同時進入，各200／201，唯一OPEN對應B。 |
| R8 | Event控制ACCEPT_SUBMISSION在原交易受理後才讓close完成；原答案列保留。反序close先則409零callback。另read DTO持有授權snapshot時close等待，新read拒絕；前端晚回另由Node驗。全部為受控callback，正式003尚未驗。 |

### 測試指令、失敗與重驗

- 分階段命令使用`.venv/Scripts/python.exe -m pytest <對應上述測試檔> -q --tb=short`；Node為`node --test tests/student-entry-009.test.cjs tests/student-room-009.test.cjs`。環境Python3.13.1／Node22.12.0，無新增依賴。
- schema初次6失敗／1通過；實作後schema／Google／007相容16通過。新部分索引接線初次暴露舊ON CONFLICT target，修正為code＋OPEN條件後，生命週期與管理／加入12通過。頁面契約及加入JS初次缺頁／缺script失敗，新增後通過。並發案例多為後補安全回歸，不偽造全程TDD。
- Node曾重現「已選結果在每次poll被清空」，修正history signature／selectedResult；又重現另一分頁改組，新增scopeBlocked及清內容後通過。
- 首次全pytest 1失敗／431通過／98 subtests：舊notes整合仍期望關課後學生結果可讀。依009契約更新為409，保留教師export-preview201檢查；後續全測439通過／98 subtests（89.87秒）。
- 補FK恢復故障與accept-first後，測試錯把既有提交201寫成200，已更正測試契約，針對兩檔10通過；並非伺服器回應變更。新增未知CHECK拒絕後schema兩檔13通過。
- 完整回歸第二次：`.venv/Scripts/python.exe -m pytest tests -q --tb=short --maxfail=3`，442 passed、98 subtests passed、73.27秒、exit0。
- T060新增邊界後，management／memberships／recovery／code_races／join_races五檔22 passed、8.74秒；history_009兩案例2 passed、1.02秒；全部Node以Get-ChildItem tests -Filter '*.test.cjs'收集後`node --test $nodeTests`，38 passed、0 failed、239ms、exit0。最終全pytest結果追加於下節。

### 收斂／圖文／剩餘工作

speckit-converge依19 FR含017a、6 SC、四故事與R1～R8、plan七項架構決策及憲章I～VI核對，產生3項partial：HIGH正式PR9合流邊界；MEDIUM人工操作／技術複核；MEDIUM自動邊界補強。僅於tasks末尾附Phase8 T058～T060，不重編原任務。T060已補測通過，前兩項依原限制保持未完成；T055整體不能冒稱clean convergence。

三圖已按實作核對責任、FK／部分索引／版本、端點及交易／終態分支，沿用Java CLI全24張PNG exit0、Codex逐張檢視009正常；尺寸／命令／對應位置見[diagram-review.md](diagram-review.md)。這是AI技術核對，C1／C2既有確認不變，沒有新增同學互審證據。

正式003仍未導入本分支；本版不能示範真實排名／結算。PR9隔離14測試與009受控callback測試分開，T051／T058未勾。T052／T059教師加兩組、390×844／桌面、鍵盤及實測關課同步未做；真Google／真Sheets寫回未做。008原人工與互審待辦保持。

## 最終回歸與範圍檢查

最終`.venv/Scripts/python.exe -m pytest tests -q --tb=short --maxfail=3`：**452 passed、98 subtests passed，80.23秒，exit0**。完整Node：**38 passed、0 failed，exit0**。新增邊界及unknown報告測試納入此版完整pytest，不以先前442數字代稱最終版。

T056完整跨產物分析已追加至analysis.md第5輪，規格25需求均有任務，未發現新文件問題；尚未完成的交付門檻分列而非抹除。tasks共60項、55完成／5未完成；T055因正式／人工門檻未達仍未勾，即使收斂檢查本身已執行。

T057檢查：git diff --check通過，僅008既有外部檔案有LF／CRLF提示；009 Markdown本機連結通過，任務ID001～060連續、無重號，3張PNG尺寸及讀圖結果一致。對本輪52個來源／測試／文件文字檔作高可信私鑰、Google key／secret及GitHub token樣式檢查，0命中；合成測試值保持明顯test／synthetic，沒有輸出真憑證。此掃描是範圍檢查，不宣稱一般安全稽核。

改動限009規格／圖／文件與必要classroom／db／學生頁接線、結果gateway讀交易及測試；003順位／結算／正式submission演算法沒有導入或覆寫。README及共同需求保存最新本機階段，008validation外部修改與原特殊名稱未追蹤檔保持，008任務未代勾。Git分支仍codex/009-release-classroom-codes、HEAD2d4f421。前後無extensions.yml，before／after implement／converge／analyze無hook可執行。本輪沒有commit／push／合併PR、啟動操作者服務、真DB遷移／清空或key／Google授權更換。

## 003＋009正式整合延續（2026-11-26，Asia/Taipei）

本節取代前節「未導入正式003／不commit」的階段狀態，其餘歷史證據保留。使用者指示延續T051／T058整合003最新master，允許清楚的本機分段commit，人工與真Sheets由使用者之後執行，不以未執行阻擋本次整合。仍不push／合併009 PR、不操作操作者DB／憑證／Google授權；舊獨立活動模式移除另開SpecKit，不混入此輪。

### 來源、可回復性與操作者

- 操作者Codex；分支codex/009-release-classroom-codes。來源003作者itsusername15，PR9最終074b4a9ddba904b841b22371d632eea7a229e8f8，master merge7ae70542c26690193c2db4e97402d89dcd323c90；Afra0704的[核准審查](https://github.com/Afra0704/se2026-group20-speckit/pull/9#pullrequestreview-6073654519)由交接提供，本輪不代替其再核准009。
- git fetch --no-tags origin master核對FETCH_HEAD=7ae7054；沒有dirty pull或checkout覆寫。先於忽略的tmp/009-integration-checkpoint-20261126保留55個009檔案、原diff及SHA-256清單，另備份008外部檔但不修改；只提交009範圍為**added5a**（feat: checkpoint 009 classroom code reuse and student entry）。
- 接著git merge --no-commit --no-ff 7ae7054，db.py與workspace/classroom.html兩處文字衝突逐項保留兩邊能力：009專用升級／validate＋003 quiz schema同交易，009失效碼文案＋003腳本。自動合併後的讀交易巢狀寫入由新增測試發現並修正，不將「無文字衝突」當作整合通過。
- 本節驗證版本為added5a＋7ae7054合流工作樹，包含下列接線修正與正式測試；後續本機merge commit封存相同程式。008外部validation的SHA-256與整合前備份相同，特殊名稱未追蹤檔保留；master帶入的008 validation-followup文件屬上游歷史，不混稱本輪人工驗收。

### 正式接口與自動案例

| 範圍 | 預期／實際與證據 |
| --- | --- |
| Factory／schema | 使用003正式accept／progress／settled／recover_pending；db私有bootstrap原子初始化core＋009＋quiz＋Google，不漏quiz表；課堂重建保留已存在quiz_*／sqlite_sequence。新Google＋quiz測試故障rollback、重啟兩次及原密文／身份／結果保持。 |
| 截止與結算 | test_quiz_classroom_009中Event＋兩writer分別控制正式提交先commit（201且保留1列）／整堂關課先commit（409且0列）；保留正式同組重送與有效提交順位、兩組排名、不可變結果。close同交易queue、commit後try_pending，重送不重新結算。 |
| 結果讀寫交易 | 活動及課堂結果均先驗權並結束預檢read，再try_pending，最終以新read transaction重新驗權／組DTO。兩路由均有pending重試assert不在讀交易及「預檢後整堂關閉」409案例；CLOSED學生不取得任何結果，教師歷史仍讀原版本。 |
| 001依賴 | 正式003快照＋實際001儲存結構＋WritableSheets合成來源驗教師關課後回填預覽201、unknown報告保持、碼重用／重送close零自動重寫；甲乙舊資格409，明確加入新堂後亦不能讀舊活動。真Sheets未操作。 |
| 學生正式腳本 | 固定載入quiz-submission.js，移除早期無正式retry fallback；同學clearOwnOperation比較key及兩個201／409回歸完整保留。新增student-room-quiz-009實際載入兩個來源模組，驗輪詢失敗→清表單→重建→新送答→舊201／409晚回→新回覆遺失→原key／body可明確重試。網路失敗invalidate generation，舊表單不能回報新畫面已受理。 |
| 版本／來源編號 | 003-D22僅指OPEN晚加入結果，009-D22指永久關課／碼重用／學生禁讀；003原規格／確認紀錄保留，新增整合覆蓋註記，不虛構組員重新確認。 |

### 指令、失敗修正及回歸

1. 新tests/integration/test_quiz_classroom_009.py初次5失敗：4例確認try_pending進讀交易；1例測試直接seed catalog後001正常啟動回填名稱，使基線不完整。前4例拆開預檢／重試／最終讀；最後一例於取得升級指紋基線前先完成正常001 bootstrap，未取消資料保留檢查。相關classroom results／quiz schema／settlement **14 passed、5.48秒**。
2. 新student-room-quiz-009.test.cjs初次舊201晚回案例失敗、409通過；修正網路錯誤清表單時的generation後，009兩檔＋003原retry測試 **10 passed**；頁面／formal／Google原子性Python **12 passed**。tmp/repro腳本只作背景參考，正式證據來自tests檔案。
3. 首輪全pytest **1 failed、470 passed、98 subtests、90.29秒**；唯一失敗為舊pending測試把正式provider當成未接入。該受控案例改為明確GET_SETTLED_RESULTS=None結果的替代provider，正式pending／正常settlement另有獨立測試，沒有弱化正式結算斷言。其後補完整Google／quiz rollback、unknown報告及正式writer兩種截止順序，專檔 **9 passed、3.95秒**。
4. 最終`.venv/Scripts/python.exe -m pytest tests -q --tb=short --maxfail=5`：**475 passed、98 subtests passed，86.36秒，exit0**。全部Node收集tests/*.test.cjs後`node --test $nodeTests`：**45 passed、0 failed，295ms，exit0**。相較上輪452／38是合流版的自行重跑結果；003作者428及其他審查427／18／31保留為來源紀錄，不當作本輪證據。

### 對圖、收斂及未執行驗收

沿用既有Java PlantUML CLI全24份重渲染exit0；Codex開009三張及003 Sequence核對queue／commit後重試／最終讀交易及關課拒絕分支，詳見diagram-review.md。AI檢視不代稱真人新圖複核。

T051／T058依本次使用者授權完成正式provider自動整合，操作者及來源版本如上，不冒稱同學同步操作。converge再核19 FR／6 SC、四故事／R1～R8、七項架構決策、61任務及憲章I～VI；無未完成程式缺口，仍有1項MEDIUM partial人工／真Sheets／技術圖複核，附T061追蹤合流版本。61任務57完成／4未完成（T052／T055／T059／T061），故不能宣稱clean convergence或完整人工驗收。003 T035／T037及008原待辦不改。

啟動方式已追加quickstart整合章節：沿用原私有設定、原DB／key、明確CLASSROOM_MODE=1，操作者停止舊服務／備份後從目前分支啟動。Codex本輪沒有啟動真實服務、真DB遷移、Google網路寫入或人工排版驗收。
