"""Pure GridData/merges recognition. Never writes to a worksheet.

Input is one Sheet resource, including properties, data and merges. Output is
teacher-only candidate data, not a published CatalogDTO or a student response.
"""
from copy import deepcopy
from dataclasses import dataclass
import math
import re


@dataclass(frozen=True)
class GridRange:
    sheet_id: int
    start_row: int
    end_row: int
    start_column: int
    end_column: int

    @property
    def anchor(self):
        return self.start_row, self.start_column

    def contains(self, row, column):
        return (self.start_row <= row < self.end_row
                and self.start_column <= column < self.end_column)

    def overlaps(self, other):
        return (self.start_row < other.end_row and other.start_row < self.end_row
                and self.start_column < other.end_column
                and other.start_column < self.end_column)


@dataclass(frozen=True)
class RecognitionIssue:
    code: str
    sheet_id: int
    message: str
    problem_range: GridRange | None = None
    question_number: str | None = None


class RecognitionError(ValueError):
    def __init__(self, issues):
        self.issues = tuple(issues)
        super().__init__("; ".join(i.code for i in self.issues))


@dataclass(frozen=True)
class RecognizedItem:
    subitem_label: str | None
    normalized_subnumber: int | None
    prompt_text: str
    label_range: GridRange | None
    answer_range: GridRange
    observed_user_value: dict


@dataclass(frozen=True)
class RecognizedQuestion:
    display_number: str
    kind: str
    number_range: GridRange
    items: tuple[RecognizedItem, ...]


@dataclass(frozen=True)
class RecognitionResult:
    sheet_id: int
    headers: tuple[GridRange, ...]
    questions: tuple[RecognizedQuestion, ...]

    @property
    def question_count(self):
        return len(self.questions)

    @property
    def submission_unit_count(self):
        return self.question_count

    @property
    def answer_item_count(self):
        return sum(len(q.items) for q in self.questions)


def _text(cell):
    entered = cell.get("userEnteredValue", {})
    if "stringValue" in entered:
        return entered["stringValue"]
    return str(cell.get("formattedValue", ""))


def _number(cell):
    entered = cell.get("userEnteredValue", {})
    value = entered.get("numberValue", entered.get("stringValue", ""))
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return str(int(value)) if math.isfinite(value) and value > 0 and value == int(value) else None
    value = str(value).strip()
    return str(int(value)) if re.fullmatch(r"[0-9]+", value) and int(value) > 0 else None


def recognize(sheet):
    """Recognize a uniquely structured sheet; raise located issues on ambiguity.

    Coordinates are zero-based, end-exclusive. Omitted trailing CellData is still
    a valid blank when the header and merge structure uniquely identify it.
    """
    sheet_id = sheet["properties"]["sheetId"]
    if type(sheet_id) is not int or sheet_id < 0:
        raise ValueError("sheetId must be a nonnegative integer")
    cells = {}
    for block in sheet.get("data", []):
        for ri, row in enumerate(block.get("rowData", []), block.get("startRow", 0)):
            for ci, cell in enumerate(row.get("values", []), block.get("startColumn", 0)):
                if (ri, ci) in cells and cells[ri, ci] != cell:
                    raise RecognitionError([RecognitionIssue("ANSWER_AMBIGUOUS", sheet_id,
                        "讀取區域重疊且內容不一致。", GridRange(sheet_id, ri, ri+1, ci, ci+1))])
                cells[ri, ci] = cell
    merges = []
    for m in sheet.get("merges", []):
        area = GridRange(sheet_id, m.get("startRowIndex", 0), m["endRowIndex"],
                         m.get("startColumnIndex", 0), m["endColumnIndex"])
        if (m.get("sheetId", sheet_id) != sheet_id
                or any(type(n) is not int or n < 0 for n in (area.start_row, area.end_row,
                                                          area.start_column, area.end_column))
                or area.start_row >= area.end_row or area.start_column >= area.end_column):
            raise RecognitionError([RecognitionIssue("ANSWER_AMBIGUOUS", sheet_id, "合併範圍無效。", area)])
        if any(area.overlaps(old) for old in merges):
            raise RecognitionError([RecognitionIssue("ANSWER_OVERLAP", sheet_id, "合併範圍交疊。", area)])
        merges.append(area)

    def region(r, c):
        return next((m for m in merges if m.contains(r, c)), GridRange(sheet_id, r, r+1, c, c+1))

    def fail(code, message, area=None, number=None):
        raise RecognitionError([RecognitionIssue(code, sheet_id, message, area, number)])

    header_cells = {text: [] for text in ("題號", "題目", "作答")}
    for (r, c), cell in cells.items():
        text = _text(cell).strip()
        if text in header_cells and region(r, c).anchor == (r, c):
            header_cells[text].append(region(r, c))
    if any(not matches for matches in header_cells.values()):
        fail("HEADER_MISSING", "找不到同列的題號、題目、作答表頭。")
    if any(len(matches) != 1 for matches in header_cells.values()):
        fail("HEADER_AMBIGUOUS", "表頭文字重複，請保留唯一表頭區。")
    number_header, prompt_header, answer_header = headers = tuple(v[0] for v in header_cells.values())
    if (len({h.start_row for h in headers}) != 1 or len({h.end_row for h in headers}) != 1
            or number_header.end_column != prompt_header.start_column
            or prompt_header.end_column != answer_header.start_column):
        fail("HEADER_AMBIGUOUS", "表頭必須同列且欄區連續、不交疊。", answer_header)

    candidates = []
    seen_numbers = set()
    for (r, c), cell in sorted(cells.items()):
        if r < number_header.end_row or not number_header.start_column <= c < number_header.end_column:
            continue
        area = region(r, c)
        number = _number(cell)
        if number is None or area.anchor != (r, c):
            continue
        if number in seen_numbers:
            fail("DUPLICATE_QUESTION", "主題號重複。", area, number)
        seen_numbers.add(number)
        if area.start_column != number_header.start_column or area.end_column != number_header.end_column:
            fail("ANSWER_AMBIGUOUS", "題號範圍與題號表頭欄區不符。", area, number)
        candidates.append((number, area))
    if not candidates:
        fail("ANSWER_AMBIGUOUS", "表頭下方沒有可辨識的正整數主題號。", number_header)

    questions = []
    used_answers = []
    for number, number_area in candidates:
        labels = []
        for (r, c), cell in sorted(cells.items()):
            if not (number_area.start_row <= r < number_area.end_row
                    and answer_header.start_column <= c < answer_header.end_column):
                continue
            match = re.fullmatch(r"\s*[（(]\s*([0-9]+)\s*[)）]\s*", _text(cell))
            area = region(r, c)
            if match and int(match[1]) > 0 and area.anchor == (r, c):
                labels.append((_text(cell), int(match[1]), area))
        if labels and (len(labels) < 2 or len({label[1] for label in labels}) != len(labels)):
            code = "DUPLICATE_SUBITEM" if len(labels) >= 2 else "ANSWER_AMBIGUOUS"
            fail(code, "題組至少兩項，且小題標號不可重複。", number_area, number)
        if labels:
            covered_rows = set()
            for _, _, label_area in labels:
                rows = set(range(label_area.start_row, label_area.end_row))
                if covered_rows.intersection(rows):
                    fail("ANSWER_OVERLAP", "小題標號涵蓋相同列。", label_area, number)
                covered_rows.update(rows)
            if covered_rows != set(range(number_area.start_row, number_area.end_row)):
                fail("ANSWER_AMBIGUOUS", "題號跨列範圍存在未對應的小題列。", number_area, number)
        specs = labels or [(None, None, number_area)]
        items = []
        for label, subnumber, area in specs:
            left = area.end_column if label is not None else answer_header.start_column
            expected = GridRange(sheet_id, area.start_row, area.end_row, left, answer_header.end_column)
            if (left >= answer_header.end_column or area.start_row < number_area.start_row
                    or area.end_row > number_area.end_row):
                fail("ANSWER_OVERLAP", "小題標號超出題號或作答欄區。", area, number)
            answer = region(expected.start_row, expected.start_column)
            if answer != expected:
                code = "ANSWER_OVERLAP" if answer.overlaps(expected) and (
                    answer.start_row < expected.start_row or answer.end_row > expected.end_row
                    or answer.start_column < expected.start_column or answer.end_column > expected.end_column
                ) else "ANSWER_AMBIGUOUS"
                fail(code, "無法唯一對應完整答案區，請檢查答案合併格。", expected, number)
            if any(answer.overlaps(old) for old in used_answers):
                fail("ANSWER_OVERLAP", "不同小題的答案區交疊。", answer, number)
            prompt = GridRange(sheet_id, area.start_row, area.end_row,
                               prompt_header.start_column, prompt_header.end_column)
            prompt_area = region(prompt.start_row, prompt.start_column)
            if prompt_area != prompt:
                fail("ANSWER_AMBIGUOUS", "題目敘述無法與作答項目唯一對應。", prompt, number)
            prompt_text = _text(cells.get(prompt.anchor, {})).replace("\r\n", "\n").replace("\r", "\n")
            if not prompt_text.strip():
                fail("ANSWER_AMBIGUOUS", "缺少可核對的題目敘述。", prompt, number)
            used_answers.append(answer)
            items.append(RecognizedItem(label, subnumber, prompt_text,
                area if label is not None else None, answer,
                deepcopy(cells.get(answer.anchor, {}).get("userEnteredValue", {}))))
        questions.append(RecognizedQuestion(number, "question_set" if labels else "single",
                                            number_area, tuple(items)))
    return RecognitionResult(sheet_id, headers, tuple(questions))
