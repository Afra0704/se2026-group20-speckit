## 變更與目的

教師從目前或歷史活動結果即可預覽回填，不必抄活動識別；預覽、報告及返回結果固定在原課程／課堂／活動／講義版本，勝組顯示原堂「第 N 組」。時間統一台北 UTC+08:00、24 小時制、到分鐘不進位，缺值／壞值有明確提示。

沿用原覆寫、冪等、先回讀恢復及安全重新授權；不改原答案、順位、勝組、snapshot、result_version、資料庫結構或 Google 金鑰。基底為已合併 PR #22 的最新 master 80510a6，保留 #19／#20 原提交鏈，不含 #17 分頁資格擴充。

## 關聯 Issue 與需求

Closes #19
Closes #20

對應 specs/012-result-writeback 的 FR-001～013／Q01～Q13，以及 specs/011-time-display 的 FR-001～014／M01～M06。共同需求依使用者已回報的雙組確認；確認者姓名及獨立外部紀錄未提供，沒有補造。

## 文件與圖表

- [整合交付檢核](https://github.com/Afra0704/se2026-group20-speckit/blob/codex/integrate-issues-19-20/docs/issues-19-20-delivery-review.md)
- [逐步人工驗收](https://github.com/Afra0704/se2026-group20-speckit/blob/codex/integrate-issues-19-20/docs/issues-19-20-manual-acceptance.md)
- specs/011-time-display/、specs/012-result-writeback/ 的 spec／plan／tasks／contracts／diagram-review。
- diagrams/011-time-display-*、diagrams/012-* 的 Component、Class、Sequence 原始圖與 CLI PNG；保留原審圖及本輪 AI 圖對碼的證據界線。

## 自動驗證

- Windows完整回歸：Python **608 passed、98 subtests passed、1 skipped**；Node **82 passed**。產品基準1502fcb，此後只新增驗收／CI／測試輸出與文件，未改產品src。
- context／重連／restart補充回歸：**50 passed**；受控QA工具合成自測 **2 passed**，批次重疊不相加成總數。
- 真Chrome：UTC／Asia/Taipei／America/New_York三個獨立context通過，返回原activity且純文字呈現。
- [Linux POSIX三時區CI](https://github.com/Afra0704/se2026-group20-speckit/actions/runs/46005787175)：ubuntu-24.04、Python3.13.18，**1 passed、0 skipped**；實際TZ＋tzset子程序輸出與JUnit已核對，補齊Windows唯一skip的跨環境證據。
- git diff --check 通過；未提交本地key、token、DB、私有launcher或QA審計原檔。

## 人工驗收

本對話使用者逐項回報A01～A13通過，涵蓋教師加兩組1／42、第二教師越權、同名活動與版本1／2、關課／移除講義歷史、無勝組、授權取消／重新連接，以及受控中斷後重啟／沿用原同意／新增來源衝突。

兩份真Google Sheets測試副本：第一份6單題；第二份4題6格（前兩題各2小題）。回填／回讀、無勝組略過、非目標格、標號、合併與格式均由使用者核對。QA的應用層寫入批次為[2,1]，已完成題組未重送。

時間精確紀錄：按結束前 **2026-11-27 21:19:23.22**、成功後 **21:19:43.49**，使用者確認頁面為 **2026-11-27 21:19**。另回報找到原偏差頁且現在正常；未提供原頁／舊數值，未宣稱獨立重現固定8小時差。

## 已知限制與共同需求變更

- 真人結果為使用者回報，沒有另外取得姓名、Sheets URL或截圖；不冒稱Codex親自操作。
- 授權失效與寫入未知採明列QA故障工具，取消／真Google重新授權及真副本恢復由使用者操作，不冒稱Google自然故障。
- 本輪技術互審仍待另一位組員；012 T049及011 T047保持待辦。請review後補結論，再收斂／合併；合併時由關聯詞自動關閉#19／#20，不提前結案。

## 請審查者確認

- [ ] 修改符合關聯需求，規格、任務、圖表與實作一致。
- [ ] 驗證結果及受控／真人／真來源證據界線清楚。
- [ ] #16組號與#19／#20時間／回填接線正確，沒有混入#17。
- [ ] 提交內容及附件沒有機敏資料。
