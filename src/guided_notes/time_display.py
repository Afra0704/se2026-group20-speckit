"""Pure, source-aware event presentation. Never used for ordering or deadlines."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Literal

SourcePolicy = Literal['sqlite_utc', 'offset_required', 'unverified']
EventKind = Literal['created', 'started', 'closed', 'confirmed', 'preview_created', 'operation_updated', 'readback']
Occurrence = Literal['occurred', 'not_started', 'not_ended', 'skipped_start', 'unknown']
Status = Literal['known', 'not_started', 'not_ended', 'skipped_start', 'missing', 'invalid', 'unknown_timezone']

TAIPEI = timezone(timedelta(hours=8), name='Asia/Taipei')
TIMEZONE_NOTICE = '台北時間（UTC+08:00）'
LABELS = {'created':'建立', 'started':'開始', 'closed':'結束', 'confirmed':'匯入確認',
          'preview_created':'預覽', 'operation_updated':'更新', 'readback':'回讀'}
MESSAGES = {'not_started':'尚未開始', 'not_ended':'尚未結束', 'skipped_start':'未開始即結束',
            'missing':'時間未記錄', 'invalid':'時間資料無法辨識', 'unknown_timezone':'時區未確認'}
_FULL = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}'
                   r'(?:\.[0-9]{1,6})?(?P<offset>Z|[+-][0-9]{2}:[0-9]{2})?', re.ASCII)
_SQL = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}', re.ASCII)


@dataclass(frozen=True)
class EventTimeInput:
    raw_value: str | None
    event_kind: EventKind
    source_policy: SourcePolicy = 'unverified'
    occurrence: Occurrence = 'unknown'
    scope: object = None


@dataclass(frozen=True)
class NormalizedObservation:
    instant: datetime | None
    status: Status
    event_kind: EventKind


@dataclass(frozen=True)
class DisplayTime:
    label: str
    status: Status
    text: str
    instant_utc: str | None


def present_time(raw_value, *, event_kind, source_policy='unverified', occurrence='unknown') -> DisplayTime:
    """Interpret only supported writer formats; format to minutes without rounding."""
    label = LABELS.get(event_kind, '時間')

    def fallback(status):
        return DisplayTime(label, status, MESSAGES[status], None)

    if (event_kind not in LABELS or source_policy not in ('sqlite_utc', 'offset_required', 'unverified')
            or occurrence not in ('occurred', 'not_started', 'not_ended', 'skipped_start', 'unknown')):
        return fallback('invalid')
    if raw_value is not None and (not isinstance(raw_value, str) or len(raw_value) > 128):
        return fallback('invalid')
    if raw_value is None or not raw_value.strip():
        return fallback(occurrence if occurrence in ('not_started', 'not_ended', 'skipped_start') else 'missing')
    if occurrence in ('not_started', 'not_ended', 'skipped_start'):
        return fallback('invalid')
    match = _FULL.fullmatch(raw_value)
    if match is None:
        return fallback('invalid')
    offset = match['offset']
    if offset and offset != 'Z' and (int(offset[1:3]) > 23 or int(offset[4:6]) > 59):
        return fallback('invalid')
    try:
        instant = datetime.fromisoformat(raw_value)
        if offset is None:
            if source_policy != 'sqlite_utc':
                return fallback('unknown_timezone')
            if _SQL.fullmatch(raw_value) is None:
                return fallback('invalid')
            instant = instant.replace(tzinfo=timezone.utc)
        utc = instant.astimezone(timezone.utc)
        local = utc.astimezone(TAIPEI)
        text = f'{local.year:04}-{local.month:02}-{local.day:02} {local.hour:02}:{local.minute:02}'
        observation = NormalizedObservation(utc, 'known', event_kind)
        return DisplayTime(label, observation.status, text, observation.instant.isoformat())
    except (ValueError, OverflowError):
        return fallback('invalid')
