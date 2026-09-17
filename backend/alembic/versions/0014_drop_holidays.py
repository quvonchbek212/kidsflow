"""Bayramlar jadvali olib tashlandi.

Bayram tabriklari endi avtomatik yuborilmaydi: ular "Ota-onalar" bo'limidagi
ommaviy xabar orqali qo'lda jo'natiladi. Shuning uchun Sozlamalardagi
"Bayramlar" ro'yxati, uning API'si va worker'dagi eslatma bloki o'chirildi,
jadval esa endi hech narsa tomonidan o'qilmaydi.

`downgrade` jadvalni 0012_telegram_v2 dagi tuzilishda qayta yaratadi, lekin
o'chirilgan yozuvlarni qaytarmaydi.

Revision ID: 0014_drop_holidays
Revises: 0013_auto_billing
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0014_drop_holidays"
down_revision: str | None = "0013_auto_billing"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_index("ix_holidays_holiday_date", table_name="holidays")
    op.drop_index("ix_holidays_branch_id", table_name="holidays")
    op.drop_table("holidays")


def downgrade() -> None:
    op.create_table(
        "holidays",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "branch_id",
            sa.Uuid(),
            sa.ForeignKey("branches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("days_before", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "repeats_yearly",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_holidays_branch_id", "holidays", ["branch_id"])
    op.create_index("ix_holidays_holiday_date", "holidays", ["holiday_date"])
