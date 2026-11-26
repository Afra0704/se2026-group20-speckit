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
