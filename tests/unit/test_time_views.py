import pytest

from guided_notes.time_views import activity_time_display, notes_time, readback_time


def activity(phase='PREPARING', version=0, **values):
    return {'phase': phase, 'phase_version': version, 'created_at':'2026-11-27 03:04:05',
            'started_at':None, 'closed_at':None, **values}


@pytest.mark.parametrize('phase,version,status', [('PREPARING',0,'not_started'),
    ('LIVE',1,'missing'), ('CLOSED',1,'skipped_start'), ('CLOSED',2,'missing'),
    ('CLOSED',None,'missing'), ('CLOSED',True,'missing')])
def test_activity_lifecycle(phase,version,status):
    value = activity_time_display(activity(phase,version), trusted_lifecycle=True)
    assert value['started_at']['status'] == status
    assert value['closed_at']['status'] == ('missing' if phase=='CLOSED' else 'not_ended')
    assert value['created_at']['text'] == '2026-11-27 11:04'


def test_direct_close_requires_trust_and_null_not_corruption():
    assert activity_time_display(activity('CLOSED',1))['started_at']['status']=='missing'
    assert activity_time_display(activity('CLOSED',1,started_at='bad'), trusted_lifecycle=True)['started_at']['status']=='invalid'
    assert activity_time_display(activity(started_at='2026-11-27 03:04:05'))['started_at']['status']=='invalid'


def test_notes_and_readback_semantics():
    assert notes_time('2026-11-27 03:04:05', event_kind='confirmed').status=='unknown_timezone'
    assert notes_time(None,event_kind='preview_created').status=='missing'
    for status in ('unknown','failed','skipped','not_processed','conflict'):
        value=readback_time(status,'2026-11-27T03:04:05Z')
        assert value.verification_status==status and value.time is None and value.text=='尚未驗證'
    assert readback_time('verified',None).time.status=='missing'
    assert readback_time('verified','bad').time.status=='invalid'
    assert readback_time('verified','2026-11-27T03:04:05Z').text=='2026-11-27 11:04'

