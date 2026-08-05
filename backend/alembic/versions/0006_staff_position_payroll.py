"""Kadrlar bo'limi: xodim lavozimi va oylik maosh (ish haqi fondi)

Revision ID: 0006_payroll
Revises: 0005_ai
Create Date: 2026-07-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_payroll"
down_revision: str | None = "0005_ai"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("position", sa.String(16), nullable=True))
    op.add_column(
        "users", sa.Column("monthly_salary", sa.Numeric(18, 2), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "monthly_salary")
    op.drop_column("users", "position")
