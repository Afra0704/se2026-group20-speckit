"""Allow only read-only teacher pages as a Sheets authorization return target."""
import re
from urllib.parse import parse_qs, urlsplit

from ..http import ApiError


def sheets_return_target(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ApiError(400, 'INVALID_REQUEST')
    try:
        parts = urlsplit(value)
    except ValueError:
        raise ApiError(400, 'INVALID_REQUEST') from None
    if (parts.scheme or parts.netloc or parts.fragment or '\\' in value
            or not re.fullmatch(r'/teacher/(?:notes(?:/export-previews(?:/[A-Za-z0-9_-]+)?|/operations/[A-Za-z0-9_-]+)?|workspace/imports/[A-Za-z0-9_-]+)', parts.path)):
        raise ApiError(400, 'INVALID_REQUEST')
    if parts.query:
        query = parse_qs(parts.query, keep_blank_values=True)
        if (parts.path != '/teacher/notes/export-previews' or set(query) != {'activity_id'}
                or len(query['activity_id']) != 1
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', query['activity_id'][0])):
            raise ApiError(400, 'INVALID_REQUEST')
    return value
