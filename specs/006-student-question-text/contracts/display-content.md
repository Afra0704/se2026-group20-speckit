# 題目全文契約（Display v1 已實作）

## 不變的介面

CatalogDTO v1、ResultSnapshot v1、Submission payload 及 003 的 questions.content 不增欄位、不改 ID／計數／順序／版本。v1 不接受 prompt_text 的測試必須保留。

## 新增內部 DisplayContentDTO v1

```json
{
  "display_contract_version": 1,
  "import_id": "11111111-1111-4111-8111-111111111111",
  "import_version": 1,
  "questions": [{
    "question_id": "22222222-2222-5222-8222-222222222222",
    "display_number": "1",
    "kind": "single",
    "items": [{
      "item_id": "33333333-3333-5333-8333-333333333333",
      "subitem_label": null,
      "prompt_text": "電腦的中央處理器，英文簡稱是什麼？\n請填英文縮寫。"
    }]
  }]
}
```

題組沿用一個 question（kind=question_set），items 有序包含每個小題的 item_id、subitem_label、prompt_text。驗證以同版 catalog 為準，不能各取最新或以文字猜配對。

### 提供端

- `notes.display_service.get_display_content(teacher_context, import_id, import_version)`：檢查教師及 import 所有權，從指定不可變 recognized 建立並驗證安全 DTO。
- `notes.course_catalogs.get_course_display_content(teacher_context, course_id, import_id, import_version)`：先檢查 course 歸屬與 import-to-course 綁定，再呼叫上者。
- 課堂 adapter config `GET_COURSE_DISPLAY_CONTENT`，legacy adapter config `GET_DISPLAY_CONTENT`。None 代表嘗試預設正式提供端；非 callable 或缺服務回 503，不以其他內建資料或 AI 生成缺字。
- 不新增學生直接查講義／Sheets 的端點；教師保存頁在原授權路由取得安全文字作模板 context。既有 JSON catalog 回應仍是純 v1。

### 新活動寫入

既有建立 request／201 response 的核心欄位不改。必須先取得同一 import_id/version 的 catalog 與 display，嚴格匹配後，在既有寫交易原子保存活動核心與 activity_displays；課堂模式同筆更新 current_activity_id/state_version。新活動禁止在缺字時默默只建立題號。

## 學生 state 回應增量

沿用 `/classrooms/{id}/state` 的 activity 與 legacy `/activities/{id}/state` 根物件，新增：

```json
{
  "display_contract_version": 1,
  "question_text_status": "complete",
  "questions": [{
    "question_id": "22222222-2222-5222-8222-222222222222",
    "display_number": "1",
    "kind": "single",
    "items": [{
      "item_id": "33333333-3333-5333-8333-333333333333",
      "subitem_label": null,
      "prompt_text": "電腦的中央處理器，英文簡稱是什麼？\n請填英文縮寫。"
    }]
  }]
}
```

這是增量片段；保留既有 activity_id、phase、phase_version、角色／本組欄位及 005 的 title。無當前活動仍為 activity=null。無快照的舊活動 status=unavailable、item.prompt_text=null；學生明示「此活動版本未包含完整題目，請老師選擇完整版本並建立新活動；文字仍缺漏時請重新匯入」。既有階段限制保持，不自動補寫或重開。

所有層以白名單序列化，不含 blank_id、來源答案／位置或他組資料。文字用 textContent/Jinja autoescape，禁止 innerHTML 或 safe filter。state 只讀活動快照，無 Sheets 網路請求。

## 錯誤約定

| 情況 | HTTP／錯誤碼 | 行為 |
| --- | --- | --- |
| 課程／講義不屬此教師或課程 | 沿用 403/404 的既有隱藏資源約定 | 不洩露其他人的資料。 |
| 指定版本不存在 | 404 CATALOG_NOT_FOUND | 不降級查最新。 |
| 新活動所選版本真正缺文字 | 409 QUESTION_TEXT_UNAVAILABLE | 提示重新匯入／選完整版本，不建立活動。 |
| display 與 catalog ID／版／順序／標號錯配 | 409 DISPLAY_CONTENT_MISMATCH | 拒絕建立，全部回滾。 |
| 顯示 provider 不可用 | 503 DISPLAY_CONTENT_UNAVAILABLE | 明示服務問題，不產生假題目。 |
| 新匯入文字空白或合併對應歧義 | 沿用 422 ANSWER_AMBIGUOUS 等辨識碼 | 在確認前標明題號／小題問題，拒絕發布。 |
| 已存活動快照損壞／與核心錯配 | 409 DISPLAY_CONTENT_MISMATCH | state 明示失敗，前端沿用失敗停用，不洩漏內部資料。 |
| PREPARING/LIVE 時建立第二場 | 409 ACTIVITY_IN_PROGRESS | 沿用 005。 |

provider payload 的未知欄位、型別錯誤及重複 ID 視為 DISPLAY_CONTENT_MISMATCH。不得用已有來源作答格原值補 prompt；題目欄本身若含老師文字則照原文顯示，不以 AI 判斷哪些字像答案。

## 示範模式移除與介面核對

依使用者 2026-11-25 指示，刪除內建示範清單、受理 fallback、示範開關與專用入口，不建立 demo 識別例外。正式 import_id 維持 UUID，與同版 canonical catalog 完全一致。舊環境即使殘留 GUIDED_NOTES_DEMO_CATALOG，也不能啟用示範資料或受理 fallback。

清單服務不可用沿用 CATALOG_UNAVAILABLE，顯示服務為 DISPLAY_CONTENT_UNAVAILABLE，受理未接入為 QUIZ_UNAVAILABLE；不把移除示範當成正式 003 已完成。介面核對安排在 tasks 產生後、實作前，記入 T002；原全文行為及已審圖狀態不重新表決。
