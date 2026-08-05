"""Asinxron SQLAlchemy ulanishi va sessiya boshqaruvi.

0-bosqichda bu yerda faqat ulanish infratuzilmasi tayyorlanadi. Biznes modellar
keyingi bosqichlarda `app/models/` ichida qo'shiladi (loyiha strukturasi, 6-bo'lim).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Barcha ORM modellari uchun umumiy baza."""


def create_engine() -> AsyncEngine:
    """Sozlamalar asosida async engine yaratadi."""
    settings = get_settings()
    url = str(settings.database_url)
    kwargs: dict[str, object] = {"echo": settings.db_echo, "future": True}
    # SQLite (lokal dev) NullPool ishlatadi — pool o'lchami qo'llanmaydi.
    if not url.startswith("sqlite"):
        kwargs.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
        )
    return create_async_engine(url, **kwargs)


engine: AsyncEngine = create_engine()

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: bitta so'rov uchun DB sessiyasi.

    Xatolik yuz bersa tranzaksiya rollback qilinadi, aks holda commit qilinadi.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
