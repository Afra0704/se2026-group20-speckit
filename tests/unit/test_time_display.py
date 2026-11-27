from dataclasses import FrozenInstanceError

import pytest

from guided_notes.time_display import present_time


@pytest.mark.parametrize('raw,policy', [
    ('2026-11-27T03:04:05Z', 'unverified'),
    ('2026-11-27T11:04:05+08:00', 'offset_required'),
    ('2026-11-26T22:04:05-05:00', 'unverified'),
    ('2026-11-27 03:04:05', 'sqlite_utc'),
])
def test_same_instant_has_fixed_minute_display(raw, policy):
    value = present_time(raw, event_kind='closed', source_policy=policy, occurrence='occurred')
    assert (value.status, value.text, value.label) == ('known', '2026-11-27 11:04', '結束')
    assert value.instant_utc == '2026-11-27T03:04:05+00:00'
    with pytest.raises(FrozenInstanceError):
        value.text = 'changed'


@pytest.mark.parametrize('raw,text', [
    ('2026-11-26T16:03:59.999999Z', '2026-11-27 00:03'),
    ('2026-11-30T16:00:00Z', '2026-12-01 00:00'),
    ('2026-12-31T16:00:00Z', '2027-01-01 00:00'),
    ('0001-01-01T00:00:00Z', '0001-01-01 08:00'),
])
def test_boundaries_and_no_rounding(raw, text):
    value = present_time(raw, event_kind='created')
    assert value.text == text
    if '.' in raw:
        assert '.999999' in value.instant_utc


@pytest.mark.parametrize('raw', [True, 1730000000, {}, [], '2026-11-27',
    '2026-W48-5T03:04:05Z', '2026-02-30T03:00:00Z', '2026-11-27T24:00:00Z',
    '2026-11-27T03:04:60Z', '2026-11-27T03:04:05+24:00',
    '2026-11-27T03:04:05+00:60', '2026-11-27T03:04:05+0800',
    '2026-11-27T03:04:05.1234567Z', ' 2026-11-27T03:04:05Z',
    '2026-11-27T03:04:05Z ', 'x' * 129,
    '9999-12-31T23:59:59Z', '0001-01-01T00:00:00+01:00'])
def test_bad_values_are_safe(raw):
    value = present_time(raw, event_kind='created', occurrence='occurred')
    assert (value.status, value.text, value.instant_utc) == ('invalid', '時間資料無法辨識', None)


@pytest.mark.parametrize('policy', ['offset_required', 'unverified'])
def test_naive_not_guessed(policy):
    assert present_time('2026-11-27 03:04:05', event_kind='created', source_policy=policy).status == 'unknown_timezone'


@pytest.mark.parametrize('raw', [None, '', '  '])
@pytest.mark.parametrize('occurrence,status', [('occurred','missing'), ('unknown','missing'),
    ('not_started','not_started'), ('not_ended','not_ended'), ('skipped_start','skipped_start')])
def test_missing_states(raw, occurrence, status):
    value = present_time(raw, event_kind='started', occurrence=occurrence)
    assert value.status == status and value.instant_utc is None


def test_contradictory_value_cannot_be_rendered_as_pending():
    for raw in ('bad', '2026-11-27T03:04:05Z'):
        assert present_time(raw, event_kind='started', occurrence='not_started').status == 'invalid'
    assert present_time('2026-11-27T03:04:05Z', event_kind='created', source_policy='client_override').status == 'invalid'
