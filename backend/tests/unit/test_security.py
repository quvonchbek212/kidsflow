"""Parol hash va JWT token uchun unit testlar (11-bo'lim)."""

from __future__ import annotations

import uuid

import pytest
from app.core import security


def test_password_hash_and_verify() -> None:
    hashed = security.hash_password("juda-maxfiy-parol")

    assert hashed != "juda-maxfiy-parol"  # ochiq matn saqlanmaydi
    assert security.verify_password("juda-maxfiy-parol", hashed) is True
    assert security.verify_password("noto'g'ri", hashed) is False


def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    token = security.create_access_token(user_id)

    assert security.decode_access_token(token) == user_id


def test_decode_invalid_token_raises() -> None:
    with pytest.raises(ValueError):
        security.decode_access_token("buzuq.token.qiymati")


def test_refresh_token_hash_is_deterministic() -> None:
    raw = security.generate_opaque_token()

    assert security.hash_opaque_token(raw) == security.hash_opaque_token(raw)
    assert security.hash_opaque_token(raw) != raw
