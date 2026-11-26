from copy import deepcopy
import pytest

from guided_notes.notes.display_models import validate_display_content
from guided_notes.http import ApiError

IMPORT = '11111111-1111-4111-8111-111111111111'


def pair():
    catalog = dict(import_id=IMPORT, import_version=1, questions=[
        dict(question_id='q1', display_number='1', kind='single', items=[dict(item_id='i1', blank_id='b1', subitem_label=None)]),
        dict(question_id='q2', display_number='2', kind='question_set', items=[
            dict(item_id=f'i2-{n}', blank_id=f'b2-{n}', subitem_label=f'({n})') for n in (1, 2)])])
    display = dict(display_contract_version=1, import_id=IMPORT, import_version=1, questions=[
        {**{k: q[k] for k in ('question_id', 'display_number', 'kind')}, 'items': [
            dict(item_id=i['item_id'], subitem_label=i['subitem_label'], prompt_text='  中文 <script>\nΩ🙂  ')
            for i in q['items']]} for q in catalog['questions']])
    return catalog, display


def test_valid_detached_display():
    catalog, display = pair()
    result = validate_display_content(display, catalog)
    assert result == display and result is not display


@pytest.mark.parametrize('change', [
    lambda d: d.update(display_contract_version=True),
    lambda d: d.update(import_version=True),
    lambda d: d.update(import_version=2),
    lambda d: d.update(import_id='not-uuid'),
    lambda d: d.update(import_id='22222222-2222-4222-8222-222222222222'),
    lambda d: d.update(questions=None),
    lambda d: d.update(source_url='private'),
    lambda d: d['questions'].reverse(),
    lambda d: d['questions'].append(deepcopy(d['questions'][0])),
    lambda d: d['questions'].pop(),
    lambda d: d['questions'][0].update(kind='question_set'),
    lambda d: d['questions'][0].update(question_id='q2'),
    lambda d: d['questions'][0].update(items=None),
    lambda d: d['questions'][0].update(display_number='99'),
    lambda d: d['questions'][0].update(private='secret'),
    lambda d: d['questions'][1]['items'].reverse(),
    lambda d: d['questions'][1]['items'].pop(),
    lambda d: d['questions'][1]['items'].append(deepcopy(d['questions'][1]['items'][0])),
    lambda d: d['questions'][1]['items'][0].update(item_id='i1'),
    lambda d: d['questions'][1]['items'][0].update(subitem_label='(2)'),
    lambda d: d['questions'][0]['items'][0].update(prompt_text=' \n '),
    lambda d: d['questions'][0]['items'][0].update(prompt_text=1),
    lambda d: d['questions'][0]['items'][0].update(blank_id='private'),
    lambda d: d['questions'][0]['items'][0].update(observed_user_value='private'),
])
def test_reject_mismatch(change):
    catalog, display = pair()
    change(display)
    with pytest.raises(ApiError) as error:
        validate_display_content(display, catalog)
    assert (error.value.status, error.value.code) == (409, 'DISPLAY_CONTENT_MISMATCH')
