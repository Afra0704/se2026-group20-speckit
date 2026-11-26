# Implementation Plan: 建立活動後顯示學生預覽

**Branch**: `codex/005-preview-before-start`（起點 `812037a`）
**Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)
**Input**: 005 規格；D18 與三圖由使用者回報確認完成，姓名及獨立紀錄待補。

## Summary

補齊已同意的規則：建立活動時，在單一寫交易檢查同堂沒有 PREPARING/LIVE，保存固定題目並更新目前活動與課堂版本。學生沿用輪詢顯示準備預覽，只有 LIVE 才啟用輸入與提交。教師可以結束準備中或搶答中活動後建立下一場。使用者已明確允許丟棄舊開發資料，採空白開發 DB 驗收，不實作舊多準備活動的相容或遷移。

依 [組件](../../diagrams/005-component.puml)、[類別](../../diagrams/005-class.puml)、[時序](../../diagrams/005-sequence.puml) 三圖設計：課堂管理發布預覽，學生顯示負責停用狀態，提交檢查仍由後端獨立執行。圖中「結束活動」包含準備中結束。

## Technical Context

**Language/Version**: Python 3.13、原生 JavaScript。
**Primary Dependencies**: 沿用 pyproject/uv.lock 中 Flask、Jinja；不新增套件或 Google scope。
**Storage**: 現有 SQLite classroom DB；`write_transaction()` 使用 BEGIN IMMEDIATE 與明確 SQL COMMIT/ROLLBACK。
**Testing**: pytest 路由／整合測試、Node VM 前端測試、教師及兩組學生人工驗收。
**Target Platform**: Windows 本機 Flask，Chrome／Edge 獨立工作階段。
**Project Type**: 現有 Web app 的增量。
**Performance Goals**: 穩定本機連線下，建立與開始後 5 秒內兩組同步，沿用一秒輪詢。
**Constraints**: 課堂模式限定，保留 legacy 模式與正式 003 限制；舊開發測試資料可丟棄，新流程正常結束仍保留歷史；不得洩漏他組資料或跨活動誤送。
**Scale/Scope**: 教師加至少兩組學生；不擴充完整題目敘述、Google 登入、正式排名或結算。

## Constitution Check

| 原則 | 設計前／設計後核對 |
| --- | --- |
| I 雙組協調 | D18 與 Q1 於 2026-11-25 由使用者回報確認；不改其他待確認項，姓名待補。 |
| II 圖表優先 | 三類 PUML/PNG 已產生、CLI 成功；使用者回報圖意審查完成。實作後仍須核對程式與圖。 |
| III 動態匯入 | 沿用 catalog 固定題目、識別、順序與題組提交單位，不硬編碼。 |
| IV 權限 | 後端重檢教師、課程／課堂歸屬、CSRF、階段；學生只有安全清單及名稱。 |
| V AI／人工 | 計畫包含競態、越權、重連及三人驗收；尚未執行新測試。 |
| VI 一致性 | 本次有獨立 spec/plan，後續 tasks→analyze→implement→converge、PR 互審。 |

設計前後無須豁免的衝突。使用者回報確認不等於程式驗收；功能尚未完成。

## Project Structure

### Documentation (this feature)

```text
specs/005-preview-before-start/
  spec.md, plan.md, research.md, data-model.md, quickstart.md
  contracts/classroom-preview.md
  diagram-review.md, checklists/requirements.md
  tasks.md  # 後續 speckit-tasks 產生
diagrams/005-{component,class,sequence}.{puml,png}
```

### Source Code (repository root)

```text
src/guided_notes/activities/
  classroom_routes.py, classroom_access.py, classroom_schema.sql
  state_routes.py, teacher.py
src/guided_notes/static/classroom.js
src/guided_notes/templates/activities/classroom.html
tests/contract/test_classroom_management.py
tests/integration/test_classroom_switch.py
tests/integration/test_classroom_close.py
tests/integration/test_classroom_preview.py  # 待新增
tests/classroom-preview.test.cjs             # 待新增
```

**Structure Decision**: 擴充既有課堂模組，不重建 app factory、登入或共用資料庫。

## 模組與資料流

1. `classroom_routes.py` 建立時先取得固定 catalog；取得寫鎖後重檢教師、OPEN 及所有關聯未結束活動，原子完成活動、題目、關聯、current_activity_id 及 state_version。catalog 查詢在持鎖前，避免外部延遲佔用交易。
2. state 以同一讀取快照返回目前 PREPARING/LIVE/CLOSED 與安全 `activity.title`，沿用 state_view 的 questions；不改 CatalogDTO、不帶來源座標或 blank_id。
3. `classroom.js` 建立成功後立即 refresh；學生按 activity id 重建題目，按階段更新 input/button，即使同 id 也須處理 PREPARING→LIVE。新增等待提示及活動名稱，採 textContent。
4. `classroom.html` 與 JS 在有未結束活動時停用建立，提供準備中結束按鈕；表單 finally 不得無條件解除業務停用。斷線停用寫操作，復線取得最新 state/history，沿用 selection/request/version 防亂序。
5. 提交仍由既有 submission_context 檢查課堂 OPEN、目前活動及 LIVE。正式 003 不可用時保留原錯誤，不注入假順位或假結算。

## 競態與開發資料範圍

- 同堂任何 PREPARING/LIVE 均阻止建立；BEGIN IMMEDIATE 串行化兩個獨立連線，後進者重檢並回 409 ACTIVITY_IN_PROGRESS。DB 忙碌沿用現有重試與 503 約定。
- schema 加入關聯 INSERT 及活動 phase UPDATE 的防護 trigger，限制第二個未結束活動及 CLOSED 重開，僅作用於課堂關聯；trigger 衝突轉 409，不能成為 500。不能用跨表 partial index 取代。
- finish 擴充目前 PREPARING→CLOSED，保留題目、版本與 closed_at，started_at 維持空值；LIVE 同樣只允許結束目前活動。沒有開始過的活動不產生答案／順位；結果是否可用由既有結算 provider 決定。
- 驗收前切換到專用空白開發 DB，先設定明確的 GUIDED_NOTES_DATABASE；原測試 DB 可依使用者授權刪除，但不是啟動／GET／init-db 自動刪除。實際刪除須先列出及核對精確路徑，不以萬用字元刪除 instance，不涉及憑證、程式檔或雲端 Sheets。
- 不提供舊多 PREPARING 的清理 UI、非目前活動 finish 特例或無指標恢復流程。新資料 current_activity_id 必須與唯一未結束活動一致，指標或歸屬不符時拒絕操作；歷史 CLOSED 不重開。
- 關課在一筆交易關閉關聯 PREPARING/LIVE，正常流程最多一個，保留本版歷史並停止加入／提交。
- 每次可見狀態異動增加 state_version；活動轉換增加 phase_version。重跑初始化保留新流程已建立的資料，不能將開發重置變成每次啟動清空。

## 驗證與交接

FR-001/002/005 對應單題／題組、兩組同步與刷新；FR-003/004/006 對應提前提交、準備中結束及關課；FR-007 對應授權與安全欄位；FR-008/009 對應雙連線建立、回滾、指標一致性及晚到狀態。

既有 test_classroom_management、test_classroom_switch 預期可預建兩場，須修正為已確認的單活動規則。新增測試採臨時空白 DB、固定 provider，不寫真實 Sheets。與 002/004 同學對齊 activity.title、409 提示、目前 PREPARING 結束及開發 DB 重置範圍；正式 003 另行接線。

## Complexity Tracking

沒有新增服務或憲章豁免；trigger 為既有跨表規則補強，不重構資料架構。
