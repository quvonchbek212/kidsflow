"""Yangi frontend uchun asosiy qism kengaytmasi (7-bosqich A).

Guruh tarifi/xonasi, xodim profili (tug'ilgan sana/passport/ishga kirgan
sana/ish turi), enrollment'da doimiy chegirma, xarajat kategoriyasida
is_variable (zararsizlik hisobi uchun) va xarajatda is_recurring belgisi.

Revision ID: 0009_frontend_core_v2
Revises: 0008_username_reset
Create Date: 2026-07-28
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_frontend_core_v2"
down_revision: str | None = "0008_username_reset"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Guruh: tarif + xona ---
    op.add_column("groups", sa.Column("monthly_fee", sa.Numeric(18, 2), nullable=True))
    op.add_column("groups", sa.Column("room_number", sa.String(50), nullable=True))

    # --- Xodim profili kengaytmasi ---
    op.add_column("users", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("passport_number", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("hire_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("employment_type", sa.String(20), nullable=True))

    # --- Enrollment: doimiy chegirma ---
    op.add_column(
        "enrollments", sa.Column("discount_type", sa.String(20), nullable=True)
    )
    op.add_column(
        "enrollments",
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
    )

    # --- Xarajat: takrorlanuvchi belgisi ---
    op.add_column(
        "expenses",
        sa.Column(
            "is_recurring", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.alter_column("expenses", "is_recurring", server_default=None)

    # --- Xarajat kategoriyasi: o'zgaruvchan (variable) belgisi ---
    op.add_column(
        "expense_categories",
        sa.Column(
            "is_variable", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.alter_column("expense_categories", "is_variable", server_default=None)

    # Mavjud (avval lazy-seed qilingan) qatorlarni yangi 7-kategoriya sxemasiga
    # moslashtiramiz: "Ta'mirlash va jihoz" birlashtirilgan qatorni "Ta'mirlash"
    # deb qoldirib, alohida "Jihoz" qatorini qo'shamiz; "Oziq-ovqat" — variable.
    conn = op.get_bind()
    categories = sa.table(
        "expense_categories",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("is_variable", sa.Boolean()),
    )
    combined = conn.execute(
        sa.select(categories.c.id).where(categories.c.name == "Ta'mirlash va jihoz")
    ).first()
    if combined is not None:
        conn.execute(
            categories.update()
            .where(categories.c.id == combined.id)
            .values(name="Ta'mirlash")
        )
        conn.execute(
            categories.insert().values(
                id=uuid.uuid4(),
                name="Jihoz",
                is_system=True,
                is_active=True,
                is_variable=False,
            )
        )
    conn.execute(
        categories.update()
        .where(categories.c.name == "Oziq-ovqat")
        .values(is_variable=True)
    )


def downgrade() -> None:
    conn = op.get_bind()
    categories = sa.table(
        "expense_categories",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
    )
    jihoz = conn.execute(
        sa.select(categories.c.id).where(categories.c.name == "Jihoz")
    ).first()
    if jihoz is not None:
        conn.execute(categories.delete().where(categories.c.id == jihoz.id))
    conn.execute(
        categories.update()
        .where(categories.c.name == "Ta'mirlash")
        .values(name="Ta'mirlash va jihoz")
    )

    op.drop_column("expense_categories", "is_variable")
    op.drop_column("expenses", "is_recurring")
    op.drop_column("enrollments", "discount_percent")
    op.drop_column("enrollments", "discount_type")
    op.drop_column("users", "employment_type")
    op.drop_column("users", "hire_date")
    op.drop_column("users", "passport_number")
    op.drop_column("users", "birth_date")
    op.drop_column("groups", "room_number")
    op.drop_column("groups", "monthly_fee")
