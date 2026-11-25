# 離線講義測試資料

`sheets_layouts.json` 是人工合成的 Google Sheet resource，沒有帳號、憑證或學生資料。
`build_layouts.py` 可重產 JSON；測試只讀 JSON，不連網或修改來源。

| 範例 | 預期主題號數／作答項目數 | 觀察 |
| --- | --- | --- |
| single | 1／1 | 答案跨欄合併，原值是公式，保留原型別與格式 |
| mixed | 2／3 | 題號跨列、(1)／（2）標號、真正空白尾格、空白分隔列及後續單題 |
| moved | 2／3 | GridData 起始列加 3、起始欄加 2，答案寬度增加；所有範圍同步位移 |
| missing_header | 拒絕 | HEADER_MISSING |
| duplicate_header | 拒絕 | HEADER_AMBIGUOUS |
| duplicate_question | 拒絕 | DUPLICATE_QUESTION |
| duplicate_subitem | 拒絕 | DUPLICATE_SUBITEM |
| answer_overlap | 拒絕 | ANSWER_OVERLAP |
| ambiguous_answer | 拒絕 | ANSWER_AMBIGUOUS |

尚不代表已核對完整課程範本的 GridData／merges，真實來源須另行驗收。
