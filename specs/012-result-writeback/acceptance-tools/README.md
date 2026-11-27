# 整合驗收的受控故障工具

只供獨立QA啟動器明確載入，正常產品create_app不會載入這些工具。本輪真人操作的來源為兩份測試Sheets副本；不撤銷真正Google grant，不改日常DB或產品writer。

- auth_fault.py：在gateway邊界回SHEETS_REAUTH_REQUIRED，只讀教師ID／revision；新連接revision後解除。標記只存ID／revision，不含token或密文。
- write_fault.py：第一次write_unit仍委派原writer，第二次模擬未送出的結果未知及本request回讀中斷；故障一次性，新的gateway可恢復讀取。audit只記格數，不記答案、來源ID或憑證。只有明確確認預覽後才會呼叫原writer。
- check_auth_fault.py／check_write_fault.py：使用既有google_support／WritableSheets合成fixture，驗證不改密文、只在新授權後解除、原同意／新衝突及最終[2,1]寫入批次。

PowerShell從repo根目錄執行合成自測：

```powershell
$env:PYTHONPATH="$PWD/src;$PWD/tests;$PWD/tests/integration"
.venv/Scripts/python.exe -m pytest specs/012-result-writeback/acceptance-tools/check_auth_fault.py specs/012-result-writeback/acceptance-tools/check_write_fault.py -q
```

本機ignored QA啟動器載入順序為create_app→install_auth_fault(marker)→install_write_fault(marker,audit)，不自動arm。故障檔置於QA目錄；未arm時沿用原gateway。arm-write初始JSON為attempts=0、injected=false、teacher_id=null，audit為actual_batches=[]、uncertain_batches=[]、blocked_readbacks=0；完成後停用標記、保留audit。不可在日常服務載入，亦不可重置既有場景audit來掩蓋重送。

本輪人工與受控證據詳見[整合驗收](../../../docs/issues-19-20-manual-acceptance.md)。實際重啟及真副本核對是使用者回報；合成測試不取代這些觀察。
