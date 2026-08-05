"""Private fayl saqlash va validatsiya (11-bo'lim).

Xavfsizlik qoidalari:
- ruxsat etilgan MIME turlari ro'yxati;
- maksimal fayl hajmi;
- MIME va real file signature (magic bytes) mosligini tekshirish;
- tasodifiy storage key (original fayl nomi path sifatida ishlatilmaydi);
- fayllar maxfiy katalogda saqlanadi, faqat backend orqali beriladi.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings


class FileValidationError(ValueError):
    """Fayl validatsiyadan o'tmadi."""


# Ruxsat etilgan turlar uchun magic-byte imzolari.
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "application/pdf": (b"%PDF-",),
}


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    checksum: str
    size_bytes: int


def _matches_signature(content: bytes, content_type: str) -> bool:
    signatures = _SIGNATURES.get(content_type)
    if signatures is None:
        return False
    return any(content.startswith(sig) for sig in signatures)


def validate_upload(content: bytes, content_type: str) -> None:
    """Fayl mazmuni, turi va hajmini tekshiradi. Xatoda `FileValidationError`."""
    settings = get_settings()

    if content_type not in settings.allowed_upload_types:
        raise FileValidationError(f"Ruxsat etilmagan fayl turi: {content_type}")

    if len(content) == 0:
        raise FileValidationError("Bo'sh fayl.")

    if len(content) > settings.max_upload_bytes:
        raise FileValidationError(
            f"Fayl hajmi {settings.max_upload_bytes} baytdan oshmasligi kerak."
        )

    # E'lon qilingan MIME real imzo bilan mos kelishini tekshiramiz.
    if not _matches_signature(content, content_type):
        raise FileValidationError(
            "Fayl mazmuni ko'rsatilgan turga mos kelmaydi (soxta MIME)."
        )


def _storage_root() -> Path:
    root = Path(get_settings().file_storage_path)
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_file(content: bytes, content_type: str) -> StoredFile:
    """Faylni tekshirib, tasodifiy kalit bilan saqlaydi."""
    validate_upload(content, content_type)

    # Tasodifiy storage key — original nom ishlatilmaydi.
    storage_key = secrets.token_hex(16)
    checksum = hashlib.sha256(content).hexdigest()

    path = _storage_root() / storage_key
    path.write_bytes(content)

    return StoredFile(
        storage_key=storage_key,
        checksum=checksum,
        size_bytes=len(content),
    )


def read_file(storage_key: str) -> bytes:
    """Saqlangan faylni o'qiydi. Yo'q bo'lsa `FileNotFoundError`."""
    # storage_key faqat hex belgilardan iborat — path traversal'dan himoya.
    if not all(c in "0123456789abcdef" for c in storage_key):
        raise FileNotFoundError("Noto'g'ri storage key.")
    path = _storage_root() / storage_key
    return path.read_bytes()
