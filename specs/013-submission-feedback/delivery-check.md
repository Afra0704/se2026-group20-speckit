# Issue18 交付檢核

記錄日期2026-11-28（Asia/Taipei）。執行者Codex；人工回報者為本聊天室使用者，姓名未提供。核對整合版本3f55492與人工紀錄提交8f9f392；未將此份文件冒認已在PR26遠端。

## PR26交付副本

依使用者指示，從PR26 f300a0b建立獨立文件分支，將已完成的驗收與交付證據同步至本目錄，不合入#15的品牌程式。人工記錄置於integration-manual-acceptance.md，保留整合版本與受控工具限制。http.py、submission_gateway.py、repository.py、quiz-submission.js與student-room.js的SHA256逐檔比對與已驗收整合版相同；PR原版完整測試另記validation.md。下文「尚未同步／遠端未操作」為本機核對時點紀錄，GitHub實際狀態以PR／Issue操作結果為準。

## 結論

已完成文件一致性分析、實作對照、需求追溯及重跑相關測試，未找到新增功能程式阻斷缺陷。前次Converge結果為`tasks_appended`，追加T020–T021兩項交付證據；後續使用者已完成S1–S3並回報同學已審核更新圖。最後Converge結果為`converged`，沒有新任務，T017–T021已依證據補齊。這表示本機Issue18範圍可交付，不表示已執行GitHub approve、merge或close；文件仍須同步遠端PR26。

## Analyze（唯讀階段已結束）

- 使用程序限定SPECIFY_FEATURE_DIRECTORY=specs/013-submission-feedback及SPECIFY_FEATURE_NO_PERSIST=1，check-prerequisites成功定位指定功能，不改feature.json或切分支。
- 核對8 FR、4 SC、3故事共9項驗收條件、原19任務；FR／SC任務覆蓋12/12（100%），無未映射任務、無新增歧義／重複／衝突。未完成的交付任務不視為程式已失敗，也不視為全功能已完成。
- 6項憲章原則均檢查；沒有新增資料表、重建身分、放寬權限或新Google授權。待補圖意複核與人工證據阻止宣告交付完成，未被忽略。
- .specify/extensions.yml不存在，before／after analyze與converge無hook執行。

## 需求、程式與證據

| 來源 | 實作／任務 | 證據與當前限制 |
| --- | --- | --- |
| FR001／SC001、US1/AC1–3 | submission_gateway.validated_answers、student-room欄位、quiz-submission.blank／showFields；T004–T007 | 後端空白／漏填拒絕、原文與Unicode；前端欄位焦點／ARIA；人工06–07通過 |
| FR002／SC002、US2/AC1–3 | attach.update／run、student-room.render；T008–T011 | 五狀態、兩題分離／活動切換；人工08、10、13–18通過 |
| FR003／SC004 | aria-invalid／describedby、feedback role=status、CSS；T005／T007／T017 | 教師及兩組、人工12四寬度／鍵盤通過；受控Chrome52版面、2鍵盤、2提示另列非真人 |
| FR004 | rejection、api傳status／Retry-After，連線與本題分開；T008–T011 | 人工15限流／503、18階段／資格拒絕；均為合成回應而非真限流／撤銷 |
| FR005／SC003、US3/AC1–2 | pending.save/read、run(true)、repository.replay／accept；T012–T016 | 人工13未達與14真201後回覆丟失皆原文／順位1；Node同頁恢復／複製、Python受理筆數／舊操作不覆蓋。未決F5／複製真人待T020 |
| FR006、US3/AC2–3 | scopeOf／isLatest／isVisible、#17生命週期；T003／T012–T016 | Node新pending不被舊201／409清除；人工16跨活動晚回。人工11只有草稿重新加入，不能冒認有pending時已測；待T020 |
| FR007 | 既有submission_context、quiz.repository與結果／在線；T002／T014／T016 | Python CSRF／關課／競態、Node在線／終態；人工05／09／12／18，原順位與角色邊界保持 |
| FR008、A1邊界 | run(true)固定operation.body、conflict相容標記；T012／T015 | 人工14–15改文保留、17合成A1阻擋；Node衝突持久及同頁恢復。A1更新圖待組員複核T021 |

## 圖對碼與三類圖檢查

| 圖 | 目前程式責任 | 核對結果 |
| --- | --- | --- |
| Component | Form=student-room.render；Feedback／Pending=QuizSubmission.attach/read/save；Tab=#17 activate/rejoin；Accepted=submission_gateway/repository | 責任與圖一致，無需修圖 |
| Class | Scope五欄序列化、Field原文／notice、Op UUID＋body＋選填conflict、Hint本題state、Result正式受理／有效答案 | 資料關係一致；圖是概念類別，不另造同名Python類別 |
| Sequence | 空白不建立操作；201／明確拒絕／未知；原操作重試；A1保留未決與改文；晚回作用域／嘗試檢查 | 與現行分支一致；A1差異的組員複核未回報，不冒填 |

Java24／PlantUML1.2026.10對三個puml執行checkonly，退出碼0。三份既有PNG簽章皆89504E470D0A1A0A，分別33136／31665／84737 bytes。未改圖意或重新產出PNG；沿用原diagram-review.md的CLI渲染證據。本次第一次PowerShell未將-Djava.awt.headless=true加引號，Java未執行PlantUML；改正參數後重跑成功，不將前次exit狀態當成功。

## 測試結果

本次重新執行：

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& D:/os_final/.venv/Scripts/python.exe -m pytest tests/contract/test_quiz_submission.py tests/integration/test_classroom_submission_races_009.py -q -p no:cacheprovider
node --test tests/quiz-submission.test.cjs tests/student-room-quiz-009.test.cjs tests/student-room-009.test.cjs tests/student-presence-lifecycle.test.cjs
```

結果：Python7 passed（2.47秒），Node36 passed／0 failed／skip。這些是相關子集，不加到先前完整628 Python＋98子測試、95 Node數目，也沒有宣稱本次再跑全套。產品程式自3f55492後未變，故沿用既有完整回歸證據；Windows1項POSIX skip保持。

人工18/18已回報通過，細節見integration-manual-acceptance.md。與本Issue直接相關：06–08驗空及本題提示、09兩組順位、10清舊提示、11草稿重新加入、12窄視窗／鍵盤／關課F5、13–18受控錯誤。真201延遲／遺失與未送後端的合成429／503／409／401分開記錄，不以畫面推定DB筆數。

## 補測步驟（T020）

先重新加入仍開放的測試課堂，由老師確認活動LIVE；不要用已關閉課堂。暫時停在資格失效提示的頁面可走明確重新加入。

在學生Console執行一次性回覆遺失工具；它會先讓真送答完成，僅吞掉一次201，之後自動還原fetch：

```javascript
(() => {
  const original = window.fetch;
  window.fetch = async function (...args) {
    const response = await original.apply(this, args);
    const url = typeof args[0] === 'string' ? args[0] : args[0].url;
    if (url.includes('/submissions') && response.status === 201) {
      window.fetch = original;
      throw new TypeError('QA: accepted response lost');
    }
    return response;
  };
})();
```

1. S1：填「補測原答案A」並提交至結果未知，F5。預期無自動送答，但仍可手動重試；按重試成功，教師核對仍為原答案及原順位。此項不要求普通未送草稿F5保存，那屬#15待做範圍。
2. S2：再用一次性工具送「補測原答案B」至未知，瀏覽器原生「複製分頁」。新頁取得獨立資格，不顯示原頁的重試；原頁仍可重試，不被複製頁清除。不在原頁操作前先按新頁重新加入。
3. S3：保留原頁這次pending，按重新加入先取消，預期原頁重試仍在；再確認，預期只原頁回空白加入頁。複製頁與另一組仍可依自己的有效資格操作；原組正式答案不刪。教師最後核對答案B及原順位。

以上步驟建立時尚未回報，後續S1–S3已由使用者依序回報通過，另回報同學已審核A1更新圖。未提供姓名／外部紀錄，不代填。詳見下方最後核對；#15草稿／Google品牌不混入#18完成條件。

## 最後Converge與完成紀錄

2026-11-28，使用者確認S1–S3及同學圖審後，再以程序限定功能目錄執行check-prerequisites成功。核對8 FR、4 SC、9故事驗收條件、7組設計義務（技術架構、作用域儲存、五狀態、錯誤分類、原文與查重、圖對碼、驗證交付）及6憲章原則；現有21任務不因勾選而豁免證據核對。缺口missing／partial／contradicts／unrequested均0，無新增嚴重度項目，結果converged，不追加空Convergence段落。

唯讀收斂核對前後tasks SHA256皆6E36931C7365362DF0FA0E9AA06F9341B912C4C96BDB2E05DDE0764788D90626，符合無缺口時不改檔規則。其後進入使用者授權的交付文件整理階段，才將T017–T021依證據勾選並同步本紀錄，非converge階段改寫舊任務。

- S1已確認F5保留pending及手動原樣重試；草稿消失如實記錄，不混同#15待做草稿功能。
- S2原生複製不承接原頁重試，原頁pending保留；S3取消保留、確認只撤原頁、複製頁／另一組及正式答案／順位不受影響，均由使用者回報通過。
- 同學審核依使用者在T021脈絡回報記錄；不將此視為GitHub review狀態已更新。
- 圖與產品程式均未改；沿用本文件已列測試，不為純文件變更重跑完整測試。前次18項＋新增3項為21個已回報通過的人工作業案例；受控／真請求限制仍適用。
- Issue18範圍交付核對完成，可準備更新／審查並合併PR26及關閉Issue18；遠端操作尚未執行。Issue15仍有自身未完成工作。
