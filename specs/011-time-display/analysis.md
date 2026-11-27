# 011 實作後一致性檢核與交付準備

日期：2026-11-27（Asia/Taipei）；Codex。範圍：011-time-display，基底80510a6之未提交實作；不改012或同學numeric-group-labels。

## 對照結果

- 19項FR／SC、14個故事驗收情境、7項研究決策及憲章6項原則已逐項核對。功能實作沒有發現missing／contradicts項；驗證有2類partial，見下。
- 固定台北、到分鐘不進位與精確instant_utc分離，spec／plan／tasks／data-model／contracts／三圖一致。原C1依使用者回報OpenSpec確認已解除，具名證據仍如實待補。
- 來源限制、無時區保守回退、空值／格式損壞、直接結束證據都實作於time_display／time_views，與data-model狀態表相符。
- history仍同一SELECT及原驗權／排序，新增sidecar而非取代raw；notes只增加HTML helper，不擴充writeback JSON、snapshot或CatalogDTO。原字串、勝組及結果版本保留測試通過。
- 三圖責任／時序沒有新增差異，mapping見diagram-review.md。分鐘文字調整已於先前CLI渲染；本次沒有假稱同學再次審圖。
- 新增browser驗證腳本屬T026的具體落實，使用既有Chrome／Node，不新增產品依賴；不是新增使用者功能。
- 本分析在implement內記錄已完成的檢核；不是呼叫read-only speckit-analyze來修改文件。

## Converge 結果

本節由implement記錄converge的會話結果；converge對產物的寫入僅為tasks.md尾端追加。不能宣稱全部converged。

| ID | 類型 | 嚴重度 | 來源 | 剩餘工作 |
| --- | --- | --- | --- | --- |
| F1 | partial | HIGH | SC-002、T025 | 真POSIX server三時區尚未執行，已有可執行測試，Windows skip不能抵證據 |
| F2 | partial | HIGH | SC-005、T018／032／040／045 | 真人教師＋兩組學生M01～M06尚未驗收；仍不得結案 |

統計：missing 0、partial 2、contradicts 0、unrequested 0；CRITICAL 0、HIGH 2。兩類均為已追蹤的驗證缺口，不代表目前程式已發現對應失敗。以新T050／T051彙整後續工作，原任務ID與未完成狀態保留。

## 分段 commit／PR 材料（T048）

1. `feat: add source-aware Taipei time presentation`：純時間核心、來源／生命週期adapter及三份核心／契約測試，可單獨驗54項。
2. `feat: show consistent event times in teacher views`：history sidecar、JS與notes HTML、安全fallback、資料保留／角色／跨環境驗證與011規格／圖／紀錄。

PR描述建議：教師活動歷史原本直接顯示無時區建立字串，notes對naive或壞值可能依主機解讀或失敗；本變更統一台北至分鐘、明示建立／開始／結束及notes事件用途，保留原資料／授權／結果。列出575 Python、98子測試、77 Node及真Chrome三context；明示1項POSIX skip與尚未執行M01～M06，不把準備材料視為已發PR或review。

不包含012的功能或私有資料。實際commit之後仍須以SHA／dirty狀態核對驗收版本。Issue #20目前不可關閉；必要跨環境及人工證據、同學review完成後才評估。

收斂結果為 `tasks_appended`，已於Phase8追加T050／T051；沒有改寫原task次序。after_converge／after_implement的extensions.yml不存在，無hook需派送。T047整體仍待剩餘驗證完成，不宣稱converged。
