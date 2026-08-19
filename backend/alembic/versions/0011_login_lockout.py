"""Hisob darajasidagi login qulfi.

IP bo'yicha rate limit bir nechta IP dan sekin taqsimlangan parol taxmin
qilishni to'xtata olmaydi — sanoq foydalanuvchi bo'yicha ham yuritilishi kerak.

Revision ID: 0011_login_lockout
Revises: 0010_phase2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0011_login_lockout"
down_revision: str | None = "0010_phase2"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "failed_login_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
