"""Project only prompt text from the selected frozen recognized catalog."""
import json

from ..auth import require_teacher
from ..db import connection
from ..http import ApiError
from . import repository as repo
from .display_models import mismatch, validate_display_content
from .models import validate_catalog


def get_display_content(teacher_context, import_id, import_version):
    if require_teacher() != teacher_context:
        raise ApiError(403, 'TEACHER_REQUIRED')
    row = repo.catalog_row(connection(), teacher_context.teacher_id, import_id, import_version)
    catalog = validate_catalog(json.loads(row['dto']))
    try:
        recognized = json.loads(row['recognized'])
        source_questions = recognized['questions']
        if not isinstance(source_questions, list) or len(source_questions) != len(catalog['questions']):
            mismatch()
        questions = []
        for core, source in zip(catalog['questions'], source_questions, strict=True):
            if any(core[k] != source[k] for k in ('display_number', 'kind')) or len(core['items']) != len(source['items']):
                mismatch()
            items = []
            for item, original in zip(core['items'], source['items'], strict=True):
                if item['subitem_label'] != original['subitem_label']:
                    mismatch()
                prompt = original.get('prompt_text')
                if not isinstance(prompt, str) or not prompt.strip():
                    raise ApiError(409, 'QUESTION_TEXT_UNAVAILABLE')
                items.append(dict(item_id=item['item_id'], subitem_label=item['subitem_label'], prompt_text=prompt))
            questions.append({**{k: core[k] for k in ('question_id', 'display_number', 'kind')}, 'items': items})
    except (KeyError, TypeError, ValueError):
        raise ApiError(409, 'DISPLAY_CONTENT_MISMATCH') from None
    return validate_display_content(dict(display_contract_version=1, import_id=import_id,
        import_version=import_version, questions=questions), catalog)
