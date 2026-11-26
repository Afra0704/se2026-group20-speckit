# 007 實作與驗證紀錄

日期：2026-11-25（Asia/Taipei）；執行者：Codex。自動實作已完成，真人與協作驗收未完成。未 commit、push、建立或合併 PR。

## 起點與範圍

- 起點 commit：812037a46c244aa057769c1969a64c512092403e。實際分支已建立 codex/007-google-teacher-login；保留 005/006 原未提交程式、文件、圖表與人工 checkbox，不 reset。
- 使用者明確要求 speckit-implement 並直接完成，不再要求例行確認；此前已確認身分首頁＋Google 登入、Drive 下一輪、舊應用資料不遷移。沒有因此代填同學或 OpenSpec 的核准。
- 專用新 DB：D:/os_final/instance/classroom-007.sqlite3。建立前確認不存在，建立後 teachers=0、google_sheets_credentials=0、auth_instance=1；沒有讀取或清空 005/006 DB。DB 初始化只用記憶體內暫時 Flask secret，不寫設定、不當作啟動服務的持久 secret。
- 沒有開啟真實 Web/Desktop client、token 或 key 內容、沒有產生真實 keyfile、沒有操作 Google Cloud 或 Sheets。所有自動 OAuth／Sheets 資料為 tests 的合成資料，key/client 位於 pytest 暫存目錄。
- D20、本輪分工、新介面與新版技術圖的具名互審待補；原 005 T033/T034/T037、006 T002/T036/T037/T041/T042 保持未完成。

## 實作產物與理由

| 範圍 | 位置／行為 | 理由與證據 |
| --- | --- | --- |
| 入口與教師登入 | identity 模板、google_login/routes.py、create_app；/、/student、/teacher/login | 原生 POST＋CSRF，不依賴 JS popup；Google 正式預設，學生免 Google。 |
| Google provider | provider.py；官方 Flow／google-auth verifier | 固定 Web client／127.0.0.1 callback、S256、nonce、iss/aud/exp/iat/sub/azp；合成 RSA 簽章經官方 verifier 測正常及錯簽章。 |
| 既有身分接線 | service.py、auth.py、schema.sql | 原 TeacherContext／grants，唯一 issuer+sub；顯示信箱相同不合併；未建立第二套教師／學生權限。 |
| 一次流程與撤銷 | browser epoch/current pointer、attempt claim | 300 秒，最後開始有效；外網前 claim、外網後短交易 finalize；登出不清學生 session、晚到 cookie 不復活教師。 |
| 本人 Sheets | sheets_service.py、crypto.py、notes.gateway | 額外同意、同 sub、實際 scope、可持續 refresh；Fernet envelope 綁 purpose/owner/instance/client/generation/revision；沒有 Desktop/global fallback。 |
| 有界刷新 | 30 秒 lease、20 秒 monotonic deadline、FixedSession | 一次 token POST／至多一次必要 cert GET；不重試、不跟 redirect，外網不持 write lock，逾時只清自己的 lease。 |
| 傳輸邊界 | transport.py、原 sheets_gateway.py 狹窄映射 | 不可刷新 access-token 快照；官方 AuthorizedHttp 的 401 只有一次 HTTP；送出前過期 HTTP=0，寫入分類 failed，不把未知寫入 replay。 |
| 正式密碼停用 | teacher_routes、init_teacher、明確 test_password fixtures | 正式密碼 API 410；CLI 在詢問密碼前拒絕；舊回歸 fixture 才可用 test_password，非 TESTING 不能啟動。 |
| 文件／圖 | README、.env.example、setup、quickstart、007 三圖 | 舊啟動步驟明標歷史，新版本使用 007 DB／Web client／持久 key；Drive 下一輪。 |

## 實際自動命令與結果

- 起步新增配置／快照測試曾因模組尚未存在而失敗，建立基礎後 3 passed。
- 第一輪完整 `python -m pytest tests -q`：292 passed、98 subtests，退出碼 0。
- 補官方 SDK／刷新測試時先觀察失敗：測試端 Response 缺 prepared request、Flask fixture 晚註冊路由；修正替代端。另找到程式未重查持久 lease、失效時未清 lease，均已修正重驗。
- 官方簽章／刷新／密文等單元組合先 26 passed，擴充真實時鐘邊界後 40 passed，退出碼 0。未把錯誤測試替代端算產品故障。
- Google 授權＋匯入至學生全文／勝組 RAW 回填／部分失敗恢復：single、mixed、moved 三版型與無授權毒丸共 4 passed。第一次 single 有既有答案，測試必須依既有契約逐格確認覆寫後才通過；未放寬正式覆寫保護。
- 中間完整回歸：343 passed、98 subtests，退出碼 0。其後補 CLI、配置、時鐘與日誌測試，最終完整結果待下方記錄。
- `node --test tests/identity-ui.test.cjs tests/student-question-text.test.cjs tests/classroom-preview.test.cjs tests/classroom-sync.test.cjs tests/classroom-recovery.test.cjs tests/activity-sync.test.cjs tests/notes-ui.test.cjs`：17 tests、17 pass、0 fail，退出碼 0。
- `uv lock` 成功，39 packages；`uv sync --locked` 成功，同步專題 package，未升級其他不必要套件。預設受限 cache 無法存取，改經平台核准的 uv 命令完成；hardlink 退回 copy 是不同磁碟快取的效能提示，非測試失敗。
- 實際版本：Python 3.13.1、Flask 3.1.3、google-auth 2.63.1、google-auth-oauthlib 1.5.0、google-api-python-client 2.202.0、cryptography 50.0.2、requests-oauthlib 2.0.0、oauthlib 4.0.1。
- `git diff --check` 退出碼 0；uv.lock 的 LF→CRLF 提示不是內容錯誤。
- .specify/extensions.yml 不存在，implement/analyze/converge 的前後 hooks 無需執行。check-prerequisites 已確認功能目錄為 007，所需文件存在。

## 覆蓋範圍與限制

受控測試涵蓋兩教師首次／再次／同時登入、同 callback 只能交換一次、最後啟動有效、過期 grant 可重登入、claim 後撤銷／停用、原子故障無半教師、取消／失敗切換保留 A、成功切換撤此 browser 舊資格、其他 browser 保留、學生實際加入後教師登出仍可讀課堂。

配置驗固定 endpoints／origin／Web 類型／repo 外邊界；官方驗簽驗正常／錯簽章／nonce/aud/iss/exp/iat/sub/azp；scope 別名／額外／不足與 scope-change Warning 局部處理，不重送 code。密文覆蓋錯 key、竄改、用途／owner/client/instance/revision 錯配、新 DB 重用 teacher_id 的搬移；CLI／全域 profile 毒丸不被讀取。

刷新覆蓋無新 ID-token、有新 token 官方驗簽、錯帳號／scope、invalid_grant、暫時 timeout、晚到 invalid_grant、單調時鐘預算／UTC lease、busy、真實 connect 與舊 refresh 交錯。新 connect 不被舊結果覆寫；timeout 不誤標失效；notes 巢狀 envelope 與 Retry-After:1 保持。

保留 005/006 全文快照、同堂單活動、準備中可結束、開始才填及題組整組提交。原 Catalog／Display／Result DTO 和 TeacherContext 形狀未擴充 Google 欄位；正式 003 未接入的 QUIZ_UNAVAILABLE／未結算限制仍在，測試注入結果不是真實排名。

20 秒是結果接受／提交期限，不能保證硬中斷所有阻塞 Python I/O；逾期結果拒收。登出不能撤回已送往 Google 的寫入，仍須回讀及原恢復流程。沒有真人網路／公開部署效能保證。

## 需交給同學核對

1. google_login blueprint、Google mode require_teacher 與原 grants/current pointer 接線；TeacherContext 未改。
2. 同 Web client 的 login/sheets 雙 purpose；新的 Web client 與 repo 外 key，原 Desktop CLI 仍獨立。
3. notes.gateway 只收本人不可刷新快照；001 RAW／回讀／恢復與 003 結果契約未改。
4. Jinja 表單、教師目前身分、登出／切換／Sheets 連接；test_password 僅 TESTING。
5. diagrams/007-* 實作核對、新版圖意與 D20 OpenSpec 同步；尚未回報姓名、分工或確認結論。

## 真人與協作狀態

T056/T057/T058/T060 保持未完成；converge 追加 T062/T063 聚合追蹤。Google Cloud Web client、兩個真實教師、持久 key 仍由操作者準備，步驟見 quickstart.md。未實際測 Google 登入或本人 Sheets，不把之前 Desktop 授權成功算作本輪 Web 授權完成。沒有刪除舊憑證或講義。

## PR 草稿（僅文件，未送出）

標題：feat: add Google teacher login and per-teacher Sheets authorization

內容：首頁新增老師／學生入口；教師使用 Google 穩定身分登入並隔離課程，登出與切換撤銷此瀏覽器教師資格、保留學生資格。Sheets 經另一次本人同意，加密綁定教師與新 DB；禁止舊全域 token fallback，傳輸不隱性刷新或重送寫入。

檢視 spec.md、plan.md、contracts/、diagrams/007-*、quickstart.md 與本紀錄。自動測試結果以下方最終紀錄為準；真人 Google、兩組學生、同學互審與 D20 同步未完成。005/006 原未提交修改一併保留在目前工作樹，提交前應核對 PR 範圍與差異，不能把本 PR 當只有登入的乾淨基線。此草稿不表示可直接合併，也沒有 commit/push/建立 PR。


## 最終結果

- `.venv/Scripts/python.exe -m pytest tests -q`：**354 passed、98 subtests passed**，100.94 秒，退出碼 0。
- 前端完整指定命令：**17 tests／17 passed／0 failed**，退出碼 0。
- 先前發現的產品 lease 檢查與清理缺口均修正並納入本輪完整回歸；scope Warning、原子回滾、本人 Sheets／回填及晚到結果都有對應測試。
- T059 已完成 analyze＋append-only converge 紀錄，見 analysis.md；converge 結果為 tasks_appended，追加 T062/T063，只剩真人／互審，不宣稱整體 converged。
- 自動工作 T001–T055、T059、T061 完成；T056/T057/T058/T060/T062/T063 保持未完成，共 57/63 項。沒有重勾舊功能人工任務。
