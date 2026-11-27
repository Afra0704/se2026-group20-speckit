import importlib.util
import json
from pathlib import Path

from conftest import app, teacher, writable, post
from test_export_routes import setup_preview, confirm_export


def test_partial_unknown_restart_and_conflict_recovery(app,teacher,writable,tmp_path,monkeypatch):
    from guided_notes.notes import routes
    # All three winning cells have explicit original values requiring consent.
    for r,c in [(4,6),(5,6),(7,5)]:writable.put(r,c,{'stringValue':'original'})
    preview,_,_=setup_preview(app,teacher,writable)
    monkeypatch.setattr(routes,'gateway',routes.gateway)
    marker,audit=tmp_path/'write-fault.json',tmp_path/'write-audit.json'
    marker.write_text(json.dumps({'attempts':0,'injected':False,'teacher_id':None}),encoding='utf-8')
    audit.write_text(json.dumps({'actual_batches':[],'uncertain_batches':[],'blocked_readbacks':0}),encoding='utf-8')
    spec=importlib.util.spec_from_file_location('qa_write_fault',Path(__file__).with_name('write_fault.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.install_write_fault(marker,audit)
    consent=[i['item_id'] for i in preview['items'] if i['action']=='requires_overwrite_confirmation']
    assert len(consent)==3
    first=confirm_export(teacher,preview['preview_id'],overwrite=consent).json
    assert first['counts']['verified']==2 and first['counts']['unknown']==1
    assert json.loads(audit.read_text())['actual_batches']==[2]
    fresh=post(teacher,f"/teacher/notes/operations/{first['operation_id']}/recovery-preview").json
    assert fresh['counts']['already_matches']==2
    assert fresh['counts']['write']==1 and fresh['counts']['requires_overwrite_confirmation']==0
    # A newly changed original needs new consent, not the original approval.
    writable.put(7,5,{'stringValue':'new conflict'})
    newer=post(teacher,f"/teacher/notes/operations/{first['operation_id']}/recovery-preview").json
    assert newer['counts']['requires_overwrite_confirmation']==1
    pending=[i['item_id'] for i in newer['items'] if i['action']=='requires_overwrite_confirmation']
    final=confirm_export(teacher,newer['preview_id'],key='qa-recovered',overwrite=pending).json
    assert final['status']=='completed'
    assert json.loads(audit.read_text())['actual_batches']==[2,1]
    assert len(writable.writes)==2
