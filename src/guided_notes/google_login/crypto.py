"""Authenticated envelopes: ciphertext cannot be reassigned to another owner."""
import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from ..http import ApiError


def cipher():
    try:
        path = Path(current_app.config['GOOGLE_TOKEN_KEY_FILE']).resolve()
        if path.is_relative_to(Path(__file__).resolve().parents[3]):
            raise ValueError()
        return Fernet(path.read_bytes().strip())
    except (OSError, ValueError, TypeError, KeyError):
        raise ApiError(503, 'GOOGLE_CREDENTIALS_UNAVAILABLE') from None


def encrypt(payload, binding):
    return cipher().encrypt(json.dumps({'binding':binding,'payload':payload}, ensure_ascii=False, allow_nan=False).encode())


def decrypt(blob, binding):
    try:
        value = json.loads(cipher().decrypt(blob))
        if set(value) != {'binding','payload'} or value['binding'] != binding or not isinstance(value['payload'], dict):
            raise ValueError()
        return value['payload']
    except (InvalidToken, ValueError, TypeError):
        raise ApiError(503, 'GOOGLE_CREDENTIALS_UNAVAILABLE') from None
