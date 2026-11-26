# 008 Picker／Sheets 授權邊界（計畫）

## 三類資格

| 資格 | 用途／保存 |
| --- | --- |
| 教師Google登入 | 原007 main Web client的OIDC→原teacher/grant；學生不需要。 |
| 本人Sheets讀寫 | 原007 google_sheets_credentials、持久refresh與顯式lease刷新；只在後端、不可刷新快照供Sheets SDK。 |
| Picker選檔 | 同project專用Picker Web client，online-only窄cache；唯一允許交瀏覽器的短期access token，不當成教師登入或Sheetscredential。 |

專用Picker client須不同main，client/API key/App ID同project；不是不同client即可隔離scope，非增量及實際scope驗證才是交付防線。

## 開始及callback

使用import-flow的authorize POST，原purpose=sheets＋DB sidecar kind=picker；共用 `/auth/google/callback`。provider、configuration、validate_current、finish都以sidecar判斷client/profile，不信前端kind或callback query。attempt＋sidecar＋flow連結同短交易。

請求scope：`openid email profile https://www.googleapis.com/auth/drive.file`；PKCE S256／nonce，`access_type=online`、`include_granted_scopes=false`，不強制prompt=consent/select_account。login_hint=sub只提示，後端仍驗簽章、issuer、aud/azp=專用client、iat/exp/nonce、sub=原教師。標準Google issuer驗後canonical化。

token response scope必須存在且可正規化；required=allowlist=上述四項（email/profile官方別名正規化後比對）。額外spreadsheets、drive、drive.readonly、metadata或任何未知scope回PICKER_SCOPE_UNSAFE，缺任何required回PICKER_SCOPE_REQUIRED，不能拿requested冒充。scope-change Warning只在原provider局部處理，不重送code、不放寬全域旗標。

有效窄cache可重用至Google expiry剩60秒；回傳ID-token只在當次驗證後丟棄，不存Picker refresh。重連產生新generation，先前ticket立即不再可接受。取消／錯帳號／驗scope失敗不覆寫原有效cache或007 Sheetscredential。

沒有sidecar的舊007 attempt只允許main client；若Picker client、已綁flow的attempt或context缺失／不一致，拒絕，不fallback或誤送sheets_service.connect。原007 login/sheets保持，新增kind不重建原purpose CHECK。

## POST token交付

`POST /teacher/workspace/imports/<flow_id>/picker/token`：CSRF、cloud flow、原current grant、同owner/course、flow TTL、cache binding/scope/expiry均有效才回200：

```json
{"ticket_id":"ticket-example","access_token":"<短期窄token，僅本端點>","expires_in":900,"ticket_expires_in":300,"api_key":"<受限制的瀏覽器key>","app_id":"<project-number>"}
```

expires_in以當下Google真實expiry計算；ticket_expires_in亦受flow/Googleexpiry-30限制，例中數字僅格式例，不是固定Google期限。回應no-store、Referrer-Policy:no-referrer，只同源、不得開CORS *；不回refresh token、ID-token、client secret、main Sheets token、完整credential或錯誤raw body。

JS只在記憶體把access token交官方Picker，單選／Sheets MIME／不提供上傳。關閉、取消、離頁、選定或錯誤時解除本地引用；不記錄到console或把token放URL、DOM data attribute、Storage、cookie。第三方腳本僅必要Google庫，不加分析／廣告。API key是受限制的前端設定，不能代替使用者OAuth。

來源限制與007全站no-referrer需一起處理：僅固定 `workspace.import_page`（乾淨flow URL、沒有OAuth query）HTML允許 `Referrer-Policy: strict-origin-when-cross-origin`，讓跨站Google請求只帶origin；callback、token POST、其他敏感回應仍no-referrer/no-store。由原http.privacy的endpoint allowlist明確設定，不能接受query/header要求任意放寬。測試驗跨站Referer無flow路徑／憑證，並真實核對Picker iframe來源限制；不以移除API key限制解錯。

這是007後端token規則的**明列限用途擴充**：只有經後端同人／scope驗證的Picker窄token可交付，原broadtoken仍禁止。Googletoken在真正過期前仍可作bearer，ticket／本地清理不會讓Google提早失效，也不保證它只涵蓋本次一檔。取消不呼叫revoke，避免撤同project其他授權。

## 選檔返回與外部驗權

`POST .../picker/selection`只接file_id/ticket_id。以同短交易claim ticket與flow，驗credential generation/revision後外網使用後端同一窄cache呼叫Drive files.get，限制fields為id/name/mimeType/trashed/capabilities.canEdit；不能信前端metadata。

須為Google Sheets且未trashed，實際後端可存取；canEdit=false不假裝可回填，可繼續唯讀匯入並保留原write forbidden行為。後續讀分頁／預覽／回填均走原本人Sheetsgateway；若未連接，只在該flow續接Sheets授權，不借Picker token替代持久回填授權。

metadata外網後finalize還須核對ticket所綁credential generation/revision仍為目前cache，且ticket是自己的claim；reconnect先完成則丟棄舊selection晚回，不只在送出前驗一次。

元資料與Sheets查詢固定Google端點／官方client、bounded timeout、num_retries=0，不接受任意來源URL的HTTP代理。無權限／來源刪除按安全code回報。外網後再驗flow/current grant/claim，錯帳號／晚回不能保存。

## Cloud與真實驗證gate

同原project啟用Picker API、Drive API，保留Sheets API；新增Picker Web client、固定callback與JS origin；建立website/API限制key，App ID=project number。測試使用者及同意scope由操作者準備，詳quickstart。

官方GIS對false有明確敘述，沿用Python Flow的直接OAuth參數是協定推論；必須真實驗main broad grant已存在、跨main/Picker client時token仍只四scope。未完成不能宣稱cloud可交付；異常failclosed，不能把額外scope默默接受。受控fake不是此真實證據。
