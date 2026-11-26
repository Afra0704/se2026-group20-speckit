"""Synthetic providers confined to tests; never imported by application code."""
from uuid import NAMESPACE_URL, uuid5

IMPORT_ID = '11111111-1111-4111-8111-111111111111'


def course_import_id(course_id, suffix=''):
    return str(uuid5(NAMESPACE_URL, f'test-course:{course_id}:{suffix}'))


def catalog(import_id, version, *, legacy=False):
    return dict(import_id=import_id, import_version=version, questions=[
        dict(question_id=f'q{i}' if legacy else f'fixture-q{i}',
             display_number=f'{version}.{i}' if legacy else str(i if version == 1 else i + 3),
             kind='question_set' if i == 2 else 'single', items=[
                 dict(item_id=f'i{i}-{j}' if legacy else f'fixture-item-{i}-{j}',
                      blank_id=f'b{i}-{j}' if legacy else f'fixture-blank-{i}-{j}',
                      subitem_label=f'({j})' if i == 2 else None)
                 for j in range(1, 3 if i == 2 else 2)]) for i in range(1, 4)])


def display(core):
    return dict(display_contract_version=1, import_id=core['import_id'], import_version=core['import_version'],
        questions=[{**{k: q[k] for k in ('question_id', 'display_number', 'kind')}, 'items': [
            dict(item_id=i['item_id'], subitem_label=i['subitem_label'], prompt_text=f"測試題 {q['display_number']} {i['subitem_label'] or ''}")
            for i in q['items']]} for q in core['questions']])


def seed_published(teacher_id, value, course_id=None):
    """Persist explicit synthetic-provider correspondences, never bypass app guards."""
    import json
    from guided_notes.db import connection
    from guided_notes.notes.repository import now
    from guided_notes.notes.recognition import recognize
    from dataclasses import asdict
    from pathlib import Path
    db=connection();iid=value['import_id'];version=value['import_version']
    sid='fixture-source-'+iid
    db.execute('INSERT INTO notes_sources VALUES(?,?,?,?,?) ON CONFLICT DO NOTHING',(sid,teacher_id,'fixture-'+iid,7,'合成講義'))
    db.execute('INSERT INTO notes_imports VALUES(?,?) ON CONFLICT DO NOTHING',(iid,sid))
    recognized=asdict(recognize(json.loads((Path(__file__).parent/'fixtures/sheets_layouts.json').read_text(encoding='utf-8'))['mixed']))
    db.execute('INSERT INTO notes_catalogs VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',(iid,version,json.dumps(value),json.dumps(recognized),'synthetic','synthetic','synthetic',now()))
    if course_id is not None:db.execute('INSERT INTO notes_import_courses VALUES(?,?,?) ON CONFLICT DO NOTHING',(iid,course_id,now()))
