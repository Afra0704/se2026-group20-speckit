# Diagram Rendering Report

執行日期為 2026-11-23，分支為 `001-guided-notes`。

使用 Java 24.0.1 及 PlantUML 1.2026.10 CLI。
JAR 取自 [官方發行頁](https://github.com/plantuml/plantuml/releases/tag/v1.2026.10)，
下載至被忽略的 `tmp/tools/`，供本機渲染使用。

JAR SHA256 為 `E9BC9E6B2EB715E8C0C929F3DCB5FC1923BE13F37599B09C293C66D354E88686`。
此雜湊記錄本次下載檔案，尚未與官方獨立發布的校驗值比對。

實際成功執行的 PowerShell 指令如下。Java 與 JAR 路徑可依組員電腦調整。

```powershell
& 'C:/Program Files/Java/jdk-24/bin/java.exe' '-Djava.awt.headless=true' -jar tmp/tools/plantuml-1.2026.10.jar -charset UTF-8 -tpng 'diagrams/001-guided-notes-*.puml'
```

- 最後一次渲染退出碼為 0，三份 .puml 均產生同目錄 PNG。
- Component 與 Class 使用 PlantUML 內建 Smetana 排版；本次成功渲染無需另裝 Graphviz。
- AI 已開啟三張圖檢視並調整標籤排版，組員人工圖意審查尚待執行。
- 本機 `java` 預設路徑及 JAVA_HOME 未指向本次使用的 JDK，重跑時可先使用上方完整路徑。

| 圖 | 原始檔 | 圖片 | 主要對應 |
| --- | --- | --- | --- |
| Component | [source](../../diagrams/001-guided-notes-component.puml) | [PNG](../../diagrams/001-guided-notes-component.png) | 模組交換約定、FR-001–FR-012 |
| Class | [source](../../diagrams/001-guided-notes-class.puml) | [PNG](../../diagrams/001-guided-notes-class.png) | Key Entities、題目與結果版本 |
| Sequence | [source](../../diagrams/001-guided-notes-sequence.puml) | [PNG](../../diagrams/001-guided-notes-sequence.png) | US1–US3、授權、變動及部分失敗分支 |

2026-11-23 已依使用者對 Q1–Q3 的選擇同步三類圖與規格，重新渲染退出碼為 0。
圖已包含表頭辨識、提交單位與題組、同勝組答案、略過與回讀重試。
依使用者提供的兩張截圖再次修訂並渲染，已支援跨列主題號、子題標號與合併答案錨點。
移除手動劃分題組假設；每個主題號是一個提交單位，子題答案分別回填。
2026-11-23 使用者回報 Q2、Q3 已與 OpenSpec 組確認，確認者姓名尚未提供。合併辨識細節仍需以完整工作表中繼資料實測。
實際 Google Sheets 匯入、寫回、權限及失敗恢復驗收尚未執行。

Plan 階段於 2026-11-23 補上 Operation Repository／Source Lease、idempotent operation 及恢復 claim，
時序圖明確採每主題號一次 RAW batch，單一請求成功具原子性，逾時為未知。
重新執行相同 CLI，三份圖與同目錄 PNG 同步更新，人工圖意審查仍待組員。

2026-11-23 設計整合：與 002 統一主題號／items、import_id／import_version 及結算後回填，
六張 001／002 圖以本機 PlantUML 1.2026.10 重渲染。002 原始作者版本與審查記錄保留在其文件，這次整合後的新增圖意仍待共同複核。

2026-11-23 離線核心續作：Class 補 ImportBundle／Fingerprints 與候選不等於發布的界線；Component 補 CLI-only consent；Sequence 恢復流程改為先讀目前結構並重辨識錨點。以下命令實際完成，退出碼 0，三張同目錄 PNG 更新；AI 已檢視圖面，新增圖意待同學審查。

```powershell
& 'C:/Program Files/Java/jdk-24/bin/java.exe' '-Djava.awt.headless=true' -jar D:/os_final/tmp/tools/plantuml-1.2026.10.jar -charset UTF-8 -tpng 'D:/os_final/diagrams/001-guided-notes-*.puml'
```

ImportBundle／Fingerprints 對應 import_service.py，ExportPreview／PreviewItem 與純恢復對應 export_service.py，Source Access 的憑證核心對應 google_authorization.py／cli.py。Store／WriteOperation／授權與 DB 整合仍未實作，不將整張圖或功能標記完成。

2026-11-24 US1 接線：Class 補 ImportPreview 與 SourceDocument 擁有者，Sequence 補 ready preview 的持久化、確認重讀、短交易發布、失效與重送分支；相同 CLI 命令渲染三張圖，退出碼 0。Component 的 Import／Catalog／Store 已分別對應 import_service、models／repository／notes schema；教師授權沿用 auth，視圖由 notes/routes 及 templates 提供。
Source Lease／WriteOperation／完整回填執行仍為後續設計，新匯入畫面與本輪圖意待同學互審。

2026-11-24 D12 命名擴充：Class 補 LectureDisplayName 與 preview／catalog 的每版本 metadata 關係；Component 標示一分頁及本機命名；Sequence 顯示命名選擇隨 preview／catalog 保存。再次使用上述 CLI 渲染三張 PNG，退出碼 0。來源識別及 CatalogDTO 未變，新的圖意與 OpenSpec 同步待人工確認。
