"""Small utilities shared across the-primer models and engine."""

from __future__ import annotations

from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)
