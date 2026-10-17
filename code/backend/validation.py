"""Input validation for the vault API.

The server never sees plaintext. It only checks that what it stores looks like
a base64url blob of a sane size, and that the limits requested are allowed.
"""
from __future__ import annotations

import re

ID_RE = re.compile(r"^[A-Za-z0-9_-]{32}$")
BLOB_RE = re.compile(r"^[A-Za-z0-9_-]+$")

ALLOWED_TTL = (3600, 86400, 604800)  # 1 hour, 1 day, 7 days
MAX_VIEWS_LIMIT = 5
MIN_BLOB_LEN = 40  # 12 byte IV + 16 byte GCM tag + at least one padded block
MAX_BLOB_LEN = 7168  # 5,000 byte secret -> 6,864 chars; stays under the WAF 8 KB body rule


class ValidationError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_create(payload):
    """Return (ciphertext, ttl_seconds, max_views) or raise ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError("invalid_body")

    ciphertext = payload.get("ciphertext")
    if not isinstance(ciphertext, str) or not BLOB_RE.match(ciphertext):
        raise ValidationError("invalid_ciphertext")
    if not (MIN_BLOB_LEN <= len(ciphertext) <= MAX_BLOB_LEN):
        raise ValidationError("invalid_ciphertext_length")

    ttl = payload.get("ttl")
    if not _is_int(ttl) or ttl not in ALLOWED_TTL:
        raise ValidationError("invalid_ttl")

    max_views = payload.get("max_views", 1)
    if not _is_int(max_views) or not (1 <= max_views <= MAX_VIEWS_LIMIT):
        raise ValidationError("invalid_max_views")

    return ciphertext, ttl, max_views


def is_valid_id(value) -> bool:
    return isinstance(value, str) and bool(ID_RE.match(value))
