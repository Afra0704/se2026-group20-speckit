# 009 Research — 2026-11-26

只讀 repo 與官方文件，沒有操作應用 DB。依 skill Phase 0 派遣唯讀研究代理核對 schema／競態，主代理核對學生入口／003 邊界，整合以下決策。

## R01 有效碼唯一性

**Decision**：保留 classrooms.code 原值，取消表內永久 UNIQUE，以 `classrooms_open_code_unique` 部分唯一索引約束 code，條件固定 `state='OPEN'`；加入查詢同時限定 code 及 OPEN。

**Rationale**：classroom_schema.sql 的 UNIQUE 阻止歷史重用；classroom_membership.join 目前不限定 OPEN。有效碼可由開放課堂投影，不須雙份碼池。SQLite 支援只對部分列強制唯一。[SQLite partial indexes](https://www.sqlite.org/partialindex.html)

**Alternatives considered**：保留永久唯一再加索引無效；改寫舊碼或刪舊堂損歷史；新增 active-code 表需雙份一致性。僅先查再寫而無 DB 約束不是最後防線。

## R02 非破壞 schema 升級

**Decision**：專用初始化連線在交易前暫停 FK，依 generalized ALTER TABLE 先建新表、逐欄 copy、drop 舊表、rename 新表、恢復相關 trigger／index／view、foreign_key_check、commit，finally 恢復 FK ON 並關閉。不在已開始的 write_transaction 裡切 FK，不用 writable_schema。[SQLite generalized ALTER TABLE](https://www.sqlite.org/lang_altertable.html#otheralter)

**Rationale**：表內 UNIQUE 無法直接移除自動索引。保留既有 db.py 的 core＋Google 身份原子初始化；新 DB 直接建新 schema 並同交易初始化 Google，既有 007／008 DB 由 schema 判斷才執行重建，失敗不提供服務、不留下半份 Google bootstrap。

**Alternatives considered**：先 rename 舊表可能改寫 child FK；清 DB／新空白 DB 違反要求；修改 sqlite_schema 風險高。未知 schema／不一致資料停止，不自動刪資料。

## R03 確認順序及重送

**Decision**：沿用 BEGIN IMMEDIATE、有限 busy retry／rollback。建堂與分配同交易；關課與未結束活動同交易；新加入取得寫入鎖後才解析一次有效目標，建立原組別／membership／grant。目標失效不在同請求轉投新堂。重送關課先驗 ownership，再對 CLOSED 回冪等 200，不增加版本／時間或重跑結算。

**Rationale**：SQLite 一次僅一個寫入交易，統一確認範圍可避免查後失效；read transaction 會持有既有快照，因此晚到結果仍需前端世代／terminal 保護。[SQLite transactions](https://www.sqlite.org/lang_transaction.html)

**Alternatives considered**：只禁用按鈕、分開關閉／釋放或按碼刪占用均不安全。不新增外部鎖服務。現有 insert_room 的 conflict target 必須匹配部分索引條件，只吸收碼衝突，不能吞其他約束錯誤。

## R04 身份與內容權限分層

**Decision**：保留 membership 的原 classroom_id／group_id FK；拆只驗身份的 helper，group_for 另驗 OPEN，供學生內容／提交／結果使用。state 經有效原身份驗證後可回 CLOSED 最小 tombstone，不呼叫 state_view。result-access 改為只在 OPEN 簽發恢復 grant，CLOSED 回錯誤，不更新 session／proof。

**Rationale**：目前 group_for 沒檢 OPEN，recover 反而只允許 CLOSED，與最新規格相反。教師歷史只驗 owner，不能共用學生 OPEN 限制。

**Alternatives considered**：刪 membership／grant 會破壞歷史；只檢到期無法即時關課；只隱藏 UI 仍洩漏 JSON。不新增多堂學生歷史登入。

## R05 獨立學生頁與晚回

**Decision**：`/student` 純加入；成功導航 `/student/classrooms/<classroom_id>`，URL 固定原堂，不由 localStorage 最後課堂覆寫。保留單一目前 classroom_grant；proof 保留原 path，不進 URL／storage。closed terminal 清內容，只留結束文案與按鈕，按下才回加入頁。

**Rationale**：現有 classroom.html 混合加入與內容，classroom.js 以 localStorage 選堂並在 closed 讀結果。學生控制分離避免損及 008 教師；以世代、room／activity scope、版本和 terminal flag 防止晚回、返回舊頁及跨分頁覆蓋。

**Alternatives considered**：Google 學生登入、常駐登入卡、自動跳回均不符合使用者答案。同瀏覽器另頁加入 B 可能使 A 的目前 grant 不匹配；A 顯示資格變更／重新加入，不能追隨 B。closed 恢復不寫 session，避免舊恢復晚回覆蓋 B。

## R06 003／001 邊界

**Decision**：003 submission_context／accept callback 仍在同寫入交易；結果 gateway 學生驗 OPEN，在同一 read transaction 驗權並組裝結果。教師 get_ended_snapshot 不受學生限制，仍依原 activity_id、CLOSED 及 result ready 取得不可變快照。

**Rationale**：quiz/results_gateway 已呼叫 group_for，可集中封鎖，但同學正式服務仍須確認每個直接入口。GET_SETTLED_RESULTS／ACCEPT_SUBMISSION 是接線點，不代表正式排名已完成。

**Alternatives considered**：重寫順位、關課等於已結算或刪除結果超出範圍。D16 變更尚待跨組同步，不能以設計代替雙組決議。

## 已解決技術選擇／待補證據

技術選擇已形成設計。後續使用者於2026-11-26回報C1雙組行為與C2新版圖意皆已確認，來源／姓名限制見diagram-review；003具體介面與具名分工仍由T003追蹤。這不表示產品測試、正式003整合或合併gate已通過。
