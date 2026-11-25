"""Recorded, failure-injectable Sheets substitute; never uses credentials."""
import copy

from guided_notes.db import connection
from guided_notes.notes.sheets_gateway import GatewayError
from test_import_routes import MutableSheets


class WritableSheets(MutableSheets):
    def __init__(self):
        super().__init__()
        self.writes = []
        self.fail_at = None
        self.unknown_applies = False
        self.uncertain = False
        self.readback_error = False
        self.write_hook = None

    def put(self, row, col, value):
        block = self.sheet["data"][0]
        rows = block["rowData"]
        row -= block.get("startRow", 0)
        col -= block.get("startColumn", 0)
        while len(rows) <= row:
            rows.append({"values": []})
        cells = rows[row].setdefault("values", [])
        while len(cells) <= col:
            cells.append({})
        cells[col]["userEnteredValue"] = copy.deepcopy(value)

    def read_sheet(self, *args):
        if self.writes and self.readback_error:
            self.readback_error = False
            raise GatewayError("SOURCE_READ_UNAVAILABLE")
        return super().read_sheet(*args)

    def write_unit(self, spreadsheet_id, sheet_id, writes):
        assert not connection().in_transaction
        assert sheet_id == 7
        assert len({w.question_id for w in writes}) == 1
        self.writes.append(copy.deepcopy(writes))
        if self.write_hook:
            self.write_hook()
        error = self.fail_at == len(self.writes)
        if not error or self.unknown_applies:
            for write in writes:
                self.put(write.row, write.column, {"stringValue": write.text})
        if error:
            unknown = self.unknown_applies or self.uncertain
            raise GatewayError("SOURCE_WRITE_UNCERTAIN" if unknown else "SOURCE_WRITE_FORBIDDEN",
                               write_outcome="unknown" if unknown else "failed")
