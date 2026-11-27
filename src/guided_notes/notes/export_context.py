"""Authorized display context, separate from immutable export/result snapshots."""
import re
from urllib.parse import quote, urlencode

from flask import current_app

from ..activities.classroom_membership import GROUP_NUMBER, group_label
from ..activities.teacher import get_activity_reference
from ..db import connection
from ..http import ApiError
from ..time_views import activity_time_display

MAPPING_MESSAGE = '勝組資料與原課堂不一致，無法回填。'


def mapping_error():
    error = ApiError(422, 'RESULT_INVALID')
    error.context = {'reason': 'WINNER_GROUP_SCOPE_MISMATCH'}
    return error


def selected_activity(args):
    values = args.getlist('activity_id')
    if not values:
        return None
    value = values[0]
    if len(values) != 1 or not isinstance(value, str) or not value.strip() or len(value) > 256 or any(
            ord(c) < 32 or ord(c) == 127 for c in value):
        raise ApiError(400, 'INVALID_REQUEST')
    return value


def activity_context(teacher, activity_id):
    reference = get_activity_reference(teacher, activity_id)
    if not current_app.config['CLASSROOM_MODE']:
        return dict(reference, activity_title='非課堂活動', classroom_id=None, classroom_title=None,
                    course_id=None, course_title=None, result_url=None, times=None)
    row = connection().execute('''SELECT ca.title AS activity_title,ca.classroom_id,
        ca.created_at,ca.started_at,ca.closed_at,a.phase,a.phase_version,
        c.title AS classroom_title,c.state AS classroom_state,c.course_id,co.title AS course_title
        FROM classroom_activities ca JOIN activities a ON a.id=ca.activity_id
        JOIN classrooms c ON c.id=ca.classroom_id JOIN courses co ON co.id=c.course_id
        WHERE ca.activity_id=? AND a.teacher_id=? AND co.teacher_id=?''',
        (activity_id, teacher.teacher_id, teacher.teacher_id)).fetchone()
    if row is None:
        raise ApiError(404, 'ACTIVITY_NOT_FOUND')
    result = dict(reference, **dict(row))
    result['times'] = activity_time_display(dict(row), trusted_lifecycle=True)
    result['result_url'] = (f"/teacher/workspace/courses/{quote(row['course_id'], safe='')}/classrooms/"
                            f"{quote(row['classroom_id'], safe='')}?{urlencode({'activity_id': activity_id})}")
    return result


def winner_labels(db, classroom_id, units):
    ids = {unit['winner_group_id'] for unit in units if unit['winner_group_id'] is not None}
    if not ids:
        return {}
    if any(not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,18}', value)
           or int(value) > 9223372036854775807 for value in ids):
        raise mapping_error()
    rows = db.execute(f'''SELECT id,name FROM classroom_groups WHERE classroom_id=?
        AND id IN ({','.join('?' for _ in ids)})''', (classroom_id, *[int(value) for value in ids])).fetchall()
    if len(rows) != len(ids) or any(not isinstance(row['name'], str) or not GROUP_NUMBER.fullmatch(row['name'])
                                    for row in rows):
        raise mapping_error()
    return {str(row['id']): group_label(row['name']) for row in rows}


def project(teacher, activity_id, units, *, strict=False):
    context = activity_context(teacher, activity_id)
    if context['classroom_id'] is None:
        return context, {u['winner_group_id']: u['winner_group_id'] for u in units}, None
    try:
        labels = winner_labels(connection(), context['classroom_id'], units)
        return context, labels, None
    except ApiError as error:
        if strict or error.code != 'RESULT_INVALID':
            raise
        return context, {}, dict(code=error.code, reason=error.context['reason'], message=MAPPING_MESSAGE)


def validate(teacher, snapshot):
    project(teacher, snapshot['activity_id'], snapshot['units'], strict=True)


def decorate(teacher, data, units):
    """Mutate only the teacher response projection, never the stored snapshot."""
    if not current_app.config['CLASSROOM_MODE']:
        return data
    context, labels, error = project(teacher, data['activity_id'], units)
    for field in ('import_id', 'import_version', 'result_version'):
        if field in data:
            context[field] = data[field]
    data['activity_context'] = context
    data['context_error'] = error
    for item in data.get('items', data.get('units', [])):
        item['winner_group_label'] = labels.get(item['winner_group_id'])
    return data
