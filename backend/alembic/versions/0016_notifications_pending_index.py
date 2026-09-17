"""Kutayotgan bildirishnomalar uchun qisman indeks.

Worker har siklda `status = 'PENDING'` bo'yicha `created_at` tartibida so'raydi.
Indeks bo'lmagani uchun har 5 soniyada butun `notifications` jadvali
ko'rib chiqilardi, jadval esa hech qachon tozalanmaydi.

Revision ID: 0016_notifications_pending_index
Revises: 0015_salary_advances
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0016_notifications_pending_index"
down_revision: str | None = "0015_salary_advances"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_index(
        "ix_notifications_pending",
        "notifications",
        ["created_at"],
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_pending", table_name="notifications")
