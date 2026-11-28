# 013 驗證紀錄

2026-11-28（台北時間），Codex 在 Issue #18 本機工作樹驗證。基底 a8c7b8f，包含已合併 #17。使用 Python 3.13 既有虛擬環境、Node 及 pytest fixtures 的暫存資料庫。

| 驗證 | 預期 | 實際 |
|---|---|---|
| 變更前 Node 送答、分頁與在線範圍 | 原行為通過 | 31 項通過 |
| 變更前 Python 送答契約及競態 | 原行為通過 | 5 項通過 |
| US1／US2／US3 完整 Node | 逐欄驗空、本題狀態、原樣重試、A1 衝突、晚回及不合契約的成功回應通過 | 95 項通過 |
| Python 送答契約及競態 | 拒絕不受理、保留原字串 | 6 項通過 |
| 另跑新版舊操作重送整合案例 | 201 重送不增受理，舊操作不覆蓋目前有效答案 | 1 項通過 |
| 完整 Python | 送答、課堂、教師及回填回歸 | 621 項、98 子測試通過，1 項跳過，退出碼 0 |

前端新增測試在實作前捕捉 A1 無本題提示，以及缺少逐欄驗空行為。實作後已重驗。

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$suite = Get-ChildItem tests/*.test.cjs | ForEach-Object FullName
node --test $suite
python -m pytest tests/contract/test_quiz_submission.py tests/integration/test_classroom_submission_races_009.py -q -p no:cacheprovider
python -m pytest tests -q -p no:cacheprovider --tb=short
```

真人驗收待完成。本工作階段沒有配置 Google Web client 憑證，未以一位教師和兩組學生操作。鍵盤、窄視窗及輔助技術仍須按驗收指南真人核對。

## 2026-11-28 #15 整合工作樹重新驗證

使用者授權在codex/013-site-branding融入本PR f300a0b。保留同學原送答／pending／A1程式，另接品牌底板及相容樣式。完整Python628通過、98子測試通過、1Windows POSIX skip；Node95通過。隔離Chrome13頁四寬度52組、2鍵盤及2本題送答提示案例通過，詳見[整合驗證](delivery-check.md)。這些為本次實際重跑，不將前述同學工作樹結果當成本分支證據。教師兩組真人、受控未知結果真人及更新後時序圖複核仍待完成，T017–T019不代勾。

後續同日，使用者完成本次整合18項人工案例，涵蓋真教師登入、兩組學生、欄位驗空、每題提示、原樣重試、受控回覆遺失／限流／503／A1／401／409及跨活動晚回，逐項回報通過。詳見[人工驗收紀錄](integration-manual-acceptance.md)，區分真請求、合成回應與尚未重驗矩陣。本次未人工覆蓋全部pending交接／複製、同scope新pending競態等情境，不能只憑18/18勾完整交付；A1圖複核及Converge仍未完成。

### 最後交付檢核（2026-11-28）

已完成本次Analyze及Converge核對，詳見[交付檢核與補測指南](delivery-check.md)。12/12 FR／SC有任務及程式／測試對應，無新增規格衝突或功能程式阻斷缺陷；重跑Python7與Node36通過，PlantUML三圖語法及既有PNG簽章正常。Converge結果tasks_appended，追加T020未決操作真人三項及T021 A1圖複核，T017–T019保持未完成。補齊自動檢查不等同已交付；未修改產品、DB或Google設定，也未操作遠端PR／Issue。

### 最後證據補齊

同日使用者逐項回報S1–S3通過，再回報同學已審核，詳見delivery-check.md最後段及integration-manual-acceptance.md。pending的F5、複製、取消／確認重新加入已取得人工證據；原草稿F5消失如實保留，屬#15範圍。更新圖審不代填姓名或GitHub review。最後Converge無剩餘缺口、未追加新任務，隨後交付整理勾選T017–T021；全21項Issue18任務完成。18原案例＋3補測均為使用者回報通過，不將受控回應當真服務故障，不推定所有額外測試矩陣皆人工執行。產品未改，沿用原完整及相關測試結果，遠端PR／Issue仍未操作。

## PR26原分支完整重驗與文件同步

2026-11-28，使用者明確要求同步PR26、正式review、合併及關閉Issue18。建立獨立codex/docs-issue18-delivery工作樹，以PR26原head f300a0b為基底，只增加本功能5份交付文件，不合入#15程式或修改日常DB／Google憑證。

本次實際重跑PR原程式：Python621 passed、1 skipped、98 subtests passed（116.12秒）；Node95 passed、0 failed／skipped（387.21毫秒）。Python命令為設定本工作樹src至PYTHONPATH後，使用既有Python3.13虛擬環境執行pytest tests -q -p no:cacheprovider --tb=short；Node遍歷tests/*.test.cjs。1項skip仍為Windows不適用POSIX跨時區環境，不記通過。

逐檔SHA256比對http.py、quiz/submission_gateway.py、quiz/repository.py、static/quiz-submission.js及static/student-room.js與3f55492整合版相同。人工21案例保留實際整合版本，不將#15首頁／品牌證據當成PR原程式功能；#18的原分支完整回歸與整合回歸各自成立。提交前git diff --check通過。GitHub review、merge及Issue狀態以遠端可核實紀錄為準。
