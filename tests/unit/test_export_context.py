import sqlite3

import pytest

from guided_notes.http import ApiError
from guided_notes.notes.export_context import winner_labels


def database():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE classroom_groups(id INTEGER, classroom_id TEXT, name TEXT)')
    db.executemany('INSERT INTO classroom_groups VALUES(?,?,?)', [(10,'a','42'), (20,'b','42'), (30,'a','999')])
    return db


def test_original_room_and_batch_labels():
    db = database()
    queries = []
    db.set_trace_callback(queries.append)
    assert winner_labels(db, 'a', [{'winner_group_id': '10'}, {'winner_group_id': '30'}, {'winner_group_id': None}]) == {
        '10': '第 42 組', '30': '第 999 組'}
    assert len(queries) == 1


@pytest.mark.parametrize('value', ['20', '99', '01', '0', '1.0', '１', 'x', '9'*128])
def test_missing_cross_room_or_malformed_winner(value):
    with pytest.raises(ApiError) as failure:
        winner_labels(database(), 'a', [{'winner_group_id': value}])
    assert failure.value.status == 422
    assert failure.value.code == 'RESULT_INVALID'
    assert failure.value.context['reason'] == 'WINNER_GROUP_SCOPE_MISMATCH'


def test_invalid_stored_number_does_not_pass_through():
    db = database()
    db.execute("UPDATE classroom_groups SET name='第一組' WHERE id=10")
    with pytest.raises(ApiError):
        winner_labels(db, 'a', [{'winner_group_id': '10'}])
    assert winner_labels(db, 'a', [{'winner_group_id': None}]) == {}


def test_group_one_is_not_its_database_id():
    db = database()
    db.execute("INSERT INTO classroom_groups VALUES(100,'a','1')")
    assert winner_labels(db, 'a', [{'winner_group_id':'100'}]) == {'100':'第 1 組'}
