# 009 Data Model

設計稿，未修改 schema 或 DB。圖表 [Class](../../diagrams/009-class.puml) 的「有效碼對應」是 classrooms OPEN 列的投影，「歷史配碼」是 code 保留值，均不新增資料表。

## 實體與欄位

| 實體 | 欄位／關係 | 驗證及變更 |
| --- | --- | --- |
| courses | 原 id、teacher_id、title、created_at | 原 ownership，無欄位變更。 |
| classrooms | id PK、course_id FK、title、code NOT NULL、state、state_version、current_activity_id、created_at、closed_at | 移除 code 表內 UNIQUE；其餘逐欄保留。code 為兩字母＋三數字，建立後不可改；id／course_id 不重用／改歸屬。 |
| 有效碼投影 | classrooms 中 state=OPEN 的 code→id | 部分唯一索引 `classrooms_open_code_unique` 約束 code WHERE state='OPEN'，全域唯一，CLOSED 不占用。 |
| classroom_activities | 原 activity_id PK／FK、classroom_id FK、title、時間 | 保留 UNIQUE(classroom_id,activity_id) 及 classrooms(id,current_activity_id) 複合 FK；原活動不移堂。 |
| classroom_groups | 原 id PK、classroom_id、name | 原 UNIQUE(classroom_id,name)／UNIQUE(classroom_id,id)，組名 trim，跨堂同名不同組。 |
| classroom_memberships | 原 id、classroom_id、group_id、proof digest、expires | 原複合 FK 指向該堂組別，從未依 code 授權；不因碼重用更新。 |
| classroom_grants | 原 token digest、membership_id、expires、read_only | 原單一 session 指標；舊 read_only grant 在 CLOSED 亦不得讀內容；開放恢復發新 read_only=0 grant。 |
| classroom_schema_versions（擬新增） | version PK、applied_at | 009 升級標記與重建同交易提交；不重用 auth_instance 或覆寫共用 user_version。 |
| 活動／講義／作答／結果／回填 | 原 activity_id、import_id／version、result_version、快照、operation／報告 | 全部保持，重用碼不轉移、清空或重算。 |
| Google／教師身份 | auth_instance UUID、teachers、google_identities、main／picker credential 密文 | 完全保留，FK／UUID／密文不得因初始化改變。 |

新增不可逆 trigger：CLOSED→非 CLOSED 拒絕；保護 code、id、course_id 不被更新為別的歸屬。沿用既有活動 CLOSED 不重開與同堂單未結束活動 trigger。新約束的具體錯誤映射見契約；不以只禁用按鈕代替。

## 狀態與確認

- 課堂：OPEN→CLOSED，無反向；第一次關課更新 closed_at／state_version，一併結束 PREPARING／LIVE；重送只回原 CLOSED，不再更新。
- 碼：有效占用是 OPEN 投影；同一 commit 退出索引即釋放，立即可由其他課程／教師重用，無定時回收工作。
- 學生：UNJOINED→OPEN_MEMBER→CLOSED_NOTICE；僅重新輸入碼＋組別可加入下一堂。grant／proof 實體可以保留，CLOSED 時內容權限為零。
- 結算：activity CLOSED 不代表 result ready；教師回填只接受已結算快照，pending 仍 RESULT_NOT_READY。
- 加入解析在 BEGIN IMMEDIATE 後發生，成功寫入固定目標；若未來拆成預覽／確認，必須攜帶固定目標並重驗，禁止同次確認重新解析到新堂。

## 009 升級流程（後續實作，尚未執行）

1. 停止所有舊版服務／連線，由操作者依既有備份方式保護 DB 與原私有 key。禁止舊版與 009 同時寫同一 DB；程式回退也不能把已重複歷史碼強塞回全域 UNIQUE。
2. 在應用接受請求前檢查 schema：新 DB 建新 schema；已完成 009 且約束正確者驗證後 no-op；舊 007／008 code 全域唯一者進升級；未知／不完整 schema 明確停止，不能把 marker 當唯一判斷。
3. 專用連線外層 finally 管理 foreign_keys：確認當下無交易，暫設 OFF，再 BEGIN IMMEDIATE。新 DB 不需要重建，維持原 core＋Google 原子初始化；舊 DB 既有 Google 身份也必須在同次 bootstrap 成功前驗證，不回退 2d4f421 的原子保護。
4. 盤點 classrooms 的所有 index／trigger／view，以及其他表上引用 classrooms 的 trigger／view；保存、辨識後依相依順序暫拆會阻礙重建的項目。若有未知定義無法可靠還原，abort，不能忽略、關 writable_schema 或自行丟棄。
5. 建新暫存 classrooms 表，逐欄 copy 原列，保留全部值與原 FK（包括 current_activity_id 的循環關係）。不先 rename 舊表。移除舊表後將新表 rename 為 classrooms，恢復依賴物件、新部分唯一索引與不可逆 trigger；沒有任何 CASCADE 資料刪除效果可被接受。
6. 驗證全欄位／列數、全部 child FK、無 OPEN 重碼、各 trigger 完整、auth_instance UUID／Google 密文及其他歷史指紋相同，執行 foreign_key_check 與 integrity_check；全部成功才寫 schema marker 並 commit。
7. 任一步故障 rollback，標記／表／索引／Google bootstrap 同時回復；恢復 foreign_keys=ON 並確認、關閉專用連線。若恢復失敗也不得提供服務。一般 g.db 連線繼續強制 ON，不得把 FK OFF 連線流入 request。
8. 再啟動、再次 init-db 都是冪等驗證，不重建／重設時間／UUID。測試需逐步故障注入、重啟兩次及多程序初始化互斥；另一初始化等待後須於鎖內重讀版本，不執行第二次 copy。

此為待實作演算法而非 migration script，本輪沒有執行以上任何 DB 操作。SQLite 官方流程與選擇見 [research R02](research.md#r02-非破壞-schema-升級)。

## 相容界線

002 非 CLASSROOM_MODE 路徑保持原 schema／學生結果規則；004／007／008 的既有 ID、API 欄位及教師內容相容。學生關課後恢復 204／結果可讀是本輪刻意變更，舊測試預期必須更新為拒絕，不能同時保留舊學生授權例外。教師歷史 code 仍可回傳，但顯示「已失效，可能重用」，不作加入入口；此為本次教師文案設計，待介面核對。
