# 013 驗收指南

使用 Python 3.13、Node、隔離測試庫及已設定 Google 教師登入的測試環境。以測試副本匯入一份有單題與多小題的講義，準備一位教師、至少兩組學生。

## 自動驗證

從專案根目錄執行。pytest 使用既有 fixtures 的暫存資料庫。

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
uv run --locked --python 3.13 python -m pytest tests/contract/test_quiz_submission.py tests/integration/test_classroom_submission_races_009.py -q
node --test tests/quiz-submission.test.cjs tests/student-room-quiz-009.test.cjs tests/student-room-009.test.cjs tests/student-presence-lifecycle.test.cjs
```

完成後執行完整 pytest 與 Node 測試。確認直接請求的權限、驗空、原文、冪等、順位及結果可見範圍。基底版本的結果與本輪結果分開。

## 真人與受控情境

1. 以鍵盤及窄視窗驗空白單題、純空白及題組漏填。逐欄提示、焦點及其他輸入符合契約，教師未看到正式受理。
2. 操作兩道題，驗證送出中、受理、重新提交、格式或階段拒絕的提示只出現在對應題目。
3. 分開模擬請求未達及伺服器受理後回覆遺失，再各測斷線恢復。未知時把答案改成另一個值，重試原操作後欄位仍顯示修改版。另以受控回應測限流、服務錯誤與晚回。
4. 有未決操作時重整原頁、複製分頁，以及取消／確認重新加入。原頁經確認交接才可重試，複製頁不承接，撤回只清本頁。教師查原正式答案與順位。
5. 分別記錄執行者、日期、提交、預期、實際及受控工具。另由組員驗證三圖與實作的責任和時序一致。
