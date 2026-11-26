# 課堂預覽契約增量

## 建立與讀取

沿用 `POST /teacher/classrooms/{classroom_id}/activities` 的 title/import_id/import_version。成功仍為 201 PREPARING，但同一交易發布目前活動並增加課堂版本。已有任何關聯 PREPARING/LIVE 回 409 ACTIVITY_IN_PROGRESS，不留活動、題目或關聯殘筆；授權及 CSRF 維持原約定。

`GET /classrooms/{classroom_id}/state` 保留既有欄位，在非空 activity 新增 `title` 字串，來自本課堂關聯。純文字顯示，不視為 HTML；學生權限與安全 questions 不變。

```json
{
  "classroom_id": "room-example",
  "classroom_state": "OPEN",
  "state_version": 1,
  "current_activity_id": "activity-example",
  "group_name": "甲組",
  "activity": {
    "activity_id": "activity-example",
    "title": "單題練習",
    "phase": "PREPARING",
    "phase_version": 0,
    "role": "student",
    "group_id": 1,
    "group_name": "甲組",
    "questions": [{
      "question_id": "q1", "display_number": "1", "kind": "single",
      "items": [{"item_id": "i1", "subitem_label": null}]
    }]
  }
}
```

題組仍為一個 question，kind=question_set，items 有序包含 (1)/(2) 等標號；不帶 blank_id、來源位置、憑證及他組資料。

## 開始、結束與關課

- `POST .../activities/{id}/start`：目前 PREPARING→LIVE；非目前目標回 409 INVALID_PHASE，若另有未結束活動回 409 ACTIVITY_IN_PROGRESS。
- `POST .../activities/{id}/finish`：擴充目前 PREPARING→CLOSED；PREPARING 與 LIVE 均僅可結束目前活動。非目前或已 CLOSED 回 409 INVALID_PHASE；回傳既有 activity_id/phase/phase_version。
- `POST /teacher/classrooms/{id}/close`：confirm=true，在交易內關閉全部關聯未結束活動及課堂，不清資料。
- 教師歷史欄位不變，PREPARING 新增結束操作；已結束不代表已結算。
- 提交端點與 payload 不變；PREPARING/CLOSED 或關閉課堂必須拒絕。正式 003 缺少時仍依既有錯誤處理，不注入假結果。

本次以空白開發 DB 驗收，不提供舊多準備資料的遷移或清理介面；正常歷史與結果仍保留。單活動限制是補齊已確認行為，不是待表決的新契約。

## UI 約定

PREPARING 顯示名稱、題號及停用的輸入／提交，提示尚未開放搶答；LIVE 才啟用，CLOSED、斷線及驗證失效停用。有未結束活動時老師不得建立下一活動，前端停用與後端拒絕均須執行。新 id 重建表單，不沿用舊答案；同 id 轉階段也要更新可用狀態。
