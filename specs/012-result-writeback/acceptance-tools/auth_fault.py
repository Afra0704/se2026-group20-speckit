"""QA launcher only: no real credential revocation or secret read/write."""
import json


def install_auth_fault(marker):
    from guided_notes.auth import require_teacher
    from guided_notes.db import connection
    from guided_notes.http import ApiError
    from guided_notes.notes import routes
    original = routes.gateway

    def gateway(teacher):
        if marker.is_file():
            if require_teacher() != teacher:
                raise ApiError(403, 'FORBIDDEN')
            row = connection().execute(
                'SELECT teacher_id,revision FROM google_sheets_credentials WHERE teacher_id=?',
                (teacher.teacher_id,)).fetchone()
            if row is not None:
                state = json.loads(marker.read_text(encoding='utf-8'))
                if state.get('teacher_id') is None:
                    state = {'teacher_id': row['teacher_id'], 'revision': row['revision']}
                    marker.write_text(json.dumps(state), encoding='utf-8')
                if state['teacher_id'] == row['teacher_id']:
                    if state['revision'] == row['revision']:
                        raise ApiError(409, 'SHEETS_REAUTH_REQUIRED')
                    # Only a newer stored authorization ends this controlled fault.
                    marker.unlink(missing_ok=True)
        return original(teacher)

    routes.gateway = gateway
