# 圖表渲染紀錄

2026-11-27（台北時間），基底 e9a29c7。使用 PlantUML CLI，以 JDK 21 執行如下，退出碼 0，核對三張 PNG 簽章：

    java -Djava.awt.headless=true -jar plantuml-speckit-003.jar -charset UTF-8 -failfast2 -tpng ./diagrams/012-*.puml

[組件圖](../../diagrams/012-tab-classroom-membership-component.png) · [類別圖](../../diagrams/012-tab-classroom-membership-class.png) · [時序圖](../../diagrams/012-tab-classroom-membership-sequence.png)

2026-11-27，依使用者對兩項草案的回報，記錄組員已完成首版圖意審查。審查者姓名與外部紀錄連結未提供。若釐清改變圖意，須重繪並複核。

## 行為釐清後重繪

2026-11-27（台北時間），依使用者確認的同堂單一組別、複製頁重新加入、有效原頁恢復及最後有效頁逾時後可換組，更新組件、類別與時序圖。沿用上述 CLI，退出碼 0，三張 PNG 簽章均通過。首版審查紀錄保留，新版圖意待組員複核。

2026-11-27（台北時間），使用者修訂複製分頁規則。複製有效課堂分頁會沿用原堂原組，新頁取得獨立資格。沿用上述 CLI 單獨渲染 012-tab-classroom-membership-sequence.puml，退出碼 0，PNG 簽章通過。此次時序變更待組員複核。

## 新版複核

2026-11-27（台北時間），依使用者本對話回報，記錄雙組確認規則，以及組員完成新版圖意複核，包含複製有效分頁直接進入原堂原組的修訂。個別確認者、審查者姓名與外部連結未提供。

## 實作對照

- 組件圖。學生加入與課堂腳本向課堂端點發出分頁請求；集中授權透過 `classroom_membership.py` 解析，再套用於 003 送答／結果與 010 在線統計。
- 類別圖。資料表保存瀏覽器與固定課堂下的組別、資格及世代；待重試的本機操作於 `quiz-submission.js` 納入分頁作用域。課堂、組別與既有結果關聯遵循圖示。
- 時序圖。加入、恢復及換組走 SQLite 寫入交易。重新加入在伺服器確認撤回後才清理本頁並導向加入頁；取消維持原頁。複製及重整各發新的文件資格，交接確認後才延續原操作作用域。這些屬於現有圖中的授權和本頁清理步驟，行為圖無需重繪。

以上為 Codex 的本機對照。組員對實作版的互審與 T018 真人驗收待完成。

Converge 核對五項 FR、三項 SC、加入／恢復／撤回契約，以及憲章的權限、保留資料、Diagram First 和驗收要求。受控驗證已涵蓋同堂異組從加入交易即拒絕、跨堂隔離、換組後舊世代拒絕、待重試送答的作用域及教師歷史授權。剩餘證據已由 T018／T019 追蹤，包含瀏覽器原生複製、在線延遲和組員互審。


## 2026-11-28 最新master整合審查

於隔離分支codex/review-24-integrated將PR24的07a9f15合入master 2c43854，保留已合併#19／#20。兩功能012圖檔衝突以本功能改名012-tab-classroom-membership-*解決；共同需求雙方段落均保留。三張PNG以Java24、PlantUML1.2026.10 CLI重新產生，退出碼0且PNG簽章正確，圖意未改。

整合後Python完整回歸619 passed、1 Windows POSIX skip、98 subtests passed（114.11秒）；Node88 passed。非真人Google或原生複製分頁證據，T018／T019仍待真人驗收及最後收斂。完整人工矩陣與審查紀錄見docs/pr24-issue17-integration-review.md。


## 2026-11-28 最終人工驗收與收斂

整合基底master 2c43854 + PR24 07a9f15；關課F5修正提交5a27264。使用者已逐步確認跨堂分頁、原生複製及在線去重、重新加入草稿／pending、教師登入登出、關課終態及修正重驗、歷史與#19／#20預覽。操作者為本對話使用者，未提供姓名、瀏覽器版本或獨立截圖，不補造。人數歸零及離線恢復均為使用者估計1秒內，符合5秒目標。

最後一組已明確回覆「是」：兩個獨立瀏覽器／訪客視窗加入QA17-B第2／6組，教師各見在線1人；第2組先完整提交同題、第6組再交不同答案，結束後教師及兩學生結果正確，第2組順位1且勝出、第6組順位2，各自原答案及F5結果保留。未藉此宣稱測試了兩個不同自然人。

自動完整Python整合基線619 passed、1 Windows POSIX skip、98 subtests passed；前端修正後完整Node90 passed。真Chrome自動補驗7項與真人原生複製分開。權限、資格到期、世代、CSRF、競態、課堂碼重用、晚到回覆及重試key依既有受控契約／整合／Node證據。瀏覽器封鎖送答用於pending介面驗收，不冒稱Google自然失敗或伺服器已寫入後丟失回覆。本輪回填只驗證預覽，未另操作真Sheets寫入；既有回填回歸保留。

Converge對照5 FR、3 SC、規格三組情境、計畫中的分頁授權／原子換組／恢復交接／在線去重／送答作用域／資料保留、19任務與六項憲章原則，未發現missing／partial／contradicts／unrequested產品缺口。前後extensions.yml皆不存在。Converge本身未改tasks或追加空階段；此段及T018／T019勾選為獲授權交付文件收尾，與唯讀檢核分開。

✅ Converged — the implementation satisfies the spec, plan, and tasks.

三圖保留後端權限、固定堂／組及本頁清除責任；關課修正僅以非授權終態標記延續圖中CLOSED分支，不新增身分或資料可見範圍。圖檔已依功能重命名並CLI重繪、核對；同學原先審圖回報保留，本輪整合與F5修正尚待同學互審，不冒稱已取得新的APPROVED。未推送、未合併master或關閉Issue #17。
