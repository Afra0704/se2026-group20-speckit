"""Google API boundary with an injectable official-client-shaped service.

No application identity, persistence, preview confirmation, or write orchestration
belongs here. All operations must be called after server-side authorization.
"""
from copy import deepcopy
from dataclasses import dataclass
import random
import re
import time
from urllib.parse import parse_qs, urlsplit


class GatewayError(RuntimeError):
    def __init__(self, code, *, http_status=503, write_outcome=None):
        self.code = code
        self.http_status = http_status
        self.write_outcome = write_outcome
        # Never embed Google's raw exception, URLs, credentials, or answer data.
        super().__init__(code)


def parse_sheets_url(url):
    """Extract an ID and optional gid, without fetching user-provided URLs."""
    try:
        parts = urlsplit(url if isinstance(url, str) else "")
        if parts.scheme != "https" or parts.netloc != "docs.google.com":
            raise ValueError
        match = re.fullmatch(r"/spreadsheets/d/([A-Za-z0-9_-]+)(?:/edit)?/?", parts.path)
        if not match:
            raise ValueError
        query_gids = parse_qs(parts.query, keep_blank_values=True).get("gid", [])
        fragment_gids = parse_qs(parts.fragment, keep_blank_values=True).get("gid", [])
        gids = query_gids + fragment_gids
        if (len(query_gids) > 1 or len(fragment_gids) > 1
                or any(not re.fullmatch(r"[0-9]+", gid) for gid in gids)
                or (gids and len({int(gid) for gid in gids}) != 1)):
            raise ValueError
        return match[1], int(gids[0]) if gids else None
    except (ValueError, TypeError):
        raise GatewayError("INVALID_SHEETS_URL", http_status=400) from None


GRID_FIELDS = ("sheets(properties(sheetId,title,gridProperties),merges,"
               "data(startRow,startColumn,rowData(values(userEnteredValue,formattedValue,"
               "userEnteredFormat))))")


def _source_id(spreadsheet_id):
    if not isinstance(spreadsheet_id, str) or re.fullmatch(r"[A-Za-z0-9_-]+", spreadsheet_id) is None:
        raise GatewayError("INVALID_SHEETS_URL", http_status=400)


def _sheet_id(sheet_id):
    if type(sheet_id) is not int or sheet_id < 0:
        raise GatewayError("INVALID_REQUEST", http_status=400)


def _anchor(anchor):
    if (not isinstance(anchor, (tuple, list)) or len(anchor) != 2
            or any(type(v) is not int or v < 0 for v in anchor)):
        raise GatewayError("INVALID_REQUEST", http_status=400)


@dataclass(frozen=True)
class AnchorWrite:
    question_id: str
    row: int
    column: int
    text: str


class SheetsGateway:
    def __init__(self, service, *, sleep=time.sleep, jitter=random.random):
        self._service = service
        self._sleep = sleep
        self._jitter = jitter

    def _read(self, make_request):
        for attempt in range(3):
            try:
                return make_request().execute(num_retries=0)
            except Exception as error:
                status = getattr(getattr(error, "resp", None), "status", None)
                if status in (429, 500, 502, 503, 504) and attempt < 2:
                    self._sleep(2 ** attempt + self._jitter())
                    continue
                if status == 401:
                    code, http = "GOOGLE_REAUTH_REQUIRED", 503
                elif status == 403:
                    code, http = "SOURCE_READ_FORBIDDEN", 403
                elif status == 404:
                    code, http = "SOURCE_NOT_FOUND", 404
                elif status == 429:
                    code, http = "GOOGLE_RATE_LIMITED", 503
                else:
                    code, http = "SOURCE_READ_UNAVAILABLE", 503
                raise GatewayError(code, http_status=http) from None

    def list_worksheets(self, spreadsheet_id):
        _source_id(spreadsheet_id)
        response = self._read(lambda: self._service.spreadsheets().get(
            spreadsheetId=spreadsheet_id, fields="sheets(properties(sheetId,title))"))
        try:
            return [{"sheet_id": s["properties"]["sheetId"], "title": s["properties"]["title"]}
                    for s in response.get("sheets", [])]
        except (AttributeError, KeyError, TypeError):
            raise GatewayError("SOURCE_READ_UNAVAILABLE") from None

    def read_sheet(self, spreadsheet_id, sheet_id):
        _source_id(spreadsheet_id)
        _sheet_id(sheet_id)
        response = self._read(lambda: self._service.spreadsheets().getByDataFilter(
            spreadsheetId=spreadsheet_id,
            body={"dataFilters": [{"gridRange": {"sheetId": sheet_id}}], "includeGridData": True},
            fields=GRID_FIELDS))
        try:
            sheets = [s for s in response.get("sheets", []) if s["properties"]["sheetId"] == sheet_id]
        except (AttributeError, KeyError, TypeError):
            raise GatewayError("SOURCE_READ_UNAVAILABLE") from None
        if not sheets:
            raise GatewayError("SOURCE_NOT_FOUND", http_status=404)
        if len(sheets) != 1:
            raise GatewayError("SOURCE_READ_UNAVAILABLE")
        return deepcopy(sheets[0])

    def read_anchor_values(self, spreadsheet_id, sheet_id, anchors):
        """Read raw entered types, using current server-reidentified anchors.

        The export service must first validate current source structure. This
        helper cannot establish that old coordinates still identify the same item.
        """
        if not isinstance(anchors, (list, tuple)) or not anchors:
            raise GatewayError("INVALID_REQUEST", http_status=400)
        for anchor in anchors:
            _anchor(anchor)
        sheet = self.read_sheet(spreadsheet_id, sheet_id)
        grid = sheet["properties"].get("gridProperties", {})
        for row, col in anchors:
            if (row >= grid.get("rowCount", float("inf"))
                    or col >= grid.get("columnCount", float("inf"))):
                raise GatewayError("SOURCE_CHANGED", http_status=409)
        values = {}
        for block in sheet.get("data", []):
            for row, cells in enumerate(block.get("rowData", []), block.get("startRow", 0)):
                for col, cell in enumerate(cells.get("values", []), block.get("startColumn", 0)):
                    coordinate = (row, col)
                    entered = cell.get("userEnteredValue", {})
                    if coordinate in values and values[coordinate] != entered:
                        raise GatewayError("SOURCE_READ_UNAVAILABLE")
                    values[coordinate] = entered
        return {tuple(anchor): deepcopy(values.get(tuple(anchor), {})) for anchor in anchors}

    def write_unit(self, spreadsheet_id, sheet_id, writes):
        """Send one question's pending items; return no success classification.

        Call only after ownership, settled snapshot, complete membership, fresh
        confirmed bindings and source lease checks. This low-level function does
        not authorize writes. Read-back and durable operation status belong to
        the export service, including after an unknown outcome.
        """
        _source_id(spreadsheet_id)
        _sheet_id(sheet_id)
        if not isinstance(writes, (list, tuple)) or not writes:
            raise GatewayError("INVALID_REQUEST", http_status=400)
        seen = set()
        question_ids = set()
        data = []
        for write in writes:
            if not isinstance(write, AnchorWrite):
                raise GatewayError("INVALID_REQUEST", http_status=400)
            _anchor((write.row, write.column))
            if (not isinstance(write.question_id, str) or not write.question_id.strip()
                    or not isinstance(write.text, str) or not write.text.strip()
                    or (write.row, write.column) in seen):
                raise GatewayError("INVALID_REQUEST", http_status=400)
            question_ids.add(write.question_id)
            seen.add((write.row, write.column))
            data.append({"dataFilter": {"gridRange": {"sheetId": sheet_id,
                "startRowIndex": write.row, "endRowIndex": write.row + 1,
                "startColumnIndex": write.column, "endColumnIndex": write.column + 1}},
                "majorDimension": "ROWS", "values": [[write.text]]})
        if len(question_ids) != 1:
            raise GatewayError("INVALID_REQUEST", http_status=400)
        try:
            self._service.spreadsheets().values().batchUpdateByDataFilter(
                spreadsheetId=spreadsheet_id,
                body={"valueInputOption": "RAW", "includeValuesInResponse": False,
                      "data": data}).execute(num_retries=0)
        except Exception as error:
            status = getattr(getattr(error, "resp", None), "status", None)
            known_failure = status in (400, 401, 403, 404, 429)
            code, http = {
                400: ("INVALID_REQUEST", 400),
                401: ("GOOGLE_REAUTH_REQUIRED", 503),
                403: ("SOURCE_WRITE_FORBIDDEN", 403),
                404: ("SOURCE_NOT_FOUND", 404),
                429: ("GOOGLE_RATE_LIMITED", 503),
            }.get(status, ("SOURCE_WRITE_UNCERTAIN", 503))
            raise GatewayError(code, http_status=http,
                               write_outcome="failed" if known_failure else "unknown") from None


def build_google_service(credentials):
    """Use official libraries after 002 installs the shared locked dependencies.

    The caller loads a teacher's authorized credentials from repo-external files.
    No implicit refresh/replay is allowed in this transport: expired credentials
    must be refreshed explicitly before constructing it, before any write starts.
    """
    try:
        import httplib2
        from google_auth_httplib2 import AuthorizedHttp
        from googleapiclient.discovery import build
    except ImportError:
        raise GatewayError("GOOGLE_DEPENDENCIES_MISSING") from None
    if not credentials.valid:
        raise GatewayError("GOOGLE_REAUTH_REQUIRED")
    try:
        return build("sheets", "v4", http=AuthorizedHttp(credentials,
            http=httplib2.Http(timeout=30), refresh_status_codes=(), max_refresh_attempts=0),
            cache_discovery=False)
    except Exception:
        raise GatewayError("SOURCE_READ_UNAVAILABLE") from None
