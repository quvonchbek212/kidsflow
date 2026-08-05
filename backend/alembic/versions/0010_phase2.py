"""7-bosqich B: payroll, xabar yuborish (kunlik ish belgisi), sozlamalar kengaytmasi.

Revision ID: 0010_phase2
Revises: 0009_frontend_core_v2
Create Date: 2026-07-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_phase2"
down_revision: str | None = "0009_frontend_core_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Sozlamalar kengaytmasi (Payme/Click/2FA ATAYLAB qo'shilmagan) ---
    op.add_column(
        "kindergarten_settings", sa.Column("hours_text", sa.String(255), nullable=True)
    )
    op.add_column(
        "kindergarten_settings",
        sa.Column("auto_invoice_day", sa.Integer(), nullable=True),
    )
    op.add_column(
        "kindergarten_settings",
        sa.Column(
            "notification_toggles",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.alter_column(
        "kindergarten_settings", "notification_toggles", server_default=None
    )

    # --- Kunlik ish belgisi (scheduler o'rnini bosuvchi) ---
    op.create_table(
        "daily_job_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_name", sa.String(64), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("job_name", "run_date", name="uq_daily_job_runs_name_date"),
    )

    # --- Payroll ---
    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("base_salary", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "bonus", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "deduction", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "advance_deducted",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("net_pay", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="RECORDED",
        ),
        sa.Column("expense_id", sa.Uuid(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=True),
        sa.Column("reversed_payroll_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["reversed_payroll_id"], ["payroll_runs.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_payroll_runs_branch_id", "payroll_runs", ["branch_id"])
    op.create_index("ix_payroll_runs_user_id", "payroll_runs", ["user_id"])
    op.create_index("ix_payroll_runs_status", "payroll_runs", ["status"])
    # Bitta xodim, bitta davr uchun faqat bitta FAOL (RECORDED) yozuv —
    # partial unique index (Enrollment'dagi "bitta faol enrollment" namunasida).
    op.create_index(
        "uq_payroll_runs_one_active_per_period",
        "payroll_runs",
        ["user_id", "period"],
        unique=True,
        postgresql_where=sa.text("status = 'RECORDED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_payroll_runs_one_active_per_period", table_name="payroll_runs")
    op.drop_index("ix_payroll_runs_status", table_name="payroll_runs")
    op.drop_index("ix_payroll_runs_user_id", table_name="payroll_runs")
    op.drop_index("ix_payroll_runs_branch_id", table_name="payroll_runs")
    op.drop_table("payroll_runs")
    op.drop_table("daily_job_runs")
    op.drop_column("kindergarten_settings", "notification_toggles")
    op.drop_column("kindergarten_settings", "auto_invoice_day")
    op.drop_column("kindergarten_settings", "hours_text")
