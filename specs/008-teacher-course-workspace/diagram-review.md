# 008 圖意與 Specify 檢查紀錄

日期：2026-11-25（Asia/Taipei）；AI 執行者：Codex。產品程式未修改，未建立 plan/tasks，不 commit/push。

## 使用者依據

- 使用者同意分層教師頁，要求課程內參考附圖的課程橫幅／左側導覽／右側內容。
- 「＋匯入講義」展開雲端加入與貼連結，操作時才取得必要講義授權；有效授權不反覆登入，教師身分仍沿用 007。
- 最新更正：「算了 課堂不能刪除 講義可以」。已從規格及三圖移除課堂刪除，課堂只結束並保留歷史。
- 講義刪除採清單移除、保留活動／回填依賴及雲端原檔的預設；不另造永久清除或回收桶功能。D21 同學／OpenSpec 新確認尚未回報。

## CLI 與結果

```powershell
& 'C:/Program Files/Java/jdk-24/bin/java.exe' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar 'diagrams/008-*.puml'
```

退出碼 0；三張 PNG 同目錄：Component 1242×977、Class 884×804、Sequence 1306×1688，均有有效 PNG 簽頭及非零尺寸。Codex 已查看 Class PNG，文字與關係可讀，其餘依 CLI／來源互動對照。

- Component：分層導覽、原權限、按需授權、兩來源接同一辨識／預覽、清單移除與歷史依賴。
- Class：教師→課程→講義／版本與課堂／活動；匯入固定原課程與教師，講義可見性與既有引用分開，不預先決定 DB schema。
- Sequence：按＋不授權，實際來源操作才檢查，回來再驗同人／原課程；保存前重檢；移除前二次確認、與新引用競態明確先後；沒有課堂刪除。

## 文件檢查

Spec 20 項 FR、8 項 SC、三故事 19 個驗收情境；品質清單 16/16，沒有未解的 NEEDS CLARIFICATION。範本經 resolve-template.ps1 spec-template -Json 解析。feature_numbering=sequential，008 是下一個目錄；無 extensions.yml，前後 hooks 無需執行。

第一次額外執行 check-prerequisites -RequireSpec 時，腳本仍要求 plan.md，因本輪尚未進 plan 而回報缺少 plan；這不是規格驗證失敗，也沒有為了通過它建立空 plan。改以 PathsOnly 核對 008 路徑，必要章節與檔案另以靜態檢查確認。

Git 仍為 codex/007-google-teacher-login，沒有 before_specify branch hook，因此不聲稱已切 008；後續實作可建立 codex/008-teacher-course-workspace。本機 .specify/feature.json 已指向 008。保留所有 005/006/007 未提交修改、資料與原人工任務；不讀憑證或改 Google Cloud。

## 同學待核對

審查者姓名、日期及結論：尚未提供，不由 AI 勾完成。請核對三圖與導航：課程／課堂邊界、雙入口／授權時機、同帳號及課程續接、講義移除與既有活動／回填、新引用競態，以及課堂不刪除。OpenSpec D21 同步及這輪 001/002/003 分工待補。

Plan 再研究雲端選檔最小權限、瀏覽器短期憑證與 007 後端 token 邊界、舊路由／資料處理、可見性原子規則及測試；specify 不選定或實作這些技術。圖意審查後可進 plan，不需要重跑 007。


## Plan 授權、技術展開及檢查（2026-11-25）

使用者明確回報「核對完畢」並允許plan；此為使用者回報的圖意核對完成，不補審查者姓名或獨立紀錄。原specify階段的「尚未核對」為當時狀態；同學對本次技術差異的互審／分工及OpenSpec D21仍未回報。

- Component：專用Picker cache／交付ticket、原attempt可信sidecar與分派、原Sheets服務；flow固定course/grant及按需授權，HTML/JSON路由分開。
- Class：具體落入flow/context/cache/ticket/preview mapping/tombstone等附加表，舊007與immutable版本保留。attempt FK標明CASCADE/SET NULL，避免舊24小時清理阻擋登入；取消／過期ready preview失效，不從舊URL繞過。
- Sequence：原nonce/PKCE/claim→外網→finalize重檢，Picker與Sheets各自同人授權，只有窄token交前端；selection外網後再驗cache generation；保存與flow completed同交易；移除與新引用明確線性化，歷史保留。
- 技術差異：Picker token可在受限POST交官方元件；乾淨匯入HTML局部strict-origin-when-cross-origin以配API key限制，callback/token仍no-referrer；這是計畫，未改http.py或真實設定。

實際命令：

```powershell
& 'C:/Program Files/Java/jdk-24/bin/java.exe' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar 'D:/os_final/diagrams/008-*.puml'
```

退出碼0。最終PNG尺寸：Component 1698×1114、Class 1654×876、Sequence 1694×2446，PNG簽頭／非零尺寸通過。Codex已查看Class PNG，文字及關係可讀；其餘以CLI及來源關係核對。這不代替同學對本次技術修圖的審查。

Phase0由本技能要求的兩研究代理唯讀核對Google授權及現有可見性／歷史接線；發現attempt cleanup FK與selection晚回重檢缺口，已在設計補正，沒有改程式或DB。官方事實、協定推論與真實待測分開記research.md；尚無本輪OAuth或產品測試結果。

靜態檢查：8份plan設計檔完整、無未解技術標記／模板佔位、文件相對連結存在、原16/16規格清單保持；check-prerequisites識別008且列research/data-model/contracts/quickstart，未建立tasks。git diff --check通過，uv.lock既有LF→CRLF提示不是新設計錯誤。

實際Git仍codex/007-google-teacher-login；setup-plan輸出008是功能路徑解析值，不表示切分支。005未完成T033/T034/T037，006未完成T002/T036/T037/T041/T042，007未完成T056/T057/T058/T060/T062/T063均保持。extensions.yml前後均不存在，無hooks需執行。未執行app/init-db/GoogleOAuth、未讀私人檔、不commit/push。

產物：plan.md、research.md、data-model.md、contracts四份、quickstart.md；下一階段tasks前需同學核對上述介面差異／修圖與D21狀態，不重新要求已確認的課堂不可刪或雙入口需求。

## Analyze I1／U1 文件補正（2026-11-25）

使用者同意採建議後，Codex同步spec、plan、research、data-model、import-flow契約、navigation、quickstart與既有tasks。I1明定reading claim到期仍可明確retry、輸入快照保留、單一接手及舊結果拒絕；U1明定同輸入才冪等，新增revise／choice_revision並失效舊preview，completed不能修改。三圖同步表達，新增技術圖意仍待組員核對，不代填OpenSpec D21確認。

實際執行：`& 'C:/Program Files/Java/jdk-24/bin/java.exe' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar 'D:/os_final/diagrams/008-*.puml'`，退出碼0；三張PNG均晚於各自puml，Class 1654×935、Component 1698×1128、Sequence 1741×2934。已開啟Sequence PNG檢視新增分支，無裁切。

靜態檢查：契約／模型／計畫／任務均含choice_revision、revise、retry；移除只允許failed的矛盾敘述。任務仍T001–T072連續72項，全未勾。git diff --check退出碼0，既有uv.lock LF→CRLF提示無關本次文件。此為針對兩項補正的靜態檢查，非重新完整speckit-analyze；未執行產品測試、人工驗收、程式／DB變更或commit/push。

## 008 實作後對圖（2026-11-26）

Codex對照Component→workspace.routes／flow_context／picker_service／lecture_lifecycle，Class→workspace.schema與notes tombstone，Sequence→外網前claim、外網後重檢、notes出版同交易、revise及活動／版本移除線性化。groups僅讀原classroom_groups，屬原Rooms責任，不變更三圖圖意。真實scope、來源限制與人工作業未由AI對圖替代。

實際CLI `& 'C:/Program Files/Java/jdk-24/bin/java.exe' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar 'D:/os_final/diagrams/008-*.puml'` 退出碼0；Component1698×1128、Class1654×935、Sequence1741×2934。技術互審仍待組員具名記錄。對應T064；本次不是同學審圖完成證據。

### 2026-11-26 PR #7 審查修圖（待同學複審）

007 Sequence補基礎／課堂／Google schema與auth_instance原子初始化；008 Sequence補Picker cache最終交易重驗、當前畫面preview_id及PREVIEW_STALE／SOURCE_CHANGED拒絕與再次核對分支。未新增Component／Class資料關係。兩圖已CLI重繪PNG並由Codex檢視；此處只記技術修改，不代填組員圖意核准。具名複審及D20／D21外部同步保持原狀態。
