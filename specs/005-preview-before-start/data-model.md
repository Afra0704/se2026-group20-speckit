# Phase 1：資料模型與狀態

沿用既有表，不新增實體或重複 phase 欄位。

| 實體 | 本次規則 |
| --- | --- |
| classrooms | id、state、current_activity_id、state_version；新建時發布 PREPARING 指標並增加版本。 |
| classroom_activities | 關聯 activity_id/classroom_id、title、created_at/started_at/closed_at；title 已存在。 |
| activities | id、phase、phase_version、import_id/version；PREPARING 及 LIVE 都算未結束。 |
| questions/items | 沿用固定題號、識別、順序與提交單位；不改 catalog。 |
| classroom_groups/memberships | 不變；換活動保留同堂組別。 |

| 操作 | 前提 | 結果 |
| --- | --- | --- |
| 建立 | OPEN，無未結束活動 | PREPARING；設定目前活動，學生可看不可填。 |
| 開始 | OPEN，目標為目前 PREPARING，無其他未結束活動 | LIVE，記 started_at、保留同一目前指標並更新版本。 |
| 結束準備 | 授權教師、OPEN、目前 PREPARING | CLOSED，記 closed_at；started_at 仍空值，無答案／順位。 |
| 結束搶答 | 授權教師、OPEN、目前 LIVE | CLOSED，記 closed_at；結果可用性仍依 provider。 |
| 關課 | 授權教師、OPEN、confirm=true | 所有關聯未結束活動及課堂 CLOSED，不刪資料。 |
| 重開 CLOSED | 任意 | 拒絕。 |

新建活動、題目、關聯及指標全成或全敗。所有寫入沿用 BEGIN IMMEDIATE，trigger 補強關聯插入／phase 更新；新流程始終最多一個未結束活動。

使用者允許丟棄先前開發資料，本次使用空白開發 DB，不做多準備資料遷移或非目前活動的特殊結束流程。正常結束保留歷史，重跑初始化保留新資料。開發重置與執行期結束是不同操作，不在 GET 或啟動時自動刪資料。

學生狀態由同一快照組合，新增 title 以純文字呈現；不帶 blank_id、來源座標或他組資料。
