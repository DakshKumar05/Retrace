"""Collision-free human-readable references.

`reference` is UNIQUE on both transactions and refund requests, and the short
five-digit form these use is only a 90,000-value space. That is fine for a
handful of seeded rows and fails quickly once anything generates in bulk — the
birthday bound bites long before the space is full, and the result is a 500 in
the middle of a demo rather than a retry.

So: propose a short reference, check it, and widen it if the short space is
crowded. The common case still returns the familiar `TX12345` shape.
"""
from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

SHORT_ATTEMPTS = 6


def unique_reference(db: Session, column, prefix: str) -> str:
    """Return a reference not already present in `column`."""
    for _ in range(SHORT_ATTEMPTS):
        candidate = f"{prefix}{secrets.randbelow(90000) + 10000}"
        if db.scalar(select(column).where(column == candidate)) is None:
            return candidate

    # The short space is busy. Widen rather than keep rolling the same dice.
    while True:
        candidate = f"{prefix}{secrets.token_hex(4).upper()}"
        if db.scalar(select(column).where(column == candidate)) is None:
            return candidate
