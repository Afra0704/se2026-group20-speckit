# 013 圖表審查

2026-11-28（台北時間），在 master a8c7b8f 建立初稿。PlantUML CLI 1.2025.4 渲染成功，三份 PNG 簽章通過。

- [組件圖](../../diagrams/013-submission-feedback-component.png)
- [類別圖](../../diagrams/013-submission-feedback-class.png)
- [時序圖](../../diagrams/013-submission-feedback-sequence.png)

圖表涵蓋本題提示、原操作重試、正式受理，以及 #17 的分頁資格與重新加入邊界。結果未知的編輯與重試規則已更新到時序圖，PlantUML CLI 重新渲染及 PNG 簽章核對均成功。

2026-11-28，使用者回報 SpecKit／OpenSpec 雙組已確認，組員已完成三圖審查。個別確認者和外部紀錄連結未提供。實作後依憲章再次核對程式與圖表。

實際使用命令（專案根目錄，PowerShell）：

```powershell
$jar = Join-Path $env:TEMP 'se2026-plantuml-1.2025.4.jar'
$uml = Get-ChildItem diagrams/013-submission-feedback-*.puml | ForEach-Object FullName
& java '-Djava.awt.headless=true' -jar $jar -charset UTF-8 -failfast2 -tpng $uml
& java '-Djava.awt.headless=true' -jar $jar -charset UTF-8 -failfast2 -tpng diagrams/013-submission-feedback-sequence.puml
```

三圖批次與時序圖單獨重繪皆退出碼 0，產出 PNG 簽章為 `89504E470D0A1A0A`。

分析修補後，時序圖補上重送內容衝突的分支。沿用上列最後一條命令重繪成功，退出碼 0，PNG 簽章一致。原三圖的已審紀錄保留，此次時序圖差異待組員複核。

## 實作對照

- 組件圖對應學生課堂表單、共用送答模組、#17 文檔作用域及既有正式受理端點。
- 類別圖對應作答欄位、單題回饋及各作用域的原始 UUID 和內容。A1 採未決資料的相容選填標記，仍屬同一操作。
- 時序圖的欄位錯誤、送出後未知、原樣重試與 A1 衝突分支均對應 `src/guided_notes/static/quiz-submission.js`。顯示衝突後只能核對或依 #17 重新加入。無程式與圖意差異需要重繪。

使用者已指示 A1 一併實作。更新後時序圖與本輪實作仍待組員複核。

2026-11-28交付檢核：Codex已將三圖逐一對照render／attach／scope／replay／A1分支，責任、資料及時序一致，詳見delivery-check.md。Java24／PlantUML1.2026.10 checkonly退出0，三份既有PNG簽章正確，未變圖意故不重繪。這是AI圖對碼檢查，不替代另一位組員對A1更新圖的複核；確認者與回報尚未提供，T021維持待辦。

同日後續：在完成S1–S3且本聊天室明確列出A1更新圖複核為最後待辦後，使用者回報「同學已審核」，據此將T021記為已完成。組員姓名及獨立審查連結未提供，不補造；此為使用者回報的組員圖意複核，不是GitHub正式review狀態。未改圖意，無需重繪PNG。
