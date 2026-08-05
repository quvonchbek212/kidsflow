"""Tibbiy ma'lumot shifrlash uchun unit testlar (11-bo'lim)."""

from __future__ import annotations

from app.utils.encryption import decrypt_text, encrypt_text


def test_encrypt_decrypt_roundtrip() -> None:
    plaintext = "Allergiya: yong'oq. Doimiy dori: yo'q."
    token = encrypt_text(plaintext)

    assert token is not None
    assert token != plaintext  # ochiq matn saqlanmaydi
    assert decrypt_text(token) == plaintext


def test_none_and_empty_return_none() -> None:
    assert encrypt_text(None) is None
    assert encrypt_text("") is None
    assert decrypt_text(None) is None
    assert decrypt_text("") is None


def test_invalid_token_returns_none() -> None:
    assert decrypt_text("bu-yaroqsiz-token") is None
