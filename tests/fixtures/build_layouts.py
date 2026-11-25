"""Regenerate synthetic Sheets fixtures, without credentials or real student data."""
import copy
import json
from pathlib import Path


def layout(grouped=False, dr=0, dc=0, width=2):
    rows = []
    merges = []

    def cell(r, c, value):
        while len(rows) <= r:
            rows.append({"values": []})
        values = rows[r]["values"]
        while len(values) <= c:
            values.append({})
        entered = value if isinstance(value, dict) else {"stringValue": value}
        values[c] = {"userEnteredValue": entered, "formattedValue": str(next(iter(entered.values()))),
                     "userEnteredFormat": {"wrapStrategy": "WRAP"}}

    def merge(r, er, c, ec):
        merges.append({"sheetId": 7, "startRowIndex": r + dr, "endRowIndex": er + dr,
                       "startColumnIndex": c + dc, "endColumnIndex": ec + dc})

    cell(3, 1, " 題號 ")
    cell(3, 2, "題目")
    cell(3, 5, "作答")
    merge(3, 4, 2, 5)
    end = 6 + width if grouped else 5 + width
    merge(3, 4, 5, end)
    cell(4, 1, {"numberValue": 1})
    cell(4, 2, "電腦的大腦？")
    merge(4, 5, 2, 5)
    if grouped:
        merge(4, 6, 1, 2)
        cell(4, 5, "(1)")
        cell(5, 5, "（2）")
        cell(5, 2, "系統軟體？")
        merge(5, 6, 2, 5)
        merge(4, 5, 6, end)
        merge(5, 6, 6, end)
        cell(7, 1, "2")
        cell(7, 2, "資料結構？")
        merge(7, 8, 2, 5)
        merge(7, 8, 5, end)
    else:
        cell(4, 5, {"formulaValue": "=1+1"})
        merge(4, 5, 5, end)
    return {"properties": {"sheetId": 7, "title": "合成學習單"}, "merges": merges,
            "data": [{"startRow": dr, "startColumn": dc, "rowData": rows}]}


def build():
    layouts = {"single": layout(), "mixed": layout(True), "moved": layout(True, 3, 2, 3)}
    for name in ("missing_header", "duplicate_header", "duplicate_question", "duplicate_subitem",
                 "answer_overlap", "ambiguous_answer"):
        layouts[name] = copy.deepcopy(layouts["mixed"])
    layouts["missing_header"]["data"][0]["rowData"][3]["values"][1] = {}
    layouts["duplicate_header"]["data"].append({"startRow": 20, "rowData": copy.deepcopy(
        layouts["mixed"]["data"][0]["rowData"][3:4])})
    layouts["duplicate_question"]["data"][0]["rowData"][7]["values"][1] = {
        "userEnteredValue": {"numberValue": 1}}
    layouts["duplicate_subitem"]["data"][0]["rowData"][5]["values"][5] = {
        "userEnteredValue": {"stringValue": "（1）"}}
    overlap = layouts["answer_overlap"]
    overlap["merges"] = [m for m in overlap["merges"] if not (
        m["startColumnIndex"] == 6 and m["startRowIndex"] in (4, 5))]
    overlap["merges"].append({"sheetId": 7, "startRowIndex": 4, "endRowIndex": 6,
                              "startColumnIndex": 6, "endColumnIndex": 8})
    ambiguous = layouts["ambiguous_answer"]
    ambiguous["merges"] = [m for m in ambiguous["merges"] if not (
        m["startColumnIndex"] == 6 and m["startRowIndex"] == 4)]
    return layouts


if __name__ == "__main__":
    Path(__file__).with_name("sheets_layouts.json").write_text(
        json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
