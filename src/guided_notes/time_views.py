"""Read-only adapters for already-authorized event records, not access control."""
from dataclasses import asdict, dataclass

from .time_display import DisplayTime, present_time


def activity_time_display(row, *, trusted_lifecycle=False):
    """Caller must authorize row before projecting it. Policies are never client input."""
    phase, version = row.get('phase'), row.get('phase_version')
    if phase == 'PREPARING':
        started = 'not_started'
    elif phase == 'CLOSED' and trusted_lifecycle and type(version) is int and version == 1:
        # This source initializes PREPARING/version0 and increments per transition.
        # A real start value must still be shown, even for an inconsistent counter.
        started = 'skipped_start' if not row.get('started_at') or (
            isinstance(row['started_at'], str) and not row['started_at'].strip()) else 'occurred'
    else:
        started = 'occurred'
    closed = 'not_ended' if phase in ('PREPARING', 'LIVE') else 'occurred'
    result = {'version':1, 'timezone':'Asia/Taipei', 'utc_offset':'+08:00'}
    for field, kind, occurrence in [('created_at','created','occurred'),
                                     ('started_at','started',started), ('closed_at','closed',closed)]:
        result[field] = asdict(present_time(row.get(field), event_kind=kind,
                                           source_policy='sqlite_utc', occurrence=occurrence))
    return result


def notes_time(value, *, event_kind='operation_updated') -> DisplayTime:
    return present_time(value, event_kind=event_kind, source_policy='offset_required', occurrence='occurred')


@dataclass(frozen=True)
class ReadbackTimeView:
    verification_status: str
    time: DisplayTime | None
    text: str


def readback_time(verification_status, value) -> ReadbackTimeView:
    if verification_status != 'verified':
        return ReadbackTimeView(verification_status, None, '尚未驗證')
    time = notes_time(value, event_kind='readback')
    return ReadbackTimeView(verification_status, time, time.text)
