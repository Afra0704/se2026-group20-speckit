# Implementation Plan: 一次性課堂碼釋放與重用

**Branch**: `codex/009-release-classroom-codes` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: 最新 D22；使用者明確授權 `$speckit-plan`，本輪僅 Phase 0／1，不產生 tasks、不實作。

**最新階段（2026-11-26）**：上述Input為計畫生成時的授權紀錄；使用者後續已依序授權tasks、analyze及implement。009本機程式與受控自動驗證已執行，證據見[validation.md](validation.md)；正式003合流及人工驗收未完成，原設計條目不構成功能完成宣告。

**003整合延續**：使用者後續指定先完成003＋009、自行負責真人／真Sheets；已導入PR9最終074b4a9及master7ae7054，正式自動接口驗證以validation最新章節為準。允許本機分段commit，仍禁止push／合併009 PR或操作操作者DB／Google授權。下文待正式接線屬先前時點，舊模式移除另立迭代。

## Summary

保留 `classrooms.code` 歷史值，以 `state='OPEN'` 的部分唯一索引表示有效碼對應，取代永久 UNIQUE。關課及未結束活動在同一交易結束，立即釋放有效占用，不刪課堂、不維護外部碼池。學生加入與恢復固定原 classroom_id／group_id，關課後只可見結束提示，教師歷史、003 結算及 001 回填依賴保持。

學生採獨立 `/student` 加入頁，成功後導航至固定課堂 URL；課堂結束後清除題目／結果，停留結束頁，按「加入其他課堂」才返回。仍使用碼＋組別，不新增 Google 學生登入。

依A1修訂，每次內容read transaction開始即驗權威原堂狀態，關課commit後新開始的內容讀取一律拒絕；關課前已合法驗OPEN的快照可能晚到，前端確認CLOSED後不得套用。依I1修訂，SC-005的真人加入新堂流程與受控fixture同碼隔離分列驗證，不要求正式人工環境抽到相同碼。

主要藍圖：[Component](../../diagrams/009-component.puml)、[Class](../../diagrams/009-class.puml)、[Sequence](../../diagrams/009-sequence.puml)。本次同步加入資料約束及介面技術註記，使用者規則不變。

## Technical Context

**Language/Version**: Python >=3.13,<3.14，原生 JavaScript、Jinja HTML/CSS，沿用 pyproject／uv.lock。

**Primary Dependencies**: 現有 Flask 3.1 相容範圍、sqlite3、pytest、Node 內建 test runner；Google libraries／cryptography 保持，無新增套件。

**Storage**: 沿用 007／008 SQLite；需非破壞表重建移除表內 UNIQUE。保留 ID、FK、時間、auth_instance UUID、Google 密文、固定版本與回填資料；本輪不開啟操作者 DB。

**Testing**: pytest 臨時 DB、多連線屏障競態、schema 故障注入、Node DOM 模擬及教師加兩組學生人工驗收。正式 003、替代 provider 及人工證據分列。

**Target Platform**: Windows 本機 Flask 與桌面／窄螢幕瀏覽器；同源 cookie／CSRF／no-store。

**Project Type**: 現有 Flask 單體 web application，不新增服務或前端框架。

**Performance Goals**: 沿用約 1 秒輪詢；正常本機關課同步以既有 5 秒人工情境為設計目標，實作後量測。有效碼堂數永遠最多 1、跨堂內容洩漏數為 0。

**Constraints**: 五碼格式、無冷卻、全域系統分配、不人工指定；沿用 12 次候選嘗試後 503 CLASSROOM_CODE_UNAVAILABLE，不宣稱掃遍碼域。禁止清 DB、換 key、操作 OAuth、覆寫同學 003 或 commit／push。

**Scale/Scope**: 碼域 26²×10³＝676,000 種，是碼域數量而非負載保證。涵蓋課堂生命週期、schema 相容升級、學生入口／恢復／結果權限；不重寫順位或結算。

## Constitution Check

*Pre-research 與 post-design 均依此表核對。*

| 原則／Gate | 前置狀態與授權界線 | 設計後核對 |
| --- | --- | --- |
| I 雙組追溯 | 使用者於2026-11-26回報C1已確認，D16→D22雙組行為確認據此記錄。 | 確認者姓名／獨立連結未提供，保留來源註記；不再將已回報的行為同步列未確認。 |
| II 圖表先行 | 三圖CLI PNG已成功；使用者於2026-11-26回報C2新版圖意已確認。 | 依使用者回報解除C2，不以AI檢視代稱組員確認；003具體介面／分工另依T003核對。 |
| III 動態回填 | 不改辨識、固定版本／勝組及格位規則。 | 教師歷史及未知回填先回讀保持。 |
| IV 權限與機敏 | 後端學生入口需驗原堂及 OPEN。 | closed 最小狀態不含題目／組別／結果，無權者不洩漏狀態；cookie／CSRF／no-store 保持。 |
| V 人工與自動證據 | 本輪無產品測試，不能套舊測試當通過。 | quickstart 定義 R1～R8、故障、權限及兩組人工情境。 |
| VI 文件一致 | Plan階段尚未產tasks；後續使用者已授權生成[tasks.md](tasks.md)，不得跳實作。 | 追溯表連結要求、圖、契約及驗收，保留 analyze／converge／實作後對圖。 |

文件的C1／C2確認門檻已依使用者最新回報記錄；具名來源待補、不影響已回報事實。003具體介面／分工及產品自動／人工驗收仍是未完成任務，不能因規格分析通過而視為實作／合併完成。

## Project Structure

### Documentation (this feature)

```text
specs/009-release-classroom-codes/
├── spec.md
├── plan.md
├── tasks.md
├── research.md
├── data-model.md
├── quickstart.md
├── diagram-review.md
├── checklists/requirements.md
└── contracts/
    ├── classroom-lifecycle.md
    ├── student-entry.md
    └── quiz-history.md
```

### Source Code (repository root)

後續預計影響範圍，非本輪已修改：

```text
src/guided_notes/
├── db.py                            # schema 版本與原子初始化
├── activities/
│   ├── classroom_schema.sql         # 部分唯一、課堂永久關閉
│   ├── classroom_migration.py       # 擬新增，安全升級 helper
│   ├── classroom_routes.py          # 建堂、關課、加入、狀態、恢復
│   └── classroom_membership.py      # 固定身份與 OPEN 內容授權分開
├── __init__.py                      # 獨立學生頁／固定課堂頁
├── templates/activities/            # 擬新增 student_join／student_room
├── static/                          # 獨立學生加入／課堂狀態控制
└── quiz/                            # 只列交接，同學核對後安排變更
 tests/contract/                     # HTTP／結果權限
 tests/integration/                  # schema／競態／歷史
 tests/*.test.cjs                    # 導頁、晚回、斷線、返回及多分頁
```

**Structure Decision**: 沿用 activities／quiz／notes 邊界，有效碼為 OPEN 課堂投影，不新增碼池資料表。學生頁可共用樣式但不干擾 008 教師初始化與 OAuth。db／003 共用改動須由負責成員核對。

## Phase 0 — Research

[research.md](research.md) 已解決有效碼索引、保留資料升級、確認順序、學生授權分層、頁面狀態與 003／001 邊界；依 repo 唯讀研究與 SQLite 官方文件形成決策，沒有執行 DB 變更。

## Phase 1 — Design & Contracts

- [data-model.md](data-model.md)：實體、欄位、狀態、FK 及 schema 升級驗證。
- [classroom-lifecycle.md](contracts/classroom-lifecycle.md)：碼、關課重送、唯一性與競態。
- [student-entry.md](contracts/student-entry.md)：獨立頁、恢復／狀態、cookie 與舊頁隔離。
- [quiz-history.md](contracts/quiz-history.md)：003 受理／結果與 001 教師歷史，列交接待確認。
- [quickstart.md](quickstart.md)：實作後驗證步驟、命令與證據矩陣，不包含實作程式。

## Requirement / Diagram Traceability

| 要求 | 圖表 → 設計落點 | 驗收 |
| --- | --- | --- |
| FR-001～006、013～015 | Code／Close、Room／Code、Sequence 關課分配 → data-model＋lifecycle | V01～V04、V08 |
| FR-007～009、012 | Join、Membership／Grant、恢復分流 → student-entry＋quiz-history | V03～V06 |
| FR-010～011 | Activity／Result／Export、教師歷史 → quiz-history | V07 |
| FR-016～018、017a | 獨立頁、Sequence 結束頁 → student-entry 狀態機 | V05、V06、V09 |
| SC-001～006 | 全部契約共同成立 | quickstart 受控／正式／人工分列 |

## Complexity Tracking

| 有限例外／成本 | 原因 | 較簡方案未採原因 |
| --- | --- | --- |
| 前階段原則I／II確認缺口（已補使用者回報） | 使用者現明確回報C1／C2皆已確認，歷史缺口保留在analysis.md，不再作未確認例外。 | 不虛構具名證據，也不要求重複確認同一行為。 |
| classrooms 非破壞重建 | 表內 UNIQUE 無法靠另加索引取消。 | 清 DB 違反要求，改寫歷史碼或雙份碼池增加相容風險。 |

## Completion / Limits

Phase 0／1 設計已產出，尚未 tasks、實作、產品驗收或正式 003 接線。setup-plan 回傳 BRANCH `009-release-classroom-codes` 為工具解析值；實際 Git 分支為 `codex/009-release-classroom-codes`。本機 feature 指向 009，008 原待辦及 PR #7 Draft 保持。

後續2026-11-26：使用者呼叫speckit-tasks，已新增57項任務與依賴／驗收追溯，取代上述「尚未tasks」的階段狀態。沒有執行任務、analyze或實作；任務T001～T004記錄前置核對與分析gate，原待確認證據不代勾。

### 實作對照與部署界線（2026-11-26）

`classroom_schema.sql`實現OPEN部分唯一索引與不可逆／固定歸屬trigger；`classroom_migration.py`識別已知schema、逐欄重建、恢復依賴並比對歷史指紋；`db.py`以私有bootstrap連線管理FK暫停／恢復及Google原子初始化。一般request維持FK ON。FK恢復若在commit後失敗，啟動仍必須失敗並關閉私有連線；下次啟動驗已提交版本，不能宣稱已commit資料也rollback。

`classroom_membership.py`拆identity_for／OPEN group_for；課堂state、room results及activity results各自在同一讀交易驗權及組DTO。`student-entry.js`與`student-room.js`落實獨立加入、固定堂／原組、generation及CLOSED終態；舊混合頁不再由學生入口使用，002路由保持。

PR9 head31b0e23的正式003程式已隔離檢查，並未導入本分支。正式合流需將try_pending的寫交易放在最終授權read transaction之前，重新驗權後組DTO；保留其Idempotency-Key及QuizSubmission客戶端，不把它包在read_view內。詳見[pr9-review.md](pr9-review.md)。此處所稱D22為009-D22，與PR9的003-D22需整合時統一編號。

部署前停止全部舊服務並備份原DB與私有key；升級失敗停止，不切換空DB掩蓋失敗。歷史重碼後不能直接恢復舊永久UNIQUE。PR7已由外部合併為master39d6275，本輪沒有操作PR狀態；目前工作樹HEAD仍2d4f421，與該base的程式樹相同。未commit／push／合併PR或操作真DB／OAuth。
