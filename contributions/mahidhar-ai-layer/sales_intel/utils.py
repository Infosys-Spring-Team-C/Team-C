"""Small shared helpers."""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC 'now'.

    `datetime.utcnow()` is deprecated in Python 3.12+. We keep the values naive
    (no tzinfo) because every timestamp in the domain models is naive UTC, and
    mixing aware/naive datetimes raises at comparison time.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
