"""Foydalanuvchilar, rol biriktirmalari va refresh tokenlar (5.2-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """Tizim foydalanuvchisi. Shaxs va rol alohida saqlanadi (3-bo'lim)."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("phone", name="uq_users_phone"),
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Login uchun ishlatiladigan taxallus (masalan "Quvonchbek"). Kichik harfda
    # saqlanadi va tizimda unique bo'lishi shart (login shu orqali amalga oshadi).
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Telefon va email normalizatsiya qilinadi; mavjud bo'lsa unique (5.2-bo'lim).
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    preferred_language: Mapped[str] = mapped_column(
        String(8), nullable=False, default="uz"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Kadrlar bo'limida guruhlash uchun yorliq (RBAC'dan mustaqil, StaffPosition).
    position: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Ish haqi fondi uchun oylik maosh (ixtiyoriy, 5.8-bo'lim kengaytmasi).
    monthly_salary: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    # Kadrlar profili kengaytmasi (frontend v2): tug'ilgan sana, passport,
    # ishga kirgan sana, ish turi — barchasi ixtiyoriy.
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    passport_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    role_assignments: Mapped[list[UserRoleAssignment]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="UserRoleAssignment.user_id",
    )


class UserRoleAssignment(UUIDMixin, TimestampMixin, Base):
    """Foydalanuvchining filialdagi roli.

    OWNER uchun `branch_id` bo'sh bo'lishi mumkin; boshqa rollar uchun majburiy
    (5.2-bo'lim). Bu bitta xodimni bir nechta filialga biriktirish imkonini beradi.
    """

    __tablename__ = "user_role_assignments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=True, index=True
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped[User] = relationship(
        back_populates="role_assignments", foreign_keys=[user_id]
    )


class RefreshToken(UUIDMixin, TimestampMixin, Base):
    """Refresh token yozuvi.

    Token qiymati ochiq saqlanmaydi — faqat SHA-256 hash saqlanadi. Rotation
    va bekor qilish (revoke) shu jadval orqali amalga oshiriladi (11-bo'lim).
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PasswordResetToken(UUIDMixin, TimestampMixin, Base):
    """Parolni tiklash uchun bir martalik token.

    Token qiymati ochiq saqlanmaydi — faqat SHA-256 hash (RefreshToken bilan bir
    xil naqsh). Email orqali yuboriladigan havolada ochiq token bo'ladi.
    """

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
