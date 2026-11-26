# 003 PR #9／009 技術交接檢查（2026-11-26）

依使用者「同學已上傳003 PR 可以先檢查後再開始」先檢查，再開始009；此為使用者指定的T003具體核對方式，不虛構同學逐條簽核。

- PR：https://github.com/Afra0704/se2026-group20-speckit/pull/9；作者itsusername15。
- 固定head：31b0e23c8938b7e629c7173238145a927ba6a8f3；base master：39d6275e0b3f005957764327c16c443d7a60825e。
- base是PR #7的合併commit；其受控檔案樹與本機HEAD2d4f421無差異，沒有自行合併或移動本機分支。
- gh CLI未安裝；沙箱HTTP無法解析GitHub，經工具核准唯讀API及git fetch。只抓物件／讀PR，無留言、核准、合併、checkout或push。
- git archive解出固定head到tmp/pr9-review/source，PYTHONPATH只指該副本src，以原venv執行quiz_schema、quiz_settlement、quiz_replay、activity_cutoff、classroom_results五份測試：14 passed in5.89s，exit0。所有DB由tests在暫存目錄建立，非操作者DB；不是完整PR複審或真人驗收。

## 已核對的交接點

| 邊界 | PR現況／009接續方式 |
| --- | --- |
| 受理 | submission_gateway共用write_transaction，submission_context for_replay區分新送答／原收據。009保留操作識別、原payload、同交易及排序邏輯；只調整課堂OPEN權限。 |
| 結束 | teacher.transition在同交易queue，classroom_routes在commit後try_pending；009重送關課不重transition／queue，但原pending可依003恢復入口處理。 |
| 結果 | try_pending可能另開write_transaction。009不得把它包進read transaction；若採用正式PR，先做授權預檢、結束該read，再恢復pending，最後開新read重新驗原堂OPEN並組DTO。教師快照同樣避免巢狀寫交易。 |
| 可見性 | PR仍依舊D16允許關課後proof恢復，與009最新已確認禁讀不同；屬下一輪009變更，不能把PR按舊規格的綠燈當009完成。 |
| 新組員歷史 | PR允許OPEN課堂新組員依D06看同堂舊活動，與009相容，應保留。 |
| 前端 | PR新增QuizSubmission.attach與Idempotency-Key、逐小題結果、pending／unavailable狀態；009獨立學生頁須保留這些介面，不能以舊送答實作覆寫正式003。 |
| schema | PR只附加quiz表且保留core／Google同交易初始化；009重建classrooms時須連quiz表／sqlite_sequence／settlement不可變資料一起保留。 |

## 編號衝突與限制

003 PR把「OPEN新組員看歷史」命名D22；本機009的「碼重用／關課禁讀」也暫稱D22。兩者行為可組合，但整合時須區分003-D22／009-D22並統一新編號，不能覆寫任何確認紀錄。本輪先用功能路徑及明確行為區分，不自行回改同學PR文件。

003排序／去重／結算演算法及其PR由itsusername15負責；009本聊天室負責碼、schema保留升級、學生OPEN授權及入口，必要gateway接線只限這些邊界。PR尚未合併，不把正式003拷入本工作樹；先在既有base實作009，後續在隔離副本驗與PR9的接線，不自動合併／提交。正式PR與009整合、真人及真Sheets驗收仍需另列證據。

## 結論

具體接口足以開始009的獨立實作；已知差異納入009設計，不重寫同學算法。沒有把14個測試通過當全PR批准，也沒有宣稱同學已具名批准每個009修改。
