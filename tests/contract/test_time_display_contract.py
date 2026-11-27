from dataclasses import asdict

from guided_notes.time_display import present_time
from guided_notes.time_views import activity_time_display


def test_display_contract_and_null_invariant():
    for raw in ('2026-11-27T03:04:05.123456Z', None, 'bad', '2026-11-27 03:04:05'):
        value=asdict(present_time(raw,event_kind='closed',occurrence='occurred'))
        assert set(value)=={'label','status','text','instant_utc'}
        assert (value['instant_utc'] is not None)==(value['status']=='known')
        assert value['label']=='結束'
    value=asdict(present_time('2026-11-27T03:04:05.123456Z',event_kind='closed'))
    assert value['text']=='2026-11-27 11:04' and value['instant_utc'].endswith('05.123456+00:00')


def test_teacher_sidecar_version_and_no_internal_values():
    value=activity_time_display({'phase':'PREPARING','phase_version':0,'created_at':'2026-11-27 03:04:05',
                                 'started_at':None,'closed_at':None})
    assert set(value)=={'version','timezone','utc_offset','created_at','started_at','closed_at'}
    assert (value['version'],value['timezone'],value['utc_offset'])==(1,'Asia/Taipei','+08:00')
    assert 'raw_value' not in repr(value) and 'phase_version' not in repr(value)
