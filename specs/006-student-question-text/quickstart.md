# 006 驗收指南（實作完成後執行）

006 已實作，以下供組員人工驗收；尚未執行的真人操作與 5 秒計時不可視為通過。005 的人工任務保持未完成。

## 前提與啟動

沿用 [005 的 CMD 設定](../005-preview-before-start/quickstart.md) 中專用開發 DB、CLASSROOM_MODE=1、本機 SECRET_KEY、Google client/token 路徑及正確教師 ID。006 移除示範模式，不再設定示範旗標；舊 005 文件中的該旗標不適用於移除後的版本。本次不需要新套件、scope 或憑證，不貼出密碼／token。

實作後必須停止舊 Python 伺服器，再從目前工作樹啟動；只重新整理瀏覽器不能讓舊後端自動載入新程式。確定 5000 未被另一個舊服務使用。

```bat
cd /d D:\os_final
.venv\Scripts\python.exe -m flask --app guided_notes:create_app init-db
.venv\Scripts\python.exe -m flask --app guided_notes:create_app run --host 127.0.0.1 --port 5000
```

此區塊以已設定好環境的 CMD 為前提；不重建既有教師、不清空 DB。init-db 只新增結構，舊活動不補快照。若 catalog 已完整保存 prompt，可供新活動使用；若文字真的缺漏則重新匯入並預覽確認。

## 教師與兩組學生人工驗收

教師用 Chrome 一般視窗、甲組用 Edge、乙組用 Chrome 無痕；兩組加入同一新課堂一次。

| 操作 | 預期 |
| --- | --- |
| 匯入單題及兩小題題組，查看教師預覽／保存頁 | 全文、標號、換行與作答對應正確。 |
| 建立活動 | 兩組 5 秒內看到題號、全文及對應欄位，尚未開始時不可填答。 |
| 題組閱讀 | (1)/(2) 各有自己的正文與欄位，全部小題仍為一個提交單位。 |
| 開始、結束及下一場 | 原 005 規則有效，不需重新加入；下一場文字不混入上一場。 |
| 長中文、英文長字串、換行及特殊符號 | 不截字，可正常換行／捲動閱讀；輸入旁的小題內容對應正確。 |
| 題目欄含 `<script>` 或 HTML 片段 | 顯示文字，不執行；在隔離講義副本測試，不放真實敏感資訊。 |
| 原作答欄已有測試答案 | 學生看不到該原值，不被預填或混成題目。 |
| 活動後修改來源文字，再重新匯入新版 | 舊活動維持原文，新活動才顯示新文。 |
| 移動欄列／換主題號後匯入另一講義 | 題號、小題、文字及答案格仍對應。 |
| 刷新／斷線復線 | 恢復同一活動文字版本與正確作答階段。 |
| 舊活動沒有全文快照 | 明確顯示不可用提示，不假裝完整、不讀 Sheets 偷補文字。 |

記錄操作者、日期、工作樹版本／commit、情境、預期、實際、5 秒計時與去機敏截圖。正式 003 未接入則只驗全文／階段，不將 QUIZ_UNAVAILABLE／待結算當排名成功。真實雲端回填仍由原驗收項追蹤。

## 自動驗證計畫

測試檔已建立；獨立測試 CMD 清除手動模式旗標，沿用 fixture 臨時 DB：

```bat
cd /d D:\os_final
set "GUIDED_NOTES_CLASSROOM_MODE="
.venv\Scripts\python.exe -m pytest tests -q
node --test tests/student-question-text.test.cjs tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs tests/activity-sync.test.cjs tests/notes-ui.test.cjs
```

需覆蓋 strict v1 仍拒絕 prompt、Display v1 白名單／全等匹配、單題／題組／移動版型、空字／換序／跨版／重複／額外項、原文空白與 LF、provider 不可用、原子回滾、活動快照不變、舊活動缺字、來源修改、新舊版本同時存在、來源答案與座標排除、003 context 不變、005 單活動與準備中結束、既有回填契約。

Node 測 DOM 純文字／對應／同步；實際長文字排版與程式片段不執行仍需瀏覽器人工驗收。所有自動 Sheets 使用替代端，不冒稱已寫入真實來源。

另外驗證：舊示範旗標即使存在也不提供示範講義；缺清單／顯示／受理服務會回約定不可用錯誤，不建立假活動或寫示範答案。產品不含內建示範模式；課程要求錄製 Demo 影片不受影響。
