# 009 實作與驗證指南

009 已實作 OPEN 有效碼唯一性、非破壞升級、關課學生禁讀與獨立加入／固定課堂頁，並合入master7ae7054的正式003 provider。自動驗證結果以 [validation.md](validation.md) 最新記錄為準；教師加兩組人工／真Sheets驗收由使用者後續執行，不宣稱完整交付。沒有啟動操作者服務、遷移真DB或操作Google。

## 前置條件

先完成 tasks／analyze、003 契約核對及受影響跨組行為同步，實作後再照本指南驗證。使用既有 Python 3.13、uv、Node、Java／PlantUML；不為 009 更換 OAuth client、key、secret 或 Google 授權。原環境詳見 [008 quickstart](../008-teacher-course-workspace/quickstart.md)，原人工與互審待辦保持。

自動測試全部使用 tests 的臨時 DB／受控 Google／結果 provider；不得以操作者 DB 當 fixture。schema 測試自行建立有資料的 007／008 fixture，包含兩教師、課程、已開／已關堂、組別、加入／授權、活動、固定版本、回填／未知報告及範例密文，不複製私人 key 或真實憑證。

本輪沒有操作真 DB。未來若要在原操作者 DB 部署，須先通過以下隔離證據，由操作者停止舊服務並依既有方式備份 DB 及原私有 key；沿用原資料，不能切新空白 DB 掩蓋升級失敗。禁止新舊服務同時寫同 DB。

## 既有測試入口（實作完成後執行）

從 repo 根目錄，使用已安裝依賴：

```powershell
Set-Location D:/os_final
& D:/os_final/.venv/Scripts/python.exe -m pytest tests/contract/test_classroom_management.py tests/contract/test_classroom_memberships.py tests/contract/test_classroom_results.py tests/integration/test_classroom_close.py tests/integration/test_classroom_bootstrap.py tests/integration/test_google_schema_atomicity.py tests/integration/test_workspace_007_compatibility.py -q
$studentTests = Get-ChildItem D:/os_final/tests -Filter 'classroom-*.test.cjs' | Select-Object -ExpandProperty FullName
node --test $studentTests
```

下列009專用測試已建立；原CLOSED恢復／結果可讀與新加入409已按新契約更新，同時保留教師歷史與課堂OPEN時的活動結果檢查。受影響檢查通過後才跑全Python及Node測試。

### 009 專用測試入口

```powershell
& D:/os_final/.venv/Scripts/python.exe -m pytest tests/integration/test_classroom_code_schema.py tests/integration/test_classroom_schema_failures.py tests/integration/test_classroom_code_lifecycle.py tests/contract/test_classroom_recovery_009.py tests/integration/test_classroom_history_009.py tests/integration/test_classroom_code_races.py tests/integration/test_classroom_join_races.py tests/integration/test_classroom_submission_races_009.py tests/contract/test_student_entry_009.py -q
node --test D:/os_final/tests/student-entry-009.test.cjs D:/os_final/tests/student-room-009.test.cjs
```

任務範圍見[tasks.md](tasks.md)：T005共用fixture，T006～T007 schema，T015生命週期，T023～T024恢復／歷史，T033～T035競態，T040～T042及T048頁面測試。首次分階段只跑已建立的對應檔案，上述合併命令留T050整合後使用，不能在任務生成階段執行。

## 隔離驗收矩陣

| ID | 操作／輸入 | 必須成立的結果 | 追溯 |
| --- | --- | --- | --- |
| V01 schema | 空 DB 初始化；populated007／008升級；再啟動兩次及init-db；每個重建階段故障／Google bootstrap故障注入 | 單一009版本；全部原值／FK／trigger、UUID及密文保持；故障完整rollback、無半份Google schema、foreign_keys恢復ON；未知schema停止 | FR-002、010；data-model |
| V02 格式及分配 | 以fixture產碼候選AB123；輸入ab123、首尾空白、AB 123、空白／非字串／超過32字 | 正規化符合FR-014；不誤吞內部空白；輸入錯誤與JOIN_DENIED清楚；不得人工指定正式碼 | FR-014；lifecycle |
| V03 關課／重用 | A碼C，兩組加入；結束A；fixture令B抽到C；同／異教師及課程；重送結束A；直接重開A | A永久CLOSED、原活動結束、C立即可用、B新ID；至多一OPEN；重送不改時間／版本／B；重開拒絕 | FR-001～008、015；R1、R3、R4、R7 |
| V04 真並發 | 多連線屏障控制R1～R8先後；分配碰撞12次、write busy、關課中transition故障 | 成功結果固定原堂／活動；失敗rollback；不在同請求改投新堂；503不假成功；先受理答案仍保留 | FR-012～013；lifecycle |
| V05 學生禁讀 | A關課成功commit後新發起各內容讀取交易，以尚有效grant、proof、直接room state／room results／activity results／submission／恢復；偽造teacher header及別組ID | state僅最小結束提示或拒絕；其他內容拒絕，JSON無題目／組名／答案／順位／勝組；C重用不解鎖；teacher header不授權 | FR-007、009、017 |
| V06 頁面／恢復 | /student輸入成功／失敗／連點；固定A頁重整、grant到期proof有效；離線再上線；B加入後A舊頁、舊恢復晚回 | 獨立加入頁成功才導頁、無常駐提示；開放恢復仍A／原組；closed不發grant；A頁不追隨B；教師session保持 | FR-016、018 |
| V07 結果／歷史 | 活動CLOSED但課堂OPEN看D06；課堂關閉後學生拒絕，教師讀原歷史／結果；pending結算；001未知回填恢復 | 學生僅開放堂可看；教師仍可看原結果／固定版本，未結算RESULT_NOT_READY；無假勝組或自動重送來源 | FR-010～011；quiz-history |
| V08 權限 | 未登入、其他教師、學生直接close／建堂；confirm缺少；CLOSED→OPEN／改歸屬約束 | 無權／不確認拒絕，不變更有效占用；永久關課DB約束生效，非課堂002模式保持 | FR-001、009 |
| V09 返回／晚回 | 關課前在同一讀取交易合法驗OPEN的狀態或結果，延遲至前端確認CLOSED之後回來；BFCache／pageshow／pagehide；換活動後舊結果；窄螢幕／鍵盤 | 先清內容再驗權，terminal不被覆蓋；無跨活動資料；只顯示結束＋按鈕，按下才回加入頁 | FR-012、017a、SC-006 |

同碼重用以測試替換產碼候選完成，不新增公開指定碼端點／UI／正式設定。並發測試須控制實際多連線的確認順序，單執行緒連續HTTP不算競態證據。V01每次故障後須驗下次啟動可恢復，不只驗例外有拋出。

## 人工流程（教師＋甲／乙兩組）

實作及隔離測試通過後，沿用原環境啟動方式；先確認運行的是待驗版本。依SC-005，教師與至少兩組學生人工驗收關課、結束提示、返回獨立加入頁及手動加入新堂；不要求隨機抽到同碼。同碼重用／舊資格隔離另由受控fixture證明，兩類證據分開記錄，人工環境不加指定碼開關。

1. 從首頁選學生，甲／乙各自獨立加入頁，以教師A的新課堂碼及組別加入；成功後進入課堂內容，上方沒有登入提示／加入表單。
2. 教師建立活動，甲／乙看到全文但PREPARING不可填；LIVE才可答。正式003尚未接線時只記可觀察介面，不能假稱排名完成。
3. 活動結束但課堂仍OPEN，已結算時甲／乙看D06可見結果；未結算明示等待。重整／同瀏覽器重開仍原堂／原組別。
4. 教師確認整堂結束，甲／乙在正常本機目標5秒內轉成「課堂已結束」，題目及結果消失，只留「加入其他課堂」；重整／舊網址不能讀回內容。
5. 按「加入其他課堂」才回獨立頁，輸入新堂碼＋組別才加入。A舊頁不可跟著變B，不能由舊資格取得新堂內容。沒有新有效對應的舊碼顯示「查無此課堂」。
6. 教師仍可讀原歷史，未結算保持等待；001真實回填／未知恢復另按001指南及授權操作，不能把受控provider當成真Google或正式003證據。
7. 驗鍵盤Tab／Enter、按鈕pending／錯誤復原、斷線再連、返回舊頁、桌面及390×844窄螢幕可讀可操作。教師登出不抹學生原資格；課堂CLOSED本身仍使學生不可讀。

## 之後的啟動命令界線

沿用007／008私有環境變數與既有DB路徑，不在文件填真secret。只有完成實作／備份及操作者決定部署後，才使用既有 `python -m flask --app guided_notes:create_app init-db`／`run` 入口；009遷移需在app提供請求前完成。這些命令會啟動schema處理，本輪沒有執行，也不得以未完成009程式直接對操作者DB驗收。

## 證據記錄

每筆記執行者、日期、branch／commit＋dirty檔案摘要、scenario或命令、預期／實際、結果及去機敏截圖／輸出。分成「受控自動」、「正式003整合」、「真人」、「真實Google」四類，未做填未執行。附R1～R8逐項結果、schema故障回復及原資料指紋比對。不得記proof／token／cookie／key；目前全部產品驗收均未執行。

## 003＋009 整合後的啟動與自動檢查（2026-11-26）

前面「尚未正式003／全部產品驗收未執行」為舊階段紀錄；目前正式自動整合已通過，真人與真Sheets仍未執行。舊模式移除另開SpecKit迭代，因此此版仍須明確設定課堂模式。

在**原先已載入私有設定的PowerShell**執行；不要換secret／key／OAuth client，不套用007起步清DB步驟。先停止舊服務並由操作者備份原DB與原私有key，再啟動此版。建立app會自動驗證／升級schema，失敗即停止，不會切換空DB。本輪沒有代替使用者執行以下服務啟動。

```powershell
Set-Location D:/os_final
$env:GUIDED_NOTES_CLASSROOM_MODE = '1'
# GUIDED_NOTES_DATABASE、SECRET_KEY、Google／Picker私有設定沿用原環境。
$env:FLASK_DEBUG = '0'
& ./.venv/Scripts/python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

開啟 `http://127.0.0.1:5000/`，教師走既有Google登入；甲乙兩組建議使用兩個瀏覽器設定檔，從`/student`輸入課堂碼／組別。驗LIVE整題送答／重送、活動結束但堂OPEN時D06結果、整堂結束禁讀、返回加入頁及手動新加入，教師原結果與回填預覽仍可用。真Sheets確認寫回仍由使用者明確操作。

只重跑自動驗證時不需載入真Google設定，測試自行建立臨時DB及合成來源：

```powershell
& ./.venv/Scripts/python.exe -m pytest tests/integration/test_quiz_classroom_009.py tests/integration/test_classroom_history_009.py tests/contract/test_classroom_results.py -q
node --test tests/student-room-quiz-009.test.cjs tests/quiz-submission.test.cjs
# 完整回歸
& ./.venv/Scripts/python.exe -m pytest tests -q --tb=short
$nodeTests = Get-ChildItem ./tests -Filter '*.test.cjs' | Select-Object -ExpandProperty FullName
node --test $nodeTests
```
