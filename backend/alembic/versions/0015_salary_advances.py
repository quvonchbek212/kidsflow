"""Xodim avanslari.

Ilgari avans hech qayerda saqlanmasdi — oy oxirida oylik hisoblash oynasida
qo'lda yoziladigan son edi. Endi oy o'rtasida berilgan avans alohida yoziladi
(bog'langan "Ish haqi" xarajati bilan) va shu oyning oylik hisobida avtomatik
ushlanadi.

Revision ID: 0015_salary_advances
Revises: 0014_drop_holidays
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0015_salary_advances"
down_revision: str | None = "0014_drop_holidays"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "salary_advances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="RECORDED",
        ),
        sa.Column("expense_id", sa.Uuid(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expense_id"], ["expenses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_salary_advances_branch_id", "salary_advances", ["branch_id"])
    op.create_index("ix_salary_advances_user_id", "salary_advances", ["user_id"])
    op.create_index("ix_salary_advances_period", "salary_advances", ["period"])
    op.create_index("ix_salary_advances_status", "salary_advances", ["status"])


def downgrade() -> None:
    op.drop_index("ix_salary_advances_status", table_name="salary_advances")
    op.drop_index("ix_salary_advances_period", table_name="salary_advances")
    op.drop_index("ix_salary_advances_user_id", table_name="salary_advances")
    op.drop_index("ix_salary_advances_branch_id", table_name="salary_advances")
    op.drop_table("salary_advances")
