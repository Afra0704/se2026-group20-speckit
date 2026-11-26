# 008 分層 HTML 與原 API 契約（計畫）

所有新教師頁require_teacher，未登入HTML303 `/teacher/login`；API仍401/403/404 JSON，不redirect Google。沒有修改目前已執行的路由，以下於implement後才可驗。

| HTML GET | 內容 |
| --- | --- |
| `/teacher` | Google/classroom模式歡迎、姓名、進入我的課程、登出；沒有整排流程表單。 |
| `/teacher/workspace` | 本人課程卡片、建立課程、空清單提示。 |
| `/teacher/workspace/courses/<cid>` | 課程總覽；橫幅、左側三區導覽、目前位置。 |
| `.../courses/<cid>/lectures` | 本課程active講義／版本、＋匯入選單、個別刪除；不自動連Google。 |
| `.../courses/<cid>/classrooms` | 原OPEN/CLOSED課堂列表及建立課堂；沒有刪除按鈕。 |
| `.../courses/<cid>/classrooms/<rid>` | 必驗rid屬cid；加入碼、學生組別、選講義、活動控制與歷史。 |
| `/teacher/workspace/imports/<flow_id>` | 只render本人綁定flow目前步驟，無token；課程導覽固定原cid。 |
| `/teacher/workspace/activities/<activity_id>/lecture` | 驗活動與課堂owner後讀原版本／全文，removed時顯示歷史提示；沒有新建活動按鈕。 |

路由中cid/rid用原驗證服務；教師B存取A的資源維持原不可見錯誤，不顯示名稱。`/` 身分入口及 `/student` 原行為保持，學生無須Google。

## 保留接口

- 原GET/POST `/teacher/courses` 及course classrooms／room activities／start／finish／close JSON、學生state/results不換HTML、不改欄位。
- 新workspace.js呼叫既有JSON mutations（CSRF），成功後依server識別組合固定HTML路徑；不允許任意外部next。
- 原 `/teacher/notes/courses/<cid>` HTML 303到新講義頁，notes全域HTML提供回我的課程入口；API Accept application/json 的原契約保持。
- 原preview、catalog JSON、export preview、operation/report/recovery URL保留；一般版本遇removed按lecture-lifecycle契約回410，歷史不使用一般頁繞active。
- 008 preview HTML由DB的preview→flow關係決定課程側欄與確認動作；舊notes確認API維持CatalogDTO格式，若HTML預覽屬008且完成，依server flow固定303原課程清單；無flow的舊HTML仍走原保存頁，不接受任意next。
- legacy CLASSROOM_MODE=false 不強制套課程頁，保留原學生／教師模板與API回歸；本輪新介面目標是Google＋classroom模式。

## UI與恢復

選單button有aria-expanded/controls、兩個有文字的選項；Escape／點外部關閉，焦點回＋。來源步驟錯誤在原課程區可見；重新整理／返回依URL及server flow恢復，不以localStorage的最後課程改寫歸屬。JS忙碌時禁重送，完成／失敗正確恢復按鈕。

固定導覽只顯示必要身分、我的課程、登出；Sheets連接／重連移入匯入任務。教師登出依007，不清學生session/proof。保留原課堂控制的一秒輪詢與過期回應丟棄規則，固定rid不讀別課的舊選擇。

1366×768、390×844驗橫幅／側欄可辨認，窄頁可收合；長字換行，不遮操作；列表有空、載入、錯誤狀態。不新增公告、作業、評分等圖片中的其他LMS模組。


## 2026-11-26 實作接線補充：教師組別清單

新workspace限定 `GET /teacher/workspace/courses/<cid>/classrooms/<rid>/groups`，回 `{groups:[{group_id,name}]}`；復用require_teacher、course ownership及owned_classroom並驗rid屬cid。只讀原classroom_groups，無提交內容、學生資格或proof。固定課堂頁隨原一秒輪詢更新，晚到資料需驗原rid；學生未登入教師不可讀，原學生state及002 JSON格式不變。對應FR-003與T017，無新增身分系統。
