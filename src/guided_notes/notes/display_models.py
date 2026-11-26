"""Strict display-only contract; core catalog and submission DTOs stay unchanged."""
from copy import deepcopy
from uuid import UUID

from ..http import ApiError


def mismatch():
    raise ApiError(409, "DISPLAY_CONTENT_MISMATCH")


def validate_display_content(value, catalog):
    def require(condition):
        if not condition:
            mismatch()

    def fields(obj, names):
        require(isinstance(obj, dict) and set(obj) == set(names.split()))

    fields(value, 'display_contract_version import_id import_version questions')
    require(type(value['display_contract_version']) is int and value['display_contract_version'] == 1)
    try:
        valid_uuid = isinstance(value['import_id'], str) and str(UUID(value['import_id'])) == value['import_id']
    except (ValueError, AttributeError):
        valid_uuid = False
    require(valid_uuid and value['import_id'] == catalog['import_id'])
    require(type(value['import_version']) is int and value['import_version'] > 0
            and value['import_version'] == catalog['import_version'])
    questions = value['questions']
    require(isinstance(questions, list) and bool(questions) and len(questions) == len(catalog['questions']))
    seen_questions, seen_items = set(), set()
    for question, core in zip(questions, catalog['questions'], strict=True):
        fields(question, 'question_id display_number kind items')
        for key in ('question_id', 'display_number', 'kind'):
            require(isinstance(question[key], str) and question[key] == core[key])
        require(question['question_id'] not in seen_questions and question['kind'] in ('single', 'question_set'))
        seen_questions.add(question['question_id'])
        items = question['items']
        require(isinstance(items, list) and len(items) == len(core['items'])
                and (len(items) == 1 if question['kind'] == 'single' else len(items) >= 2))
        for item, original in zip(items, core['items'], strict=True):
            fields(item, 'item_id subitem_label prompt_text')
            require(isinstance(item['item_id'], str) and item['item_id'] == original['item_id']
                    and item['item_id'] not in seen_items)
            seen_items.add(item['item_id'])
            require(item['subitem_label'] == original['subitem_label']
                    and (item['subitem_label'] is None if question['kind'] == 'single'
                         else isinstance(item['subitem_label'], str) and bool(item['subitem_label'].strip())))
            require(isinstance(item['prompt_text'], str) and bool(item['prompt_text'].strip()))
    return deepcopy(value)
