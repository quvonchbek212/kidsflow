"""Fayl validatsiyasi va saqlash uchun unit testlar (11-bo'lim)."""

from __future__ import annotations

import pytest
from app.utils import file_storage
from app.utils.file_storage import FileValidationError

from tests.conftest import TINY_PNG


def test_valid_png_passes() -> None:
    file_storage.validate_upload(TINY_PNG, "image/png")  # xato ko'tarmasligi kerak


def test_disallowed_type_rejected() -> None:
    with pytest.raises(FileValidationError):
        file_storage.validate_upload(b"MZ...", "application/x-msdownload")


def test_mismatched_signature_rejected() -> None:
    # Matn mazmuni, ammo image/png deb e'lon qilingan → rad etiladi.
    with pytest.raises(FileValidationError):
        file_storage.validate_upload(b"not a real png", "image/png")


def test_empty_file_rejected() -> None:
    with pytest.raises(FileValidationError):
        file_storage.validate_upload(b"", "image/png")


def test_oversize_rejected(monkeypatch) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 3)
    with pytest.raises(FileValidationError):
        file_storage.validate_upload(TINY_PNG, "image/png")


def test_save_and_read_roundtrip() -> None:
    stored = file_storage.save_file(TINY_PNG, "image/png")

    assert stored.storage_key
    assert stored.size_bytes == len(TINY_PNG)
    assert file_storage.read_file(stored.storage_key) == TINY_PNG


def test_read_rejects_path_traversal() -> None:
    with pytest.raises(FileNotFoundError):
        file_storage.read_file("../etc/passwd")
