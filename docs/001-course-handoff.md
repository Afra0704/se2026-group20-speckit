# 001 → 002 課程講義接線

日期：2026-11-24。提案由 001 負責使用者提出，使用者回報同學同意且分工確認。以下是 001 已實作的 adapter 約定，**確切欄位與命名仍需 002 接線審查**；Issue 編號、確認者姓名與 OpenSpec 同步紀錄未提供。不包含 Google 登入／Drive Picker。

## 002 需提供的唯一課程入口

預期檔案 `src/guided_notes/activities/course_service.py`，002 實作：

```python
def get_owned_course(teacher_context, course_id):
    # 使用共用 require_teacher() 再驗目前登入教師。
    # 從 002 的真實課程儲存驗證 ownership。
    # 未知／其他教師課程：raise ApiError(404, "COURSE_NOT_FOUND")。
    return {"course_id": course_id, "teacher_id": teacher_context.teacher_id,
            "title": "計算機概論"}
```

- course_id 為不透明字串，1–128 個英文字母／數字／底線／連字號；UUID 可直接使用。若 002 採其他識別格式，接線前同步調整驗證與契約。
- teacher_id 沿用共用整數教師 ID，title 為非空字串。
- 不將課程加入碼或活動碼當 course_id。
- 001 動態查找上述函式；缺少模組／函式回 503 COURSE_UNAVAILABLE，不建立假的課程。
- `GET_OWNED_COURSE` 僅為伺服器組態的 adapter 注入點；測試注入 substitute。瀏覽器不能傳入 provider 或自稱課程擁有者。
- provider 呼叫在 SQLite 寫交易外；001 在讀取 Google 後重檢課程權限，再以短交易發布。

## 002 如何開啟課程講義頁

驗證登入後，由 002 的課程頁連到：

```text
/teacher/notes/courses/<course_id>
```

該頁由 001 提供匯入連結表單、所有已確認講義版本，以及將既有未分配講義加入課程的表單。課程名稱由 002 provider 提供，001 不建立 courses／classrooms schema。

## 002 如何選講義與版本

```python
from guided_notes.notes.course_catalogs import list_course_catalogs, get_course_catalog

choices = list_course_catalogs(teacher_context, course_id)
# 前端選取 choices 中的 import_id 與明確 import_version。
catalog = get_course_catalog(teacher_context, course_id, import_id, import_version)
# 接續 002 的活動建立邏輯，固定保存以上版本。
```

也有等價的教師 HTTP 入口：

```text
GET /teacher/notes/courses/<course_id>/catalogs
GET /teacher/notes/courses/<course_id>/catalogs/<import_id>/versions/<version>
```

清單範例（識別為說明用途）：

```json
{
  "course_id": "course-123",
  "title": "計算機概論",
  "lectures": [{
    "import_id": "2f5a4e31-a6d6-4de0-b108-8f1cb5b4cfa2",
    "versions": [{
      "import_version": 1,
      "title": "第一週複習",
      "source_title": "學習單",
      "question_count": 2,
      "answer_item_count": 3,
      "confirmed_at": "2026-11-24T02:00:00+00:00"
    }]
  }]
}
```

同一 import 的 versions 由新到舊排列，絕不自動以最新版本替代活動指定版本。get_course_catalog 返回既有 CatalogDTO，**不加入 course_id、名稱或來源座標**。課程內新活動必須使用此限制入口，不能只靠既有 get_catalog 的教師 ownership，否則無法擋住同教師的跨課程誤選。

## 匯入與既有資料

- POST worksheets／import-previews 可選 course_id；缺省沿用既有無課程匯入，明確空值／非法字串拒絕。
- course_id 保存於 server preview，confirm 不接受更換 course_id。來源變動替代 preview 保留原課程。
- 所有版本固定歸屬同一 import 的課程。更新版本必須使用同課程 preview；無課程 preview 不能更新已分配講義。
- 舊資料不自動分配。明確加入：`POST /teacher/notes/courses/<course_id>/lectures`，JSON 僅含 `import_id`，使用共用 CSRF header；HTML 表單另帶 csrf_token。
- 分配重送回相同關聯；已屬其他課程回 409 COURSE_MISMATCH。若需在另一課程使用同來源，可另行匯入為獨立 import，不提供搬移。
- 001 只新增 notes_import_courses／notes_preview_courses 附表，不改 catalog JSON、題目 UUID、來源 bindings 或舊活動。課程正式 FK／刪除政策需等 002 schema 對齊；目前每次課程操作以 provider 查驗，002 不應直接刪除仍有講義／課堂的課程而留下孤立關聯。

## 範圍及待辦

2026-11-25 PR #6 合流後，002 的真實 course provider、課程頁連結、課堂建立／加入／切換已與 001 接上，使用真實本機 course/catalog 及受控 Sheets／結算完成自動整合驗證。已分配講義回教師課程管理選課堂，不再使用舊的獨立活動按鈕。正式 003、真人兩組與真實 Google 副本驗收仍待完成，詳見 [合流驗證](pr6-integration-validation.md)。

回填仍依 activity_id 查可信結果、固定 import/version，不更換勝組或自動清空來源。2026-11-25 已接上確認、回讀報告、idempotency、來源互斥與恢復 HTTP，替代來源測試通過；正式結算 provider 仍待 002／003。課堂改版後的活動 reference、結果 provider 與跨活動隔離需共同驗收，尚未對真實副本寫入驗收。

建議接線後兩人共同驗收：兩門課各匯入講義、同堂兩活動、另一批學生新課堂、跨課程拒絕、舊資料保留，以及指定活動結果對應原講義。
