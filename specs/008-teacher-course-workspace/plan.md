# Implementation Plan: 教師課程工作區與雙入口講義匯入

**Date**: 2026-11-25（Asia/Taipei） | **Spec**: [spec.md](spec.md)
**Branch**: 實際仍為 `codex/007-google-teacher-login`；預定實作分支 `codex/008-teacher-course-workspace`。setup-plan 的 BRANCH 為功能路徑解析值，不是已切換 Git 的證據。
**Status**: 2026-11-26：008受控實作與自動驗證已完成，真Google／人工／具名互審及D21仍待完成；不宣稱整體驗收。005/006/007修改與原人工任務保持，未操作操作者DB或commit/push。
**Input**: 使用者於 2026-11-25 回報「核對完畢」並允許 plan；核對者姓名、獨立紀錄尚未提供。OpenSpec D21、分工與本次技術修圖互審未回報，不自行填完成。

## Summary

沿用 Flask app、TeacherContext、原 grants、課程與 notes／活動服務，新增分層 HTML workspace；舊 JSON 不換 HTML。教師歡迎頁→課程卡片→課程橫幅／側欄／單區內容，進指定課堂才顯示組別與活動控制。

匯入 flow 綁教師、目前 browser/grant、原課程及來源方式，實際選雲端／明確讀連結才檢查授權。官方 Picker 使用專用 Web client、online-only 窄 token；後端先驗同 sub／實際 scope 才交付，原 Sheets refresh credential 保持後端。兩入口接同一分頁、命名、辨識、預覽與確認。

講義以 import_id tombstone 移除一般清單及新引用，不硬刪版本、來源、活動或回填。新活動／新版本最終 write transaction 再驗 active。課堂與課程沒有刪除功能；沿用 007 DB 附加 schema，不清空資料。

## Technical Context

**Language/Version**: 現有 Python 3.13.1、JavaScript、HTML/CSS/Jinja。
**Primary Dependencies**: 現有鎖定 Flask 3.1.3、google-auth 2.63.1、google-auth-oauthlib 1.5.0、google-api-python-client 2.202.0、cryptography 50.0.2；不變更 Python lock，不加 SPA 或打包工具。Picker 使用官方瀏覽器庫。
**Storage**: 原 `instance/classroom-007.sqlite3`、原 auth_instance 與 repo 外 key。新附加 flow／OAuth context／Picker cache／removal／schema marker 表，詳 data-model.md。
**Testing**: pytest 單元／契約／整合／競態，Node UI；真人兩教師、教師加兩學生組，1366×768／390×844 與鍵盤。
**Target Platform**: Windows 本機 `http://127.0.0.1:5000`，固定 callback；公開部署／HTTPS 改造不在本輪。
**Project Type**: 既有 Web app 增量，不另建 app factory、身分或匯入系統。
**Performance Goals**: 原一秒輪詢及人工 5 秒全文同步維持；外網不持 SQLite write lock；Google 互動不承諾秒數。
**Constraints**: 課堂不可刪、講義整份移除、immutable DTO不改、歷史回填可用；不把 broad token 交 Picker，不借 Desktop；真實窄 scope smoke 未執行。
**Scale/Scope**: 本機兩教師、多課程／講義／一次性課堂；單份單分頁。不加公告、評分、Drive上傳／檔案管理、刪課程、回收桶或003假排名。

## Constitution Check

| 原則 | 設計前 | Phase 1 後 |
| --- | --- | --- |
| I 雙組協調 | 使用者確認D21並允許plan，OpenSpec待同步。 | 原狀保留；介面／分工列待核對，計畫不代表對方採用。 |
| II 三圖優先 | 三圖已渲染，使用者回報核對完畢。 | 按三圖具體化 sidecar、flow、窄token與tombstone，CLI重渲染，技術修圖待核對。 |
| III 動態匯入回填 | 沿用001/006辨識及版本。 | 雙入口同服務，不刪來源或版本，歷史回填／恢復保持。 |
| IV 機敏與角色 | 原登入／Sheets token後端。 | Picker窄token是明列的用途擴充，同sub/scope/grant/course重檢；原後端秘密不外露。 |
| V 自動＋人工 | 舊人工任務保持。 | 受控／真Google／人工分欄，scope smoke與歷史保留納入必要驗證。 |
| VI 文件一致 | 本輪只設計。 | 四份契約／資料模型／quickstart與圖對照；後續tasks→analyze→implement→converge。 |

無需改憲章或技術例外。007「不向瀏覽器交OAuth token」於008新增嚴格限定的Picker窄access-token交付；不能原地放行 broad Sheets token。憲章IV的機敏載入、持久化與日誌規則保持；技術差異須同學核對。共同採用／合併前補D21及具名互審，不把未知寫已確認。

## Project Structure

```text
specs/008-teacher-course-workspace/
  spec.md / navigation.md / diagram-review.md / checklists/requirements.md
  plan.md / research.md / data-model.md / quickstart.md
  contracts/workspace.md / import-flow.md / picker-authorization.md / lecture-lifecycle.md
diagrams/008-{component,class,sequence}.{puml,png}
src/guided_notes/
  workspace/__init__.py / routes.py
  workspace/import_flows.py / repository.py / schema.sql
  templates/workspace/{base,welcome,courses,overview,lectures,classrooms,classroom,import}.html
  static/{workspace.css,workspace.js,import-flow.js,picker.js}
  google_login/{provider,service,routes,repository}.py
  google_login/{flow_context,picker_service}.py
  notes/lecture_lifecycle.py
  notes/{schema.sql,repository.py,course_catalogs.py,import_service.py,routes.py}
  activities/{teacher_routes,classroom_routes,classroom_catalog,classroom_access,course_service}.py
  __init__.py / db.py / config.py / http.py
tests/
  unit/{test_picker_authorization,test_import_flow,test_lecture_visibility}.py
  contract/{test_workspace_routes,test_import_flow_routes,test_lecture_removal}.py
  integration/{test_workspace_007_compatibility,test_import_flow_oauth}.py
  integration/{test_lecture_removal_races,test_workspace_history}.py
  workspace-navigation.test.cjs / import-menu.test.cjs / picker-flow.test.cjs
```

以上是待實作配置，不表示產品／測試檔已建立。workspace只組合原服務，不複製課程、身分、辨識或回填核心。

## Phase 0 — 決策摘要

詳 [research.md](research.md)：專用HTML namespace保留JSON；官方Picker＋drive.file＋專用client／非增量；online-only避免Picker refresh scope擴張；tombstone保存歷史；新引用交易重檢；附加schema保留007。

同project不同client不是grant隔離。Python Flow採false是根據官方GIS與OAuth參數的協定推論，尚待真Google smoke；實際scope不符即拒絕cloud交付，不fallback broad token或擅改全Drive scope。

## Phase 1 — 圖表落地

### A. 分層頁與既有路由

Component Home/Workspace→workspace.routes與Jinja base；Course/Rooms→原course_service/classroom APIs；權限→原require_teacher。

- `/teacher`：Google/classroom模式顯示welcome；`/teacher/workspace`卡片；`/teacher/workspace/courses/<cid>`總覽；其下`lectures`、`classrooms`；`classrooms/<rid>`指定課堂控制。
- 原JSON GET/POST `/teacher/courses`、`.../classrooms`、`.../activities`格式保持。workspace.js呼叫原mutation，成功以回傳識別組合固定本地路徑。清單server-render，JS錯誤／pending狀態可讀；若需抽取create-course/room驗證，落原service，不複製SQL或self-HTTP。
- 原 `/teacher/notes/courses/<cid>` HTML 303至新講義頁；全域notes HTML作導覽入口；JSON、preview/report/recovery URL保留。移除講義的一般saved URL回410，歷史另由activity reference驗權。
- 課堂JS固定data-course-id/room-id，不以舊localStorage默默選他課；學生`/student`、輪詢與proof不變。legacy CLASSROOM_MODE=false 保留原API與模板測試，不強迫遷移002 DB。

### B. 按需授權與匯入flow

1. GET清單／展開加號零授權。選cloud建flow；link先展開輸入，按讀取才建flow。固定teacher/browser/current-grant-hash/course/source_kind，期限30分鐘。
2. cloud若本人Picker cache有效直接交付ticket；否則建立原purpose=sheets OAuth attempt＋sidecar kind=picker/flow_id，專用client、PKCE/nonce、online、false。claim→外網→finalize再驗，303固定flow頁。
3. POST token交付重驗owner/current grant/flow/client/actual scope/generation/expiry，只有窄access token。Picker選檔POST file_id＋ticket；後端用窄cache讀Drive metadata驗Sheets MIME/未trashed，不信前端標題或MIME，再檢查本人Sheets授權。可讀不可寫可匯入，回填仍按原實際權限回報。
4. link解析原Sheets URL/gid，明確read才檢查原Sheets授權。兩條路缺Sheets授權時保存原意圖，原007 connect附sidecar kind=sheets；完成回同flow，不丟到全域notes或要求重填。
5. callback不直接匯入。303後flow頁以CSRF續接POST執行先前明確請求，無JS顯示繼續讀取按鈕；GET/refresh不自動起新OAuth。read claim/CAS防雙送；來源讀取claim最長120秒，逾時晚回不提交，後續明確重試。
6. worksheets後單選、命名、create_preview；建立preview→flow關係。confirm仍採原服務，flow由DB取得，不接受body改course/name；來源變動的新preview續接同flow、再確認。
7. 外網完成後、preview/publish最終write transaction內再次驗原grant、教師與課程。原notes服務需可信內部flow guard，不能只在route前驗一次；flow完成與catalog出版同交易，回原課程清單。

多分頁各有flow；Google互動沿原browser last-start-wins。被supersede的授權明確重試，其他flow不改course/source。登出／切換／原grant過期使原flow失效，不轉移到新grant；重新登入後重發匯入。

取消／過期／失效同交易invalidate綁定的ready notes previews，避免舊confirm URL繞flow；terminal flow至少保留24小時後才有界清理。007原attempt隔日清理須透過sidecar ON DELETE CASCADE、flow.oauth_attempt_id ON DELETE SET NULL相容；NULL不是可自動續接的新流程。selection外網後除flow/grant/claim，亦重查ticket綁定cache generation/revision，拒絕reconnect後的晚回結果。

### B1. I1／U1：逾時重試及明確修改選擇（2026-11-25 使用者同意）

- 未到120秒claim期限回FLOW_BUSY；failed或reading且now >= claim_until時，明確retry可在原flow/grant/course仍有效下，以保存的動作與輸入快照原子取得新claim/revision。兩個重試只准一個接手；舊claim晚回不提交，GET不自行重試，1800秒flow期限優先。selection仍驗ticket/cache，失效則引導必要授權／重新選檔。
- flow新增choice_revision、request_state_json及retry_action；同動作、同選擇版次且canonical白名單輸入相同才算重送。preview比較分頁／命名，confirm亦比較existing_import_id；不同輸入FLOW_STEP_CONFLICT，不靜默回舊預覽。
- 預覽提供「重新選擇／修改名稱」，POST revise(expected_revision)；已有分頁候選且無有效claim的未完成流程，同交易invalidate舊ready previews、清引用／preview快照、遞增choice_revision/revision後回分頁／名稱步驟。previews必帶目前choice_revision，舊版請求及原notes舊確認URL拒絕。completed不可修改；換來源另建flow。原命名回填表單，不自動建新預覽。
- T022–T025補時間邊界、雙重試、輸入比對與修改競態測試；T028/T033/T041–T044落實模型、端點、UI與原notes guard。quickstart分開記受控故障與真人操作，尚未執行。

### C. Picker與007接線

`flow_context`只從DB決定credential_kind；專用Picker client與main不同、同project、同固定callback。provider/validate_current選可信client；finish派發picker_service或原sheets_service.connect。普通007無sidecar attempt僅接受main client；flow有oauth_attempt_id卻缺sidecar、Picker client無context或參照不一致，一律拒絕。

Picker cache purpose=picker，獨立Fernet BLOB、actual scope、expiry、owner/client/instance/generation/revision，不存refresh。有效cache可由本人新grant重用，但交付每次驗目前grant；300秒ticket綁原flow與credential generation。007 Sheets credential/status/refresh不替換；原base模板常駐連接表單移入匯入任務，舊connect API保留但沒有任意next。

Google token真實期限不能被本機ticket TTL假裝縮短，不revoke同project grant。007原cookie、epoch/current pointer、claim、timeout／顯式refresh／不可刷新Sheets快照均須回歸。

原http.privacy全站no-referrer可能令受來源限制的Picker key無Referer；僅固定workspace.import_page的乾淨HTML採strict-origin-when-cross-origin，跨站只帶origin。OAuth callback、token POST及其餘敏感頁仍no-referrer/no-store；以endpoint allowlist控制，加入原http.py的最小接線及header／真Picker測試，不能全站放寬或移除key限制。

### D. 講義移除與歷史

Class Lecture可見性→notes_lecture_removals；Version/Activity/Record原表保持。owned_import/catalog_row只驗owner，不全域過濾active。一般清單、更新指定import、assign、一般版本頁及新引用provider顯式require_active。

remove與新activity／catalog出版共用BEGIN IMMEDIATE。網路、Catalog/Display可在交易外，但store_activity/save_catalog前必須以同db重檢。防禦trigger只依tombstone拒新activities／catalog INSERT，映射LECTURE_REMOVED，不取代服務權限。測試provider需seed真正notes對應或明確測試adapter，不加正式bypass。

所有一般入口、同來源更新選單及confirm_preview已confirmed冪等結果都排除removed。重匯同來源選新增→新UUID/version1，不復活舊ID。歷史以activity reference／operation/report驗權，原source lease、固定勝組、回讀及恢復不受一般可見性影響。課程／課堂無DELETE或其他刪除動作。

防禦trigger統一固定訊號lecture_removed，classroom_access.activity_transaction及legacy teacher-create／notes publication的相應邊界將它映射410 LECTURE_REMOVED；不能讓SQLite IntegrityError直接變500。一般情況仍先由同交易服務guard回清楚錯誤。

### E. 007資料相容

附加schema不ALTER原INSERT VALUES表、不改purpose CHECK、不重建catalog／auth_instance。absence=active無全量rewrite；保留credential BLOB/key。008 schema與version marker同交易，失敗rollback／停止啟動，不catch後清空DB。原core/notes初始化分段，不假稱整個歷代步驟全原子；每段冪等保留既有資料。

用臨時populated007 fixture驗表資料與密文byte-for-byte、兩次啟動與init-db、故障注入rollback、FK/trigger。實作前操作者備份DB／key，plan不接觸；不建立空白DB掩蓋問題。

notes移除表與純visibility triggers由notes.schema在各模式初始化，不依賴Google表；workspace的flow／Picker／sidecar表只在Google＋classroom模式於原Google與notes初始化後建立。兩附加步驟各自短交易、各自冪等；workspace_schema_versions僅標記workspace步驟，不表示先前歷代初始化跨段全原子。legacy test_password fixtures仍建立notes移除表，不能用「未啟用UI」略過新引用可見性檢查。

## 驗證策略

1. 配置／schema兼容→HTML與舊API→flow/sidecar→Picker／Sheets續接→移除／歷史競態；各段定義失敗預期後實作。
2. OAuth測真state/nonce/PKCE/client dispatch/grants，受控scope涵蓋額外broad、missing、aliases、錯帳號／client、過期重放晚回、callback乾淨URL。
3. Node驗選單、cancel、popupblocked、焦點與Escape；真正Picker／popup／鍵盤與窄螢幕由人工驗，DOM不代替真人。
4. 移除所有一般清單／舊網址／歷史入口、同來源新UUID、已confirmed preview重送、remove↔create/version雙向屏障、未知回填恢復。
5. 全套原pytest/Node；TeacherContext/Catalog/Display/Result不加Google或removed欄位。003未接入仍明報QUIZ_UNAVAILABLE／未結算。
6. 真Google先驗已有main broad grant時仍回窄Picker scope；再用副本驗兩入口、教師隔離及教師＋兩組學生，真實寫回依001另外記錄。

## 進入tasks前待辦

- 同學核對本次四契約與技術修圖：HTML/JSON、兩client/sidecar、窄token邊界、flow final guard、tombstone/歷史；姓名／結論待補。
- D21 OpenSpec新增行為確認與本輪001/002/003分工未回報，保持待同步；使用者plan授權不代填。
- 後續依quickstart準備Picker client/API key/project number、Drive/Picker服務、origin與scopes；本輪未操作Console。真窄scope smoke為交付gate，不要求現在提供憑證。
- tasks需包含上述安全／兼容／競態／真人，之後analyze；本輪不建立tasks或提前實作。

## 2026-11-26 實作對照

workspace.routes/HTML、import_flows/repository/schema、google_login.flow_context/picker_service及notes.lecture_lifecycle已依本計畫接線；主要組件與三圖責任不變。教師組別另以新workspace限定GET讀原classroom_groups，原JSON不擴欄，契約補於workspace.md。

重送快照只保存輸入與結果識別，題目DTO／分頁清單不重複塞入有界request_state_json。原007測試的合成provider補真實notes來源／版本關聯，沒有正式bypass。實作／測試日期跨2026-11-25至26，真Google、人工與具名互審仍待完成，詳validation.md。
