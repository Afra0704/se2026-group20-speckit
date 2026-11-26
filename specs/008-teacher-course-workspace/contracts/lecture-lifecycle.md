# 008 講義移除／歷史契約（計畫）

## 移除接口

`POST /teacher/notes/courses/<course_id>/lectures/<import_id>/remove`

- 有效教師＋CSRF，server驗course、import及owner；JSON僅`{"confirm":true}`，HTML僅confirm=true與csrf_token，不能指定owner/version/雲端delete等額外欄位。
- HTML先顯示二次確認名稱、整份所有版本、歷史保留及雲端不刪；確認才POST，取消無mutation。
- 一個BEGIN IMMEDIATE內再驗owner/course，INSERT tombstone ON CONFLICT DO NOTHING；200 `{"import_id":"...","removed":true}`，HTML303原課程講義頁。
- 本人重送同結果，removed_at不變；越權／不存在404，未確認400，CSRF403；沒有課堂／課程刪除接口。

## 一般可用與歷史存取分離

| 入口 | removed行為 |
| --- | --- |
| 全域／課程講義清單、活動版本選單 | 排除整份所有版本。 |
| 未分配舊講義與同來源新增版本候選 | 排除；assign_lecture亦拒絕直接重配。 |
| 一般catalog／Display provider、新活動POST、一般版本HTML/JSON | owner已驗後410 LECTURE_REMOVED；非owner仍404。 |
| confirm_preview指定existing_import_id／已confirmed重送 | 拒絕移除結果，不新版本、不導回可用頁、不靜默復活。 |
| 明確新增同來源 | 新import UUID/version1，可共享source_id；不重用移除講義。 |
| activity的固定questions/activity_displays、結果與學生歷史 | 保持原權限與階段規則，不因removed消失。 |
| `/teacher/workspace/activities/<activity_id>/lecture` | 驗activity/room/teacher，再讀原固定版本並標歷史；不能建立新活動或靠query include_removed繞過。 |
| 原export preview／operation／readback／recovery | 由原activity/reference及owner驗權，沿用原catalog、winner、source lease；不加active filter。 |

低階repo.owned_import/catalog_row維持owner語意，不能全域加NOT removed。新增明確 `require_active_import(db,teacher_id,import_id,expected_course_id)`；002新引用透過001 `require_available_for_activity(teacher,course_id,import_id,version,db)` 在最終交易呼叫，TeacherContext及原DTO不改。

一般路由不得接受`include_removed=true`作權限開關；歷史對應必從已授權activity或operation推得。講義移除不呼叫Google delete/trash/update，不回收原credentials，不刪notes_sources/bindings/catalogs或課堂。

## 競態與冪等

- remove與create_activity同BEGIN IMMEDIATE序列；create交易內store_activity/save_display之前重查active與course，不能只信交易前取得的Catalog/Display/title。
- create先commit→活動固定版本仍可用、remove可成功；remove先commit→create410，沒有半activity或classroom.current指向空內容。
- confirm_preview網路前與出版最終transaction內都驗指定existing_import未移除；remove先完成則拒新version；version先完成則後續整份移除包含該version。
- confirmed preview的早回分支也要驗active；移除後重送不新增、不修改舊confirmed結果，可提示新建講義。
- 防禦INSERT trigger僅拒removed import的新activities/catalogs，固定訊號lecture_removed，由classroom_access.activity_transaction及legacy create／notes出版邊界映射410 LECTURE_REMOVED；不能變500，亦不能阻止已建活動狀態更新、結果或回填。
- 回填中的remove只影響新引用，已取得作業依原lease繼續；未知結果仍回讀恢復，不因清單刪除自動重送或假成功。

## 必驗

兩教師越權／CSRF／確認取消／重送；各一般清單與直接舊URL；同來源新UUID；remove↔activity與remove↔version兩方向屏障；confirmed preview重送；removed講義既有活動全文、結果、預覽、部分／未知回填及恢復；Google零delete呼叫；課堂／課程無刪除端點。所有兼容測試用臨時007 fixture，操作者DB不作測試材料。
