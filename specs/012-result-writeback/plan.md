# Implementation Plan: 活動結果回填與原課堂組名

**Branch**: `codex/012-result-writeback` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)
**Input**: Issue #19；使用者回報三圖已審查並呼叫 speckit-plan。
**Status**: Phase 0／1 設計完成，三故事實作已接線；實際驗證與未完成項目見 validation.md、tasks.md。

## Summary

教師從目前／歷史結果的「預覽回填講義」直接提交所選活動，沿用既有回填 POST 建立預覽，再以 303 導向保存頁。預覽與報告增加由原活動取得的課程、課堂、活動及時間，勝組以原課堂及組別 ID 查詢後交由 #16 共用格式呈現。沿用 001 的不可變快照、覆寫同意、來源租約、冪等及回讀恢復，不改結算、答案對應或來源格位。

三圖為設計藍圖：[Component](../../diagrams/012-component.png) 對應入口／context／既有回填責任；[Class](../../diagrams/012-class.png) 對應 [資料模型](data-model.md) 的只讀投影；[Sequence](../../diagrams/012-sequence.png) 對應 [HTTP 契約](contracts/http.md) 的驗權、狀態、來源、確認及恢復順序。

## Technical Context

**Language/Version**: Python >=3.13,<3.14；原生 JavaScript。
**Primary Dependencies**: 既有 Flask 3.x、Jinja 3.x、官方 Google API／Auth 用戶端；不新增套件。
**Storage**: 原 SQLite。由既有課堂／活動／組別／講義版本與回填表組合投影；本功能無 schema migration。
**Testing**: pytest、標準庫 unittest；Node `--test` 現有 `.test.cjs`；受控 Sheets gateway；真人測試副本另驗。
**Target Platform**: 現有 Flask Web 服務與桌面／行動瀏覽器；Windows 開發環境。
**Project Type**: 單一 Web 專案，保留現有 activities／quiz／notes 邊界。
**Performance Goals**: 進入指定預覽流程一次操作、零手輸 ID；GET 已保存預覽／報告不新增 Sheets 讀寫。context／勝組使用一次活動查詢及一次批次組別查詢，避免逐格查詢。
**Constraints**: 每個入口驗教師與原堂歸屬；網路呼叫不置於 DB 寫交易；不更改結果版本、來源動態辨識、既有授權或歷史；不以組名／加入碼對應；不重送已完成題。
**Scale/Scope**: 兩個教師結果入口、notes 預覽／清單／報告與錯誤返回、共用 context service。學生輸入與 #20 時間核心由相依功能負責。

## Constitution Check

| 原則 | Phase 0 前 | Phase 1 後 |
| --- | --- | --- |
| I 需求追溯 | 依 Issue #19 及使用者 #16 契約；規劃初期 #19 確認待補 | 2026-11-27 使用者回報 C1-A–C 已雙組確認，行為確認門檻通過；姓名／外部紀錄未提供，技術整合與人工證據分開保留 |
| II 圖先行 | 三圖 CLI 成功；使用者本聊天室回報「已審查」 | 規劃沿用原三圖；概念到檔案對應已列明 |
| III 動態回填 | 沿用 match_source／prepare_writes | 不接受前端勝組或座標；真副本驗收列入指南 |
| IV 權限與機敏 | 讀取現有程式，無讀憑證 | 新 context 與舊預覽／報告重驗原堂；學生不新增教師資料 |
| V 自動與人工 | 設計階段不聲稱產品通過 | 自動矩陣與教師加兩組／真來源驗收分開記錄 |
| VI 產物一致 | 已有 spec／三圖 | plan／research／model／contracts／quickstart 完成；tasks／analyze／converge 留後續 |

研究與設計無新增架構違例。C1-A–C 共同行為已依使用者回報確認，實作前確認門檻通過；不得僅將未來行為變更的確認延至合併或驗收前。產品實作接線仍須取得 #16 實際介面與 #20 共用時間模組並完成對照；政策確認不代表程式已合流、模組作者技術互審或人工驗收已完成。

## Project Structure

### Documentation (this feature)

```text
specs/012-result-writeback/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── diagram-review.md
├── checklists/requirements.md
└── contracts/
    ├── http.md
    ├── display-context.md
    └── dependency-boundaries.md
```

後續已由 speckit-tasks 產生 [tasks.md](tasks.md)，任務全部尚未執行。

### Source Code (repository root)

```text
src/guided_notes/
├── activities/{classroom_access.py,teacher.py,classroom_schema.sql} # 沿用查權／資料
├── quiz/{results_gateway.py,settlement.py} # 沿用正式快照
├── notes/
│   ├── export_context.py # 擬新增：原活動與原堂勝組投影／驗證
│   ├── export_service.py # 建立預覽前校驗 context／勝組
│   ├── writeback.py # confirm／恢復在新增寫入前校驗
│   ├── routes.py # 接線及教師 JSON 投影，保留現有端點
│   ├── static/notes.js # 移除一般回填的最近活動自動填入依賴
│   └── templates/notes/{export_context,export_form,export_preview,report,error}.html
├── static/classroom.js # 目前／歷史結果 POST 表單及返回 query 初始化
├── workspace/routes.py # 返回原結果的只讀選取參數驗權
└── templates/{workspace,activities}/ # 必要 CSRF／入口呈現
tests/
├── unit/ # context／無勝組／格式投影
├── integration/ # 原堂／版本／權限／授權／恢復
├── contract/ # 教師 DTO、原交換契約不變
└── *.test.cjs # 選活動與晚到回應不更換入口
```

**Structure Decision**: 僅新增一個 notes context 模組，集中原活動與原堂資料查詢；不新增框架、影子課堂表或複製結算資料。時間核心與組號核心使用相依模組，具體名稱以合流版本為準。

## Implementation Approach

1. **相依對照**：取得 #16 formatter／資料表示，與 #20 確定時間呈現入口。記錄提交及檔案責任；函數名稱不同僅調整薄接線，不建立第二套規則。
2. **Context 與驗證**：`export_context` 以 `requested_activity`／`owned_classroom` 驗權，再按原 activity_id JOIN 課程／課堂與活動事件；以原 classroom_id＋所有非空 winner_group_id 一次查組別。先校驗才可讀來源或新增寫入。
3. **直接入口**：`classroom.js` 目前／歷史結果以已選活動 ID 建原生 POST 表單至既有 preview endpoint，附 CSRF。按鈕隨結果區重建並受既有選取序號保護，絕不讀 localStorage 最近活動。失敗使用活動專屬 GET 返回頁明確重試。
   預覽／報告返回以原 workspace.classroom URL 帶單一 activity_id；workspace 路由驗原堂與活動，將已驗權選取交給 classroom.js 初始化。刷新及關課歷史仍選原活動；無效／跨堂明確拒絕，不退回最新活動。這是結果頁選取，不是新增 Sheets OAuth 返回目的地。
4. **教師投影**：預覽／報告加入 context 和 `winner_group_label`；一般表格只呈現標籤，ID 留 `<details>` 診斷區。v1 快照不加顯示欄位，避免 digest 改變。
5. **失敗與歷史**：未結束／未結算沿用現有錯誤；全部無勝組保留 skip 預覽的既有低階契約，顯示「沒有勝組可回填」，教師 UI 不提供無效寫入。原堂勝組缺失用既有 `RESULT_INVALID`（422）加安全 reason；報告保留原狀態及錯誤，禁用新增寫入。關課／清單移除不使用「開放中」／「未移除」過濾。
6. **確認與恢復**：沿用 preview 消耗、source mutex／lease、冪等、結果重驗、覆寫及回讀。在新操作開始前與每批原結果校驗位置加原堂勝組驗證；冪等重送原報告仍可讀。恢復按既有 origin／root 操作鏈處理。

## Validation Strategy

FR-001–003：兩場同名／同講義不同版本結果入口、刷新、返回及授權取消／成功；FR-004–006：兩堂相同組號、缺失／跨堂組別、HTML／JSON 一致；FR-007–008：三狀態、關課歷史、清單移除與越權；FR-009–013：既有覆寫、來源變動、部分／未知、restart、冪等、兩配置 Sheets 副本與非目標資料保留。見 [quickstart](quickstart.md)。本輪僅檢查規劃產物，未執行產品測試。

## Complexity Tracking

無需例外。待確認的協作證據與人工驗收保持未完成，不以本計畫取代。
