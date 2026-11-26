# 006 圖表與設計起點（歷史紀錄及實作核對）

日期：2026-11-25；plan 設計已建立，尚未修改應用程式或既有活動，契約目前是計畫文件。

三圖：[Component](../../diagrams/006-component.png)、[Class](../../diagrams/006-class.png)、[Sequence](../../diagrams/006-sequence.png)。對應來源為 diagrams/006-*.puml。

圖意重點：來源題目文字與作答項目綁定、老師預覽確認、活動固定版本、學生只取得安全文字；缺字不能用答案替代，題組不能錯位。005 的預覽時機與單活動規則沿用。

本機程式觀察：RecognizedItem 已有 prompt_text，指紋也包含文字；但目前公開 catalog 的嚴格驗證不接受題目文字，活動保存與學生 state 也不帶文字。因此不能只改畫面或讓學生直接讀完整 Sheets 回應。plan 須設計一致的文字傳遞／版本與介面演進，並與 001/002/003 契約使用端核對。

CLI（本次使用）：

```powershell
& 'C:\Program Files\Java\jdk-24\bin\java.exe' '-Djava.awt.headless=true' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar -charset UTF-8 -tpng 'D:/os_final/diagrams/006-*.puml'
```

Specify CLI 渲染退出碼 0，三張 PNG 均成功產生。使用者回報同學已審圖，並澄清全文為雙方一開始定義、OpenSpec 原先已知的功能，不再列為新提案確認阻擋。姓名與獨立紀錄待補，不代填。

## Plan 圖意展開

將原圖「固定版本→活動→安全顯示」展開為安全 DisplayContentDTO 與獨立活動文字快照，維持原行為：題目欄文字、一小題對一欄、活動內容固定、開始後才填答。CatalogDTO/003 context 不新增文字，避免影響回填及排名。

- 組件圖：安全投影由指定不可變版本抽取，活動同交易保存全文，state 只讀本活動快照。
- 類別圖：新活動必須有快照，舊活動可缺但明示 unavailable；不在 GET 補字。概念上的快照不改動 core 作答項目。
- 時序圖：明示教師／課程權限、版與識別匹配及原子寫入；缺字／錯配需拒絕建立，不讀來源答案補字。

本次修圖是技術責任展開，不虛構已另行人工審閱；同學應核對新增 DTO/provider、快照表及 state metadata。渲染結果以本次實際 CLI 執行為準。

Plan 本次執行上述 CLI 結束碼 0，三類 PNG 均重新產生；git diff --check 通過。沒有執行產品測試、修改應用程式或變更 005 的人工任務。

## Analyze 後文件修正

2026-11-25 使用者指定移除內建示範模式，I1 改為刪除示範相關產品路徑而非增加 UUID 例外；三圖原本就只表達真實講義／顯示／活動，無示範組件，責任及時序不變，無須為刪除不存在的圖中分支重畫。I2 統一為實作前的 T002 介面核對。此紀錄只反映文件修正，程式尚未刪除示範功能。


## 006 實作後核對（2026-11-25）

- Component：notes/display_service.get_display_content 從精確不可變講義投影；course_catalogs 與 classroom_catalog 負責 scoped provider；activity display_service 與 state_view 保存／只讀本活動安全副本；兩種學生 JS 用 textContent。
- Class：DisplayContentDTO v1 由 display_models 嚴格核對；activity_displays 的 activity_id PK/FK、dto、created_at、防 update/delete trigger 對應圖中不可變快照；沒有在 questions.content 增加文字。
- Sequence：實作實際先 store_activity 保存活動／核心題目，再保存快照，最後更新課堂目前指標／版本，全部在同一交易。已把圖中這三步順序改成與程式一致；授權重檢、同堂單活動、PREPARING/LIVE、舊活動 unavailable 分支不變。三圖標題改為實作對應，不再標草稿。
- 已執行本檔所列 Java／PlantUML CLI，退出碼 0，三張同目錄 PNG 重新產生。不涉及產品行為變更。
- Codex 已核對程式與圖意。使用者原先回報同學審圖仍保留；本次修圖與新增介面尚未有同學再次逐項核對結果，不能代填日期或姓名，T002 待補。
