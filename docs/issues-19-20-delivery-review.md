# Issue #19／#20 整合交付檢核

日期：2026-11-27（Asia/Taipei）。AI技術核對：Codex。人工執行：本對話使用者，未另提供姓名；不冒認具名組員審查。

## 版本與範圍

- master基底：80510a6bbf6310bf4634052a7a56066f8f1e8baf，PR前再次fetch仍為此版本。
- 產品人工基準：1502fcb，包含#19及#20與原#16提交；此後只增加驗收／故障自測工具、CI、時間測試輸出及交付文件，未修改產品src。
- 真POSIX測試提交：912db43121061c449d9afa74b6ecd37cdfb8f207；[run46005787175](https://github.com/Afra0704/se2026-group20-speckit/actions/runs/46005787175) success，實際日誌已讀取。
- 不包含#17分頁資格擴充，不改snapshot、排序／勝組、授權期限或schema，不清除日常DB／key。

## 技術對照與證據

| 範圍 | 結果與證據 |
| --- | --- |
| #19 13 FR／6 SC、11故事情境 | 原活動結果直達、query返回原選取、原堂勝組／group_label與HTML／教師DTO外層；驗證映射及拒絕發生於來源前／保存前／每批寫入／恢復前，未改不可變snapshot。詳012規格／契約／diagram-review與50項補充回歸。 |
| #20 14 FR／5 SC、14故事情境 | aware與可信UTC解讀、分鐘截取、未知／缺值／壞值、生命週期及notes語意；原資料保留回歸與實際三時區環境完成。詳011規格／契約／diagram-review及posix-ci-evidence.json。 |
| 自動完整基線 | Python608passed、98subtestspassed、Windows1skip；Node82passed（1502fcb產品版本）。未將重疊批次相加。 |
| 補充受控異常 | context／重連／restart50passed（14.96s），缺失／跨堂勝組、直接權限請求、未結算、原返回／取消／失敗及固定版本恢復；QA工具合成自測2passed（1.08s）。 |
| 真Chrome | Chrome158.0.8127.37，UTC／Asia/Taipei／America/New_York獨立context通過，返回同activity，純文字呈現。 |
| 真POSIX | ubuntu-24.04、Python3.13.18；TZ＋tzset子程序UTC、CST、EST/EDT，1passed（0.55s），JUnit0skip。原Windows skip保留但已有另一真環境證據，不刪測試騙過驗收。 |
| 真人A01～A13 | 教師A、兩組1／42、第二教師、同名／不同版本、關課／講義移除歷史、全無勝組、授權取消／重連、受控中斷後重啟及新衝突皆依逐次回報記錄。詳人工驗收，不冒認Codex親自操作。 |
| 兩份真Sheets | 第一份6單題；第二份4題6格、前兩題各2小題。勝組位置、無勝組略過、覆寫、回讀、標號／非目標格／合併／格式均由使用者回報通過。沒有副本URL／截圖，不補造。 |
| 精確時計 | 按結束前21:19:23.22、成功後21:19:43.49，使用者確認頁面2026-11-27 21:19；符合分鐘區間，不自造秒值／誤差。 |
| 原時間偏差 | 使用者回報找到原頁且目前正常；未提供原頁名／舊值，不宣稱獨立重現唯一根因或固定8小時偏差。 |
| 圖／憲章 | 對應兩份diagram-review；授權、唯讀投影、原結果關聯及恢復分支一致。CI及QA工具不是產品新元件，沒有新增圖意差異；不冒認同學再次審圖。 |

## 機敏與可重現性

只提交不含憑證的QA包裝與合成自測、人工回報及CI已知樣本。私有啟動器、session key、DB、token、Google key與本地審計原檔均在ignored tmp，不加入PR。受控未知為一次未送出的單格寫入及回讀中斷；實際原writer委派[2,1]，不冒稱Google自然逾時或服務端日誌。正常create_app不載入故障工具，真人場景完成後標記停用。

## 交付判定與剩餘門檻

- 功能與必要驗證證據已齊，AI技術對照未發現需新增產品實作的缺口，可發PR請組員審查。
- 012 Converge原F1／F2（真人／真來源）及011原F1／F2（POSIX／真人）已補證據；012 T049與011 T047的最終交付收斂仍等待另一位組員技術互審，保持未勾。
- 本次沒有把AI自查或使用者功能驗收當作組員程式／三圖互審。收到真實PR review後補審查者、結論及必要修正重驗，再收斂、合併並關閉Issue。
- PR關聯Closes #19／Closes #20，待合併後自動結案；目前先不提前關閉。兩組需求確認依各規格既有使用者回報，不補造具名OpenSpec紀錄。

## 2026-11-27 正式組員審查與合併補記

GitHub唯讀API已核對：[PR #23組員審查](https://github.com/Afra0704/se2026-group20-speckit/pull/23#pullrequestreview-6089360085)，審查者itsusername15，狀態APPROVED，針對提交c5e1fb2b6e12b61d506bf0ef0d60b1860a510328，時間2026-11-27 22:07:34（台北）。審查原文：「完成 #19／#20 技術審查。已核對原課堂回填、台北時間顯示及驗收紀錄，相關 Python 95 項、Node 8 項通過。舊非數字組名僅為可捨棄的開發測試資料，依已確認範圍通過。」95／8為審查者回報，非Codex新執行；未另外取得逐圖意見，不補造獨立審圖文件。

itsusername15於2026-11-27 22:07:36合併，merge commit為2708ebe757c1c4dc3e7cf16783c1ab3b21d008d3；#19於22:07:37、#20於22:07:40自動Closed／Completed。PR該head的CI run46007121360為success，沒有行內待修意見。

本次只補已發生的審查／結案證據。合併樹已確認與被核准head相同；沒有因可捨棄開發資料的說明而刪DB、改舊組名或重寫答案／歷史。前文「待同學審查／未合併」為當時狀態，以本段為最新事實。


## 2026-11-27 合併後最終收斂

PR #23 已由 itsusername15 核准並合併（2708ebe757c1c4dc3e7cf16783c1ab3b21d008d3），#19／#20 已 Completed。此為合併後核對，不冒稱在同學合併前完成。實際 review 與日期見 docs/issues-19-20-delivery-review.md 最新補記。

本次對照 011 的14 FR／5 SC、14驗收情境與012的13 FR／6 SC、11驗收情境，以及兩份計畫既有決策、51／49任務與六項憲章原則。沿用已記錄的程式對照、自動回歸、真POSIX、真人與真Sheets證據；組員審查補齊最後治理缺口。missing／partial／contradicts／unrequested 均為0，沒有追加新任務。converge核對本身未改寫tasks；後續T047狀態更新為獲授權交付文件收尾。無extensions.yml，沒有前後hook。

✅ Converged — the implementation satisfies the spec, plan, and tasks.

本次只更新文件，未重新執行產品測試、修改程式、操作DB或Google授權；不擴張為其他Issue或尚未列入本輪的改善項目已完成。
