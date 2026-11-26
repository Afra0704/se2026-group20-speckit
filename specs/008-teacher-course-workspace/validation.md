# 008 實作與驗證紀錄

日期：2026-11-25（Asia/Taipei）；執行者：Codex。使用者授權speckit-implement。

## 起始狀態

- 已建立 codex/008-teacher-course-workspace，沿用007與005/006未提交修改，無reset/stash/commit/push。
- requirements.md 16/16 PASS；extensions.yml不存在。
- 起始Python：`.venv/Scripts/python.exe -m pytest tests -q`，354 passed、98 subtests passed，104.88秒。
- 所有新增測試使用tmp_path暫存DB／合成Google，未使用操作者DB或私人憑證。未讀取或複製真實key；操作者真實DB/key備份尚未驗證。
- OpenSpec D21、具名技術互審與分工仍待補，不以本次授權代填。
- 真Google／人工任務T066–T070未執行，005/006/007原人工任務不變。

## 實作進度

進行中；下列只有實際執行證據才可勾tasks。

## 2026-11-26 續作與修正

- 起點HEAD：812037a46c244aa057769c1969a64c512092403e；實際分支codex/008-teacher-course-workspace。預定沿用DB：D:/os_final/instance/classroom-007.sqlite3；私人備份尚未由操作者回報。未啟動連接該DB的app、未讀私人key/client/token。
- .gitignore已覆蓋環境、憑證、instance、SQLite、tmp、Python／Node快取；本輪無Docker／ESLint／Prettier／Terraform／Helm設定需新增忽略檔。沿用原lock，未升級套件或安裝框架，Picker三設定只加佔位值。
- 使用者已同意分層頁、雙入口、課堂不可刪／講義可移除及I1/U1；D21、技術修圖與001/002/003分工具名確認未回報，T070不代填。
- 導覽先新增3個失敗測試（404），接線後3 passed；匯入先2個失敗測試（404），接線後通過；刪講義先失敗（缺端點），實作後通過。新增Picker、CAS、相容及恢復測試依失敗結果修正並重驗，不將後補測試全部宣稱為事先TDD。
- 第一輪全套26 failed／14 errors／320 passed：合成provider缺真實notes對應、直接provider unit缺attempt_id，以及既有confirm目標錯誤優先序。補測試資料而非取消正式guard；指定回歸48 passed，其後43 passed。
- 第二輪1 failed／379 passed／98 subtests：remove在DTO取得後發生時，預設活動名稱查詢先回404；已加active檢查維持410，屏障競態3 passed。
- Node最終指令：`node --test tests/workspace-navigation.test.cjs tests/import-menu.test.cjs tests/picker-flow.test.cjs tests/identity-ui.test.cjs tests/student-question-text.test.cjs tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs tests/activity-sync.test.cjs tests/notes-ui.test.cjs`，10檔、24 tests passed、退出碼0。DOM模型不是視窗／鍵盤／真Picker人工證據。
- 明確測試：007 populated DB重啟兩次＋init-db保留UUID／教師／課程／密文／immutable catalog、schema故障rollback；120秒接手雙retry與舊結果先回；同輸入冪等、修改選擇與舊確認拒絕；Picker真provider URL online/false/PKCE、scope／帳號／加密錯配、main密文不改、metadata／expiry／generation晚回；移除↔活動／版本、歷史固定版本、移除後未知回填先回讀恢復且勝組不變。Google及結果provider均為受控替代端，非真排名或真Google證據。

## 最終自動驗證（2026-11-26）

- `.venv/Scripts/python.exe -m pytest tests -q --tb=short`：退出碼0，391 passed、98 subtests passed，99.87秒。相較本輪起始新增37個測試；包含被修正的舊回歸，無skip或預填舊數字。
- 上述10檔Node：退出碼0，24 passed。`git diff --check`：退出碼0；uv.lock既有LF→CRLF提示不是失敗。
- 三圖CLI：`& 'C:/Program Files/Java/jdk-24/bin/java.exe' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar 'D:/os_final/diagrams/008-*.puml'`，退出碼0；PNG Component1698×1128、Class1654×935、Sequence1741×2934，與原設計責任一致。技術互審未代填。
- 定向檢查.env.example與本輪主要source無真實API-key樣式或私鑰標頭；只掃repo內候選程式／佔位設定，未開啟私人憑證。原Python lock與依賴選擇保留。
- extensions.yml於before/after implement、analyze、converge檢查均不存在，無hook需執行。

## 任務與證據對照

| 任務 | 實作／證據 |
|---|---|
| T001–T004 | 起始紀錄、原lock／忽略規則、Picker佔位設定、google_support/workspace_support及明確合成provider資料 |
| T005–T010 | workspace_007_compatibility：populated007重啟／init-db保留、失敗rollback；workspace.routes權限；原完整回歸 |
| T011–T020 | workspace_routes、workspace_navigation、workspace-navigation.test.cjs；分層模板、固定room／groups、新HTML保舊JSON |
| T021–T025 | picker_authorization、import_flow、import_flow_routes、import_flow_oauth及兩Node選單／Picker測試；shared Google官方驗簽／claims回歸 |
| T026–T032 | config、workspace.schema／repository；flow/context/cache/ticket/preview mapping/marker、真實FK與constraints |
| T033–T043 | import_flows、flow_context、picker_service、原service/provider/callback與notes最終flow guard；CAS／同帳號／scope／24h cleanup測試 |
| T044–T048 | workspace/import模板、import-flow.js／picker.js、局部Referrer與日誌、雙入口受控測試；原其他組答案可見範圍回歸 |
| T049–T062 | lecture_visibility、lecture_removal、lecture_removal_races、workspace_history；tombstone／原owner查詢／最終active guard／歷史與未知寫回恢復 |
| T063–T065 | README、設定／操作文件、三圖CLI及全套Python／Node／diff檢查 |
| T071–T072 | analysis.md與本紀錄的靜態對照／收斂、PR草稿；人工缺口保持未完成 |

測試檔名為上述實際名稱，集中helper於tests/workspace_support.py；不為符合計畫檔名重複建立空測試。未執行真Google／真人／具名互審的T066–T070與收斂T073保持未勾；不能宣稱008整體完成或可合併。005/006/007原未完成人工任務不變。

## PR 草稿（尚未建立或推送）

標題：`feat: add course workspace and on-demand lecture import`

教師登入後由課程卡片進入分層工作區，在課程內用雲端選檔或連結匯入講義，只有需要時才取得講義授權。匯入以固定課程／grant與版本化預覽防止晚到結果及重送誤存；講義移除保留活動、結果及回填歷史，課堂不可刪除。沿用原007資料與登入、005／006的全文與單活動行為。

驗證：391 Python tests、98 subtests、24 Node tests及git diff --check通過；原007資料／密文保留、OAuth安全邊界、CAS及刪除競態有受控測試。真Google Picker窄scope／來源限制、真人兩教師與兩組學生、窄視窗／鍵盤及D21具名互審尚未完成，PR應先作草稿，完成T066–T070/T073後再審交付。

分支含005／006／007既有未提交修改，以上前置成果需在正式PR說明範圍，不將它們隱藏或當本輪新產物。未commit、push、建立或合併PR；真實DB／key備份由操作者另行確認。


## 補充異常驗收（2026-11-26，PR #7 後續）

- 執行者Codex；使用合成Google帳號、暫存DB／受控Sheets，不是兩位真人或真Google驗收。
- 新增 `tests/integration/test_workspace_failure_acceptance.py`：非法連結／gid、403／404／503來源失敗及恢復、授權缺少、取消後舊確認、來源變動再預覽，以及已完成流程在授權失效後的防重開。
- 初跑13例：11 passed、2 failed。其中產品問題為已完成匯入再次read且缺少Sheets授權時被改成awaiting_sheets_auth；另一項是測試fixture的實體座標偏移，修正測試定位後重驗。
- 修正read先拒絕terminal、成功read重送直接用既有安全狀態；進入等待授權前在最終交易重檢狀態與revision，避免晚到授權檢查重開已完成流程。
- 指令 `.venv/Scripts/python.exe -m pytest tests/integration/test_workspace_failure_acceptance.py tests/unit/test_import_flow.py tests/integration/test_import_flow_oauth.py tests/contract/test_import_flow_routes.py -q --tb=short`：22 passed，退出碼0。
- 使用者回報My First Project的Drive／Picker API已啟用，Picker專用Web client已建立並另存JSON；API key限制與本機環境正逐步設定，未讀取／輸出真實key，未將上述狀態當作真Google連線通過。
- 本機5000未啟動、agent環境無Google設定。曾啟動獨立5001合成資料QA server；內建瀏覽器連線逾時，未據此勾瀏覽器視覺或真人任務。正式服務與真實DB未被當成測試fixture。

- 真實007 DB在QA前以SQLite backup建立一致副本：`instance/qa-backups/classroom-007-before-qa-47805bd9b8.sqlite3`（ignored），未查出或輸出個人資料，原Fernet key未變更。這次是實際DB備份，不再僅為「備份未回報」。
- 同目錄只核對檔名，確認web-client.json、web-token.key及picker-client.json存在；未讀取憑證內容。使用者正在同一CMD透過只顯示SET/MISSING的檢查補環境，不以此宣稱Google往返成功。

- 修正後完整回歸：`.venv/Scripts/python.exe -m pytest tests -q --tb=short`，404 passed、98 subtests passed，131.29秒，退出碼0；產品程式自該輪執行後未再變更。這次13個HTTP異常驗收案例均通過。
- 使用者回報SECRET_KEY及Picker三項環境均SET，原登入client／Fernet key路徑已補；正進行本機啟動與真Google驗收，尚未回報成功前不勾T066–T069。

### 真實 Google 操作進度（2026-11-26，使用者回報）

- 使用者在同一 CMD 啟動 127.0.0.1:5000 後，回報教師 Google 登入成功。
- 在課程講義管理由「＋匯入講義 → 從 Google 雲端選擇」操作，依步驟選講義副本、分頁與自訂名稱後，回報已看到正確題目全文與題數預覽。
- 證據來源為使用者逐步回報，Codex 未直接觀察瀏覽器或檢查實際授權 scope；保存與重新整理持久性正在驗收。此進度不代表兩位教師隔離、錯帳號、取消、權限限制、鍵盤與兩組學生等整套人工任務完成，T066–T070／T073 維持原狀。

- 使用者接續確認：講義保存後出現在原課程清單，重新整理後仍存在，名稱與題數皆與預覽一致。真實雲端入口的預覽、保存及重新整理持久性已有逐步回報；取消選檔與授權沿用正在驗收，其餘人工任務仍未勾選。

- 使用者對取消選檔驗收回覆「確認」；記錄為取消後未產生額外講義的使用者回報。是否再次要求授權未獨立明確回報，不據此宣稱授權快取行為已驗證。下一項為貼連結入口的單題講義匯入及兩份講義並存。

- 使用者確認貼連結入口的單題講義完成全文／題數核對、保存與重新整理，QA-連結-單題及QA-雲端-題組皆正確保留。證據仍為使用者逐步回報；開始驗收非Google Sheets連結的拒絕與清單不受影響。

- 使用者確認非Sheets連結 https://example.com/ 被提示錯誤，返回並重新整理後原有兩份QA講義保留且無新增。下一項驗收講義刪除二次確認的取消分支，尚不執行實際移除。

- 使用者確認刪除QA-連結-單題有二次確認，取消後重新整理兩份QA講義皆保留。下一項僅對該QA講義實際移除，核對指定清單項目移除、其他講義保留及Google Sheets原檔不受影響；歷史快照／回填恢復仍須另外驗收。

- 使用者確認實際移除QA-連結-單題後，重新整理清單已無該講義，QA-雲端-題組仍保留；直接開啟Google Sheets副本確認原檔與內容完整。僅記錄此項清單移除與雲端原檔保留，未以此代替歷史活動、結果及回填恢復驗收。下一項確認第二位真實教師帳號的測試可用性。

- 使用者回報第二個真實Google帳號可成功登入；尚未據此認定教師隔離或第二帳號Sheets／Picker授權通過。下一項交叉核對教師A既有驗收課程與教師B新建QA-教師B課程的清單可見性。

- 使用者確認兩位教師在我的課程清單僅見各自課程；教師B建立QA-教師B後，教師A重新整理仍看不到該課程，且A原課程及QA-雲端-題組保留。這是清單可見性人工回報，直接網址越權拒絕正在分開驗收。

- 教師B直接開啟教師A講義管理網址，使用者回報回應為COURSE_NOT_FOUND，context為空且retryable=false，未顯示A的課程／講義資料；回到B自己的QA-教師B課程可正常開啟。直接網址越權阻擋有人工回報證據。另記錄HTML導覽失敗直接顯示JSON的易用性問題，尚未修改或宣稱已修正。下一項驗收Picker授權Google帳號與目前教師不一致時的拒絕。

- 教師B發起雲端匯入、Google授權時刻意選教師A帳號，使用者回報提示「請選擇與目前教師相同的 Google 帳號連接講義。」符合錯帳號拒絕的預期；未因此宣稱scope內容已直接查核。下一項驗收改選B本人後可重新授權並開啟Picker，且教師登入身分不變。

- 教師B改用本人帳號重試雲端授權，使用者回報Google顯示「已封鎖存取權：Guided Notes未完成Google驗證程序」。本項真實同帳號恢復仍未通過，優先查核Picker所在Cloud專案的Testing測試使用者名單；不將Google端拒絕記為應用程式測試成功，也尚未判定程式缺陷。

- 使用者在Cloud專案測試使用者名單加入教師B後，回報授權可繼續，並進一步確認能開啟Google選檔視窗、網站教師身分仍為B，最後取消選檔。錯帳號拒絕後以同帳號重新授權的恢復路徑已有逐步回報證據；實際scope內容未直接查核。下一項為教師A與兩組獨立學生工作階段的建立後全文預覽及開始前禁止作答驗收。

- 使用者依第18步確認：教師A新QA課堂中，甲／乙兩個獨立學生工作階段加入同堂；建立QA-雲端-題組活動但未開始時，兩組皆可見完整題目、小題標號與作答欄，且不能輸入／提交。此為005／006／008跨功能路徑的使用者回報，不代替正式003搶答受理或結算驗收。下一項驗收未結束活動互斥、準備中直接結束與同堂切換活動。

- 使用者依第19步確認：已有準備中活動時無法再建立第二個未結束活動；準備中可不經開始搶答直接結束；同堂重新建立後甲／乙兩組不用重新輸入課堂碼即可看到新活動全文。證據為UI人工回報，真正並發請求的互斥另有自動測試，不混為此項人工證據。下一項為開始後可輸入及重新整理／同工作階段重開的課堂與組別恢復；不驗收未提交草稿持久性。

- 使用者依第20步確認：開始搶答後甲／乙兩組可輸入；甲重新整理、乙在同瀏覽器工作階段關閉再開原學生網址後，仍在原課堂與組別、題目全文不變且可繼續輸入。未提交答案，未將此項認定為正式003受理／順位／結算或草稿持久性通過。下一項驗收活動停止作答、課堂結束同步及拒絕新學生加入。

- 使用者依第21步確認：活動結束後甲／乙兩組不能再作答；課堂結束後兩組看到已結束提示；未加入過的學生使用相同課堂碼無法加入。正式003提交／結算仍未驗收。

### 待討論介面建議：已結束課堂的加入提示

- 提出者：使用者；日期：2026-11-26。使用者詢問是否應顯示「查無此課堂」而非「課堂已結束」，要求先記錄。
- 狀態：待確認顯示文字及適用畫面，不變更現有規格、程式或課堂生命週期。本次拒絕加入的功能驗收仍通過，提示文案建議另行追蹤。
- 建議區分：已加入學生收到結束通知時保留「課堂已結束」；新學生輸入課堂碼時可採「課堂碼無效或課堂已結束」。單寫「查無此課堂」可能使使用者誤以為輸入錯誤或課堂被刪除。
- 下一次功能迭代再確認文案及適用範圍；本輪不直接實作。

### 使用者確認：一次性課堂碼釋放與重用（2026-11-26）

- 使用者已同意以下需求，取代上段尚待確認的加入提示建議；確認者姓名未提供。這是使用者確認，不代表OpenSpec組或其他組員已完成確認。
- 課堂結束後永久關閉，教師不能重新開始，歷史資料保留。
- 結束時釋放課堂碼，之後可分配給其他新課堂；新加入入口僅查有效課堂碼，無有效對應時顯示「查無此課堂」。
- 學生加入與恢復資格綁定內部課堂ID及原組別，不僅綁課堂碼。原學生重新整理／重開舊頁面仍屬原課堂，顯示「課堂已結束」，不得因課堂碼重用自動進入新課堂。
- 加入後來使用相同碼的新課堂，必須重新執行輸入課堂碼與組別的加入流程。
- 狀態：已確認需求、尚未實作／驗證。下一輪依SpecKit流程建立規格、圖表、計畫與任務；本輪不直接修改程式。須涵蓋碼釋放與再分配競態、有效碼唯一性、舊恢復資格隔離及歷史保留，並與負責課堂模組的組員對齊。

- 使用者依第22步確認：教師A新QA課堂建立QA-雲端-題組活動後移除網站內該QA講義；甲／乙重新整理仍能看到原活動全文，老師仍可正常開始與結束既有活動。此為固定活動快照不受講義移除影響的人工回報；未提交答案，不包含正式結果或回填歷史驗收。下一項分開核對已移除講義排除於新活動選項及已結束活動的歷史題目存取。

- 使用者依第23步確認：教師頁重新整理後，新活動講義選單已排除移除的QA-雲端-題組；從已結束活動的講義／歷史入口仍可查看原題目。證據限講義內容及選單，不包含003結果或回填歷史。下一項為明確重新匯入同來源的新講義及舊移除狀態、舊活動保留。

- 使用者依第24步確認：以貼連結入口明確重新匯入同一題組來源，保存為QA-重新匯入-題組；原QA-雲端-題組未復活，舊活動仍保留原題目。下一項由使用者僅在Google Sheets講義副本的題目文字加入QA標記，分開驗證既有活動快照固定及新匯入讀取線上最新來源；不修改答案、題號或合併結構。

- 使用者依第25步確認：由QA-重新匯入-題組建立的活動，在線上題組副本第一小題末尾新增【QA來源修改】並儲存後，老師及甲／乙兩組重新整理仍顯示活動建立時文字，未出現新增標記。此為真實來源修改下活動文字快照固定的人工回報；下一項驗證新讀取預覽能取得標記，取消該匯入並還原副本。

- 使用者依第26步確認：新讀取題組副本的預覽含【QA來源修改】，既有活動無標記；已取消該次匯入，並移除副本內該標記等待儲存。真實線上來源的新讀取與既有快照固定已分別驗證。下一項為預覽後來源文字變動時，確認保存必須拒絕舊預覽並要求重新預覽；尚未回報結果。

- 使用者依第27步回報：來源在預覽後改動，按確認匯入時未看到提示，頁面直接重新載入並顯示新內容。本項不記為人工通過，等待修正後重驗；Google Sheets副本的【QA預覽後修改】標記尚待後續還原。
- Codex核對：confirm端點在來源變動時回409 SOURCE_CHANGED並產生新預覽；前端run直接reload，原錯誤訊息因此未顯示。後端未自動保存新內容，但教師無法從畫面理解仍須再次確認。
- 修正：來源變動回應前加入一次性頁面提示，沿用匯入頁既有role=alert顯示：「來源已變動，已更新預覽，目前尚未匯入。請核對最新題目與作答格後，再次確認匯入。」不變更原409、新預覽及再次確認契約。
- 擴充HTTP回歸：舊預覽失效後無catalog保存、新預覽頁顯示提示、提示只顯示一次、舊preview_id仍被拒絕、新預覽經明確確認才保存。
- 指令 `.venv/Scripts/python.exe -m pytest tests/integration/test_workspace_failure_acceptance.py tests/contract/test_import_flow_routes.py tests/integration/test_import_flow_oauth.py -q --tb=short`：19 passed，4.76秒，退出碼0。真實Google畫面重驗尚未執行，相關人工任務不代勾。

- 修正9147096後，使用者重啟Flask並依重驗步驟回報「確認」：再次修改副本來源、回預覽確認時可見來源已變動且尚未匯入的提示。此為提示修正的真實操作回報；未推論已完成新預覽的第二次確認保存。下一項取消該匯入、核對無誤存並還原測試副本內新增標記。

- 使用者依第28步確認：取消來源變動測試匯入後，重新整理無新增QA-預覽失效，原QA-重新匯入-題組保留；Google Sheets副本的本次測試新增標記已移除並還原。未提交新預覽保存。下一項為使用者人工鍵盤Tab／Enter／Escape及匯入表單、窄視窗操作檢查；尚未回報結果。

- 使用者依第29步回報「正常」：鍵盤Tab／Enter可展開匯入、Escape關閉並恢復焦點，貼連結表單可鍵盤操作；縮窄視窗後導覽、講義清單與表單可閱讀操作，按鈕未被遮住或切掉。僅為本次頁面範圍的人工回報，非所有裝置／輔助科技完整符合性聲明。下一項驗收同瀏覽器教師登出不清除學生資格，以及教師內容重新要求登入。

- 使用者依第30步確認：同一瀏覽器／設定檔的學生分頁加入QA課堂後，教師登出不清除原課堂與組別恢復資格；登出後直接開啟教師課程網址須重新登入。此為007教師／學生session隔離的人工回報。下一項由教師A另建限制存取且未分享給B的QA副本，驗收教師B貼連結讀取的真實Google權限拒絕與無誤存。

- 使用者依第31步回報真實Google權限拒絕訊息：「無法讀取來源，請確認Google帳號與講義分享權限。」該錯誤提示已確認，尚未單獨回報失敗後清單無新增。下一項先補查無誤存，再僅分享此QA副本給教師B編輯權限，測試原失敗流程重試與保存至B的課程，不公開檔案。

- 使用者依第32步確認：權限不足失敗時清單無誤存；教師A僅將QA副本分享給B編輯權限後，B於原失敗流程重試，可選分頁、核對全文並保存為QA-權限恢復，僅歸屬B課程。真實Google權限拒絕及補權限後恢復已有逐步人工回報；不代表回填寫入、順位或結算驗收完成。

- 使用者依第34步確認：另建QA-文字與資料隔離副本、匯入保存並建立活動後，甲／乙學生頁保留換行與Ω／😀，長英文正常換行，<b>QA粗體測試</b>以含尖括號的字面文字呈現，未解讀成HTML粗體；學生頁及作答欄未出現來源作答格測試值QA-來源答案-不應公開。此為純文字顯示及來源答案隔離的使用者人工回報；未執行腳本標籤或瀏覽器原始網路回應審計。下一項為真實單題副本整體插入欄列後辨識，以及兩組建立／開始同步實際計時。

- 使用者依第35步確認：真實單題副本整體左插兩欄、上插兩列後，匯入題數／全文／作答格對應正確；甲／乙保持學生頁開啟且不手動整理，建立後兩組看到完整題目、開始後兩組可輸入均回報不到1秒。此為使用者計時回報（非Codex儀器計時，無更細毫秒值），符合此輪兩項5秒內門檻。下一項只讀DB內scope／身分中繼資料進行去機敏安全核對，不解密或輸出token／Google識別值。

### 真實授權中繼資料核對（2026-11-26，Codex唯讀）

- 使用ignored腳本tmp/check-real-picker-metadata.py以SQLite mode=ro查詢既有007 DB；不讀取secret_blob、Google subject／email原值或client JSON，身分／client對應僅由SQL比較並輸出boolean。
- 兩筆實際保存的Picker credential，其正規化actual_scopes皆恰為openid、email、profile、https://www.googleapis.com/auth/drive.file；無額外broad scope。與同教師Sheets credential的client不同、issuer／subject皆對應同一google_identity、instance相同；Sheets狀態connected且granted_scopes含spreadsheets。各布林皆true。
- 此證據為成功Google交換後的持久中繼資料與程式既有驗證結果，不解密token、不呼叫tokeninfo，不額外宣稱完成nonce／aud封包人工審計或refresh token不存在的直接檢驗。metadata讀取首次比較使用Google長scope別名而得到false，依既有provider的email／profile正規化修正檢查腳本後結果皆true；產品程式未改。
- 缺scope／extra broad拒絕保持受控自動測試證據，不刻意向真實帳號授予額外權限。下一項真實短時間再次選檔的cache沿用人工驗收尚待回報。

- 使用者依第36步確認：完成必要本人授權並取消選檔後，一分鐘內再次發起雲端選檔會直接開啟Picker，不再要求選帳號／同意權限，最後取消。有效Picker cache沿用有真實人工回報。下一項驗收多分頁選擇、明確修改分頁與名稱、新預覽及只保存最後選擇；不將UI操作當作舊API確認ID拒絕的替代證據。

- 使用者依第37步確認：同一真實Sheets副本新增QA-分頁二並加入【第二分頁】標記；原分頁／QA-選擇前預覽後，使用明確修改入口改分頁／名稱，最新預覽含標記，保存後只新增QA-選擇後，未新增QA-選擇前。下一項為同教師兩瀏覽器分頁、兩課程、不同來源／名稱交錯保存的真實流程隔離。

- 使用者依第38步確認：同教師同瀏覽器兩分頁分別在原驗收課程／QA-並行課程建立單題QA-並行A與題組QA-並行B預覽，先B後A交錯保存，兩份僅歸屬指定課程，名稱／來源／內容未混用。此為人工交錯流程證據，不代替同時交易競態測試。下一項同CMD同DB／key重啟服務，核對登入、各教師資料及活動歷史保留。

- 使用者依第39步確認：同CMD、同DB／key停止並重啟Flask後，兩位教師各自保持登入，課程及剛匯入講義保留，先前已結束活動的原講義歷史仍可查看。未重建或清空DB。

### 本輪人工驗收彙整與限制（2026-11-26）

- 操作者：使用者及其操作的兩位Google教師、甲／乙學生工作階段；實際姓名與各瀏覽器版本未提供，不自行補填。使用者逐步回報結果，Codex未直接操控或截取這些Google畫面。前段使用9147096之前版本，來源變動提示重驗及其後使用9147096；本輪產品修改僅該提示修正。
- 已回報：雙入口、單題／題組／欄列移動、最新線上來源、預覽變動重確認、多分頁改名、取消、刪除及歷史、明確重新匯入、兩課程並行、兩教師資料與直接網址隔離、錯帳號拒絕／本人重試、測試名單補設定、權限拒絕／分享後恢復、有效Picker授權沿用、同堂單活動、建立後全文、開始前禁止作答、準備中結束、換活動／重新整理／重開、結束課堂拒絕新加入、來源答案隔離、純文字／換行／Unicode、鍵盤及縮窄視窗、教師登出保留學生及服務重啟持久性。移動版型單題的建立／開始兩組同步，使用者皆計時不到1秒。
- 實際尚缺：正式003答案受理／整組提交／順位／結算及真實回填、部分寫入恢復等整合；具名圖意／介面互審與D20／D21外部同步；指定1366×768與390×844數值尺寸、長名稱、彈窗／載入被阻擋及完整登入取消／失效流程等仍未獨立回報。OAuth重放、缺scope／額外scope、flow逾時、並發及故障恢復維持受控自動證據，不宣稱真人或真Google故障驗收。
- 因原人工任務為多項聚合，未以本輪部分回報直接全勾005／006／007／008人工任務。已取得的證據保存在本節及逐步紀錄，後續只補缺項，不重做已確認的操作。
- 課堂碼釋放與重用為使用者已確認的下一輪需求，不在本輪實作，保留前述規則與恢復隔離要求。

### 本輪收尾自動回歸（2026-11-26，9147096程式版本）

- `.venv/Scripts/python.exe -m pytest tests -q --tb=short`：404 passed、98 subtests passed，108.51秒，退出碼0。
- 原10檔Node指令：24 passed、0 failed，退出碼0；`git diff --check`退出碼0，僅既有LF／CRLF提示。
- 停止本輪由Codex啟動的tmp/qa-browser-server.py合成QA helper（依專用腳本路徑匹配）；未停止使用者5000真實Flask。tmp輔助檢查腳本不納入版本控制。
- 本輪已知UI改善：直接網址越權目前回JSON，權限阻擋正確；易讀HTML錯誤頁待後續確認，不擅自擴入本輪。課堂碼釋放／重用另列下輪SpecKit需求。

## PR #7 review 6070380173 修正（2026-11-26）

- 審查者itsusername15，review當時遠端head為276ec55。使用者明確授權修正並將本機後續修正與驗收紀錄一起push到原PR，不合併。
- T074先補回歸：Node 2 failed、HTTP 1 failed／3 passed，重現確認前GET新ID及表單未綁定畫面ID。修正表單hidden preview_id及提交handler，PREVIEW_STALE提示核對新內容，不自動確認。
- T074重驗：`node --test tests/import-confirm.test.cjs tests/import-menu.test.cjs`，5 passed；`.venv/Scripts/python.exe -m pytest tests/contract/test_import_flow_routes.py tests/integration/test_workspace_failure_acceptance.py -q --tb=short`，17 passed，5.15秒。HTTP證明A舊頁ID被409拒絕且無catalog保存，B新預覽明確確認才成功；不是人工雙分頁畫面驗收。
