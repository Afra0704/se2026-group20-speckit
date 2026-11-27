import importlib.util
from pathlib import Path

from conftest import post
from google_support import google_app, login, connect


def test_fault_requires_new_authorization_and_never_mutates_secrets(google_app,tmp_path,monkeypatch):
    from guided_notes.auth import require_teacher
    from guided_notes.db import connection
    from guided_notes.notes import routes
    monkeypatch.setattr(routes,'gateway',lambda teacher:'original-gateway')
    marker=tmp_path/'auth-fault.json'
    spec=importlib.util.spec_from_file_location('qa_auth_fault',Path(__file__).with_name('auth_fault.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.install_auth_fault(marker)
    google_app.add_url_rule('/qa-fault-probe',view_func=lambda:{'gateway':routes.gateway(require_teacher())})
    google_teacher=login(google_app.test_client(),google_app)
    connect(google_teacher)
    assert google_teacher.get('/qa-fault-probe').json=={'gateway':'original-gateway'}
    with google_app.app_context():
        before=tuple(connection().execute('SELECT * FROM google_sheets_credentials').fetchone())
    marker.write_text('{"teacher_id": null}',encoding='utf-8')
    assert google_teacher.get('/qa-fault-probe').status_code==409
    assert google_teacher.get('/qa-fault-probe').status_code==409
    with google_app.app_context():
        assert tuple(connection().execute('SELECT * FROM google_sheets_credentials').fetchone())==before
    connect(google_teacher)
    assert google_teacher.get('/qa-fault-probe').json=={'gateway':'original-gateway'}
    assert not marker.exists()
